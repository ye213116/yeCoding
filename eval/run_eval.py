"""T6 evaluation runner: grep, whole-file, and symbol-index context assembly.

Usage:
    uv run python eval/run_eval.py [--budget 4000] [--skip-llm] [--out eval/results/results.json]

Retrieval dimensions (context tokens, recall) always run. The generation
dimension (usefulness, LLM-as-judge) runs when an API key is configured and
uses the SAME model for both strategies. See eval/README.md for the full
methodology and statistical calibers.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import statistics
import subprocess
import sys
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from yecoding.rag.code_index import SKIP_DIRS, CodeIndex  # noqa: E402
from yecoding.rag.evaluation import (  # noqa: E402
    ANSWER_SYSTEM,
    ANSWER_TEMPLATE,
    JUDGE_TEMPLATE,
    RetrievalResult,
    TaskMetrics,
    compute_recall,
    file_retrieve,
    generate_answer,
    grep_retrieve,
    judge_answer_with_evidence,
    load_tasks,
    symbol_retrieve,
)


def _mean_std(values: list[float]) -> tuple[float, float]:
    return statistics.mean(values), (statistics.stdev(values) if len(values) > 1 else 0.0)


def _fmt(value: float) -> str:
    return f"{value:.2f}"


def summarize(rows: list[TaskMetrics]) -> dict[str, dict[str, str]]:
    by_strategy: dict[str, list[TaskMetrics]] = {}
    for row in rows:
        by_strategy.setdefault(row.strategy, []).append(row)
    summary: dict[str, dict[str, str]] = {}
    for strategy, items in sorted(by_strategy.items()):
        tokens_mean, tokens_std = _mean_std([float(i.token_estimate) for i in items])
        primary_mean, primary_std = _mean_std([i.primary_recall for i in items])
        overall_mean, overall_std = _mean_std([i.overall_recall for i in items])
        file_mean, file_std = _mean_std([i.file_recall for i in items])
        calls_mean, calls_std = _mean_std([float(i.tool_calls) for i in items])
        entry = {
            "context_tokens": f"{tokens_mean:.0f}±{tokens_std:.0f}",
            "primary_recall": f"{primary_mean:.2%}±{primary_std:.2%}",
            "overall_recall": f"{overall_mean:.2%}±{overall_std:.2%}",
            "file_recall": f"{file_mean:.2%}±{file_std:.2%}",
            "tool_calls": f"{calls_mean:.1f}±{calls_std:.1f}",
        }
        scored = [i.usefulness_score for i in items if i.usefulness_score is not None]
        if scored:
            u_mean, u_std = _mean_std(scored)
            entry["usefulness"] = f"{u_mean:.2f}±{u_std:.2f} (n={len(scored)})"
        else:
            entry["usefulness"] = "not scored (n=0)"
        line_mean, line_std = _mean_std([i.overall_line_coverage for i in items])
        entry["overall_line_coverage"] = f"{line_mean:.2%}±{line_std:.2%}"
        summary[strategy] = entry
    return summary


def render_markdown(summary: dict[str, dict[str, str]]) -> str:
    dimensions = list(next(iter(summary.values())).keys())
    header = "| dimension | " + " | ".join(summary.keys()) + " |"
    separator = "| --- " * (len(summary) + 1) + "|"
    lines = [header, separator]
    for dimension in dimensions:
        cells = " | ".join(summary[strategy][dimension] for strategy in summary)
        lines.append(f"| {dimension} | {cells} |")
    return "\n".join(lines)


def save_report(path: Path, metadata: dict, rows: list[TaskMetrics]) -> None:
    payload = {
        **metadata,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "summary": summarize(rows),
        "rows": [
            {
                "task_id": row.task_id,
                "strategy": row.strategy,
                "context_sha256": row.context_sha256,
                "token_estimate": row.token_estimate,
                "primary_recall": row.primary_recall,
                "overall_recall": row.overall_recall,
                "file_recall": row.file_recall,
                "tool_calls": row.tool_calls,
                "truncated": row.truncated,
                "usefulness_score": row.usefulness_score,
                "answer_text": row.answer_text,
                "context_text": row.context_text,
                "judge_text": row.judge_text,
                "overall_line_coverage": row.overall_line_coverage,
            }
            for row in rows
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.replace(path)


def restore_report(path: Path, metadata: dict, rows: list[TaskMetrics]) -> int:
    if not path.is_file():
        return 0
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    if any(previous.get(key) != value for key, value in metadata.items()):
        return 0
    previous_rows = {
        (row.get("task_id"), row.get("strategy")): row for row in previous.get("rows", [])
    }
    restored = 0
    for row in rows:
        old = previous_rows.get((row.task_id, row.strategy), {})
        if old.get("context_sha256") != row.context_sha256:
            continue
        row.answer_text = old.get("answer_text")
        row.usefulness_score = old.get("usefulness_score")
        row.judge_text = old.get("judge_text")
        restored += row.usefulness_score is not None
    return restored


async def run_generation_dimension(
    rows: list[TaskMetrics],
    results: dict[tuple[str, str], RetrievalResult],
    tasks,
    answer_llm,
    judge_llm,
    save_progress: Callable[[], None],
) -> None:
    metrics_by_key = {(m.task_id, m.strategy): m for m in rows}
    for task in tasks:
        for strategy in dict.fromkeys(row.strategy for row in rows):
            metric = metrics_by_key[(task.id, strategy)]
            if metric.usefulness_score is not None:
                continue
            result = results[(task.id, strategy)]
            if not result.text:
                continue
            if metric.answer_text is None:
                metric.answer_text = await generate_answer(answer_llm, task.query, result.text)
                save_progress()
            score, judge_text = await judge_answer_with_evidence(
                judge_llm, task, metric.answer_text
            )
            metric.usefulness_score = score
            metric.judge_text = judge_text
            save_progress()
            print(f"scored {task.id} {strategy}: {score:.0f}/5", flush=True)


def source_manifest(root: Path) -> dict[str, str]:
    """Hash the Python inputs, including uncommitted changes, without reading secrets."""
    files = {}
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS or part.startswith(".") for part in relative.parts):
            continue
        files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return files


def git_state(root: Path) -> dict:
    def probe(*args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(root), *args],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return result.stdout.strip() if result.returncode == 0 else None

    # An extracted fixture inside an ignored folder is not the parent Git repository.
    if probe("check-ignore", ".") is not None:
        return {"revision": None, "dirty": None}
    status = probe("status", "--porcelain")
    return {
        "revision": probe("rev-parse", "HEAD"),
        "dirty": bool(status) if status is not None else None,
    }


def validate_tasks(index: CodeIndex, tasks) -> None:
    """Reject invalid or ambiguous labels instead of silently changing recall denominators."""
    ids = [task.id for task in tasks]
    if not tasks or len(ids) != len(set(ids)):
        raise ValueError("task set must be nonempty with unique task IDs")
    by_name = {}
    for symbol in index.list_symbols(limit=100000):
        by_name.setdefault(symbol.qualified_name, []).append(symbol)
    for task in tasks:
        if not task.query.strip() or not task.en_terms or not task.primary_symbols:
            raise ValueError(f"{task.id}: query, terms and primary symbols are required")
        for name in [*task.primary_symbols, *task.dep_symbols]:
            matches = by_name.get(name, [])
            if len(matches) != 1:
                raise ValueError(f"{task.id}: symbol {name!r} has {len(matches)} matches")
            if matches[0].path not in task.relevant_files:
                raise ValueError(f"{task.id}: relevant_files omits the file for {name!r}")
        for relative in task.relevant_files:
            path = (index.root / relative).resolve()
            if not path.is_relative_to(index.root) or not path.is_file():
                raise ValueError(f"{task.id}: invalid relevant file {relative!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget", type=int, default=4000)
    parser.add_argument("--repo", type=str, default=str(REPO_ROOT))
    parser.add_argument("--tasks", type=str, default=str(Path(__file__).parent / "tasks.json"))
    parser.add_argument("--out", type=str, default=None)
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--ablation", action="store_true", help="also run symbol_no_deps")
    parser.add_argument(
        "--config-root", type=Path, help="model configuration root (default: --repo)"
    )
    args = parser.parse_args()
    if args.budget < 128:
        parser.error("--budget must be at least 128 tokens")
    if not Path(args.repo).is_dir():
        parser.error("--repo must be an existing directory")

    tasks = load_tasks(args.tasks)
    index = CodeIndex(args.repo)
    index.rebuild()
    validate_tasks(index, tasks)
    task_metadata = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    source_files = source_manifest(index.root)
    benchmark_repository = task_metadata.get("repository")
    if benchmark_repository and source_files != benchmark_repository.get("source_files_sha256"):
        parser.error("--repo source does not match the task set's pinned source manifest")
    out_path = Path(args.out) if args.out else Path(__file__).parent / "results" / "results.json"

    rows: list[TaskMetrics] = []
    results: dict[tuple[str, str], RetrievalResult] = {}
    for task in tasks:
        # All strategies receive the same fixed, task-author-supplied keywords.
        symbol_query = f"{task.query} {' '.join(task.en_terms)}"
        grep_result = grep_retrieve(index, task.en_terms, args.budget)
        file_result = file_retrieve(index, task.en_terms, args.budget)
        symbol_result = symbol_retrieve(index, symbol_query, args.budget)
        retrieved = [grep_result, file_result, symbol_result]
        if args.ablation:
            retrieved.append(
                symbol_retrieve(index, symbol_query, args.budget, include_dependencies=False)
            )
        for result in retrieved:
            results[(task.id, result.strategy)] = result
            rows.append(compute_recall(index, task, result))
    for row in rows:
        context = results[(row.task_id, row.strategy)].text
        row.context_sha256 = hashlib.sha256(context.encode("utf-8")).hexdigest()
        row.context_text = context

    use_llm = not args.skip_llm
    config = None
    answer_llm = None
    judge_llm = None
    if use_llm:
        from yecoding.config import load_config
        from yecoding.llm.factory import create_llm_client

        config = load_config(project_root=args.config_root or Path(args.repo))
        if config.llm.api_key:
            config.llm.temperature = 0.0
            config.llm.max_tokens = min(config.llm.max_tokens, 1024)
            answer_llm = create_llm_client(config.llm)
            judge_limit = 1024 if config.llm.provider.lower() == "deepseek" else 4096
            judge_llm = create_llm_client(replace(config.llm, max_tokens=judge_limit))
            if config.llm.provider.lower() == "deepseek":
                answer_llm.thinking = "disabled"
                judge_llm.thinking = "disabled"
            print(f"usefulness dimension enabled: model={config.llm.model}")
        else:
            print("no API key configured; usefulness dimension skipped")

    signature = hashlib.sha256(
        (ANSWER_SYSTEM + ANSWER_TEMPLATE + JUDGE_TEMPLATE).encode("utf-8")
    ).hexdigest()
    metadata = {
        "report_version": 2,
        "repository": str(index.root),
        "repository_git": git_state(index.root),
        "benchmark_repository": benchmark_repository,
        "source_files_sha256": source_files,
        "implementation_files_sha256": {
            **{
                f"src/yecoding/{path}": sha
                for path, sha in source_manifest(REPO_ROOT / "src/yecoding").items()
            },
            "eval/run_eval.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        },
        "strategies": list(dict.fromkeys(row.strategy for row in rows)),
        "budget_tokens": args.budget,
        "task_count": len(tasks),
        "tasks_sha256": hashlib.sha256(Path(args.tasks).read_bytes()).hexdigest(),
        "evaluation_signature": signature,
        "model": config.llm.model if answer_llm is not None else None,
        "provider": config.llm.provider if answer_llm is not None else None,
        "temperature": config.llm.temperature if answer_llm is not None else None,
        "answer_max_output_tokens": answer_llm.max_tokens if answer_llm is not None else None,
        "judge_max_output_tokens": judge_llm.max_tokens if judge_llm is not None else None,
        "thinking": answer_llm.thinking if answer_llm is not None else None,
    }
    if answer_llm is not None:
        restored = restore_report(out_path, metadata, rows)
        if restored:
            print(f"resumed {restored} scored rows from {out_path}")

    def save_progress() -> None:
        save_report(out_path, metadata, rows)

    save_progress()
    if answer_llm is not None:
        asyncio.run(
            run_generation_dimension(rows, results, tasks, answer_llm, judge_llm, save_progress)
        )

    summary = summarize(rows)
    markdown = render_markdown(summary)
    print(f"\n== T6 comparison (budget={args.budget} tokens, {len(tasks)} tasks) ==")
    print(markdown)
    print("\nper-task detail:")
    for row in rows:
        usefulness = _fmt(row.usefulness_score) if row.usefulness_score is not None else "-"
        print(
            f"  {row.task_id} {row.strategy:6s} tokens={row.token_estimate:5d} "
            f"primary={row.primary_recall:.0%} overall={row.overall_recall:.0%} "
            f"file={row.file_recall:.0%} calls={row.tool_calls} "
            f"truncated={row.truncated} usefulness={usefulness}"
        )

    print(f"\nresults written to {out_path}")

    # Sanity assertion: same task set and budget for all strategies.
    for row in rows:
        assert row.budget_tokens == args.budget
    assert len(rows) == (4 if args.ablation else 3) * len(tasks)


if __name__ == "__main__":
    main()
