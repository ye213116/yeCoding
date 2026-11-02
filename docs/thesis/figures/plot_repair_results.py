"""Render chapter 6 from archived results; this never calls models or Docker.

Run with uv run --no-project --with matplotlib==3.11.2 python, followed by this file's path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import subprocess
from collections import Counter
from pathlib import Path

import matplotlib
from matplotlib import font_manager


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=("zh", "en"), default="zh")
    args = parser.parse_args()
    english = args.language == "en"
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    font_path = subprocess.check_output(
        ["fc-match", "-f", "%{file}", "Noto Sans CJK SC"], text=True
    ).strip()
    font_manager.fontManager.addfont(font_path)
    figures = Path(__file__).resolve().parent
    root = figures.parents[2]
    source = root / "eval/evidence/repair-heldout-live.json"
    data = json.loads(source.read_text())
    strategies = ("single", "team", "verified")
    summary = {}
    records = []
    failures = Counter()
    for strategy in strategies:
        runs = [r for row in data["records"] for r in row["runs"] if r["strategy"] == strategy]
        result = {
            "tasks": len(runs),
            "verified": sum(r["status"] == "verified" for r in runs),
            "independently_passed": sum(
                bool(r["independent"] and r["independent"]["passed"]) for r in runs
            ),
            "false_acceptances": sum(r["false_acceptance"] for r in runs),
            "mean_tokens": statistics.mean(r["usage"]["total_tokens"] for r in runs),
            "mean_seconds": statistics.mean(r["duration"] for r in runs),
        }
        for key, value in result.items():
            if not math.isclose(value, data["summary"][strategy][key], rel_tol=1e-12):
                raise ValueError(f"Archived summary mismatch: {strategy}.{key}")
        result["mean_llm_calls"] = statistics.mean(r["llm_calls"] for r in runs)
        result["budget_exhausted"] = sum(r["status"] == "budget_exhausted" for r in runs)
        summary[strategy] = result
    for row in data["records"]:
        for run in row["runs"]:
            records.append(
                {
                    "task": row["id"],
                    "strategy": run["strategy"],
                    "run_id": run["id"],
                    "status": run["status"],
                    "independent_checked": run["independent"] is not None,
                    "independently_passed": bool(
                        run["independent"] and run["independent"]["passed"]
                    ),
                    "llm_calls": run["llm_calls"],
                    "tokens": run["usage"]["total_tokens"],
                    "attempts": len(run["attempts"]),
                }
            )
            if run["status"] == "budget_exhausted":
                if any(a.get("passed") for a in run["attempts"]):
                    phase = "after_acceptance_pass"
                elif any("patch_hash" in a for a in run["attempts"]):
                    phase = "after_candidate_handoff"
                else:
                    phase = "before_candidate_handoff"
                failures[phase] += 1
    audit = {
        "source": "eval/evidence/repair-heldout-live.json",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "matplotlib_version": matplotlib.__version__,
        "summary": summary,
        "budget_failure_phases": dict(failures),
        "independent_checked": sum(r["independent_checked"] for r in records),
        "records": records,
    }
    notes = figures.parent / "notes"
    notes.mkdir(exist_ok=True)
    (notes / "ch06-statistics.json").write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n"
    )

    plt.rcParams.update(
        {
            "font.family": ["DejaVu Sans"] if english else ["Noto Sans CJK SC", "DejaVu Sans"],
            "font.size": 12,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.unicode_minus": False,
            "svg.fonttype": "path",
            # This CJK font contains CFF outlines; Type 3 preserves the glyphs
            # when importing the vector PDF into TeX and common PDF viewers.
            "pdf.fonttype": 3,
        }
    )
    labels = (
        ["Single role\nsingle", "Review feedback\nteam", "Test feedback\nverified"]
        if english
        else ["单角色\nsingle", "评审反馈多角色\nteam", "验证反馈多角色\nverified"]
    )
    rows, columns = (2, 1) if english else (1, 2)
    size = (6.2, 7.0) if english else (9.2, 4.0)
    fig, axes = plt.subplots(rows, columns, figsize=size, layout="constrained")
    x = list(range(3))
    width = 0.34
    left = axes[0]
    workflow = left.bar(
        [i - width / 2 for i in x],
        [summary[s]["verified"] for s in strategies],
        width,
        label="Workflow success" if english else "流程验收成功",
        color="#355f8d",
    )
    independent = left.bar(
        [i + width / 2 for i in x],
        [summary[s]["independently_passed"] for s in strategies],
        width,
        label="Extra checks passed" if english else "额外检查通过",
        color="#e6b65b",
        hatch="//",
    )
    left.bar_label(
        workflow, labels=[f"{summary[s]['verified']}/8" for s in strategies], padding=3, fontsize=12
    )
    left.bar_label(
        independent,
        labels=[f"{summary[s]['independently_passed']}/8" for s in strategies],
        padding=3,
        fontsize=12,
    )
    left.set_xticks(x, labels)
    left.set_ylim(0, 10.5)
    left.set_yticks(range(0, 9, 2))
    left.set_ylabel("Passing tasks (n=8 per group)" if english else "通过任务数（每组 n=8）")
    left.set_title("(a) Workflow and extra checks" if english else "(a) 流程结果与额外检查")
    left.legend(loc="upper right", frameon=False, fontsize=10 if english else 12)
    left.grid(axis="y", alpha=0.2)
    left.set_axisbelow(True)
    right = axes[1]
    tokens = [summary[s]["mean_tokens"] / 1000 for s in strategies]
    bars = right.bar(x, tokens, width=0.58, color="#355f8d")
    right.bar_label(bars, labels=[f"{v:.2f}" for v in tokens], padding=4)
    right.set_xticks(x, labels)
    right.set_ylim(0, 80)
    right.set_ylabel("Mean total tokens (thousands)" if english else "平均累计 token（千）")
    right.set_title("(b) Usage, including failures" if english else "(b) 模型用量（包含失败运行）")
    right.grid(axis="y", alpha=0.2)
    right.set_axisbelow(True)
    for suffix in ("svg", "pdf", "png"):
        name = "06-repair-comparison-en" if english else "06-repair-comparison"
        fig.savefig(figures / f"{name}.{suffix}", dpi=180)
    plt.close(fig)
    print(
        json.dumps(
            {
                "summary": summary,
                "budget_failure_phases": dict(failures),
                "independent_checked": audit["independent_checked"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
