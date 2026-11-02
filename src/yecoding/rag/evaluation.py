"""Evaluation harness for keyword, whole-file, and structural code context.

Implements the T6 comparison with three quantified dimensions per task:

1. context length in tokens (same budget for both strategies),
2. recall of labeled relevant symbols (span-intersection based),
3. usefulness of the generated answer (LLM-as-judge, same model, optional).

All strategies run on the same task set (``eval/tasks.json``) and, when the
generation dimension is enabled, through the same LLM client. The grep
baseline is a deterministic simulation of the pre-index agent loop: one grep
per query term followed by expanding hits into fixed-size excerpts, capped by
the token budget. It receives the same English keywords a model would grep
for, so no LLM is needed to keep retrieval metrics reproducible.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from yecoding.context import estimate_text_tokens
from yecoding.rag.code_index import SKIP_DIRS, CodeIndex
from yecoding.rag.context_builder import ContextBuilder, ContextPackConfig

GREP_CONTEXT_LINES = 3
GREP_PER_TERM_LIMIT = 30
DEF_SPAN_LINES = 4


@dataclass(slots=True)
class EvalTask:
    id: str
    query: str
    en_terms: list[str]
    primary_symbols: list[str]
    dep_symbols: list[str]
    relevant_files: list[str]

    @classmethod
    def from_mapping(cls, data: dict) -> EvalTask:
        return cls(
            id=str(data["id"]),
            query=str(data["query"]),
            en_terms=[str(t) for t in data["en_terms"]],
            primary_symbols=[str(s) for s in data.get("primary_symbols", [])],
            dep_symbols=[str(s) for s in data.get("dep_symbols", [])],
            relevant_files=[str(f) for f in data.get("relevant_files", [])],
        )


def load_tasks(path: str | Path) -> list[EvalTask]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [EvalTask.from_mapping(item) for item in raw["tasks"]]


@dataclass(slots=True)
class RetrievalResult:
    strategy: str
    text: str
    token_estimate: int
    budget_tokens: int
    #: path -> set of 1-based line numbers present in the context.
    spans: dict[str, set[int]] = field(default_factory=dict)
    tool_calls: int = 0
    truncated: bool = False


@dataclass(slots=True)
class TaskMetrics:
    task_id: str
    strategy: str
    token_estimate: int
    budget_tokens: int
    primary_recall: float
    overall_recall: float
    file_recall: float
    tool_calls: int
    truncated: bool
    usefulness_score: float | None = None
    answer_text: str | None = None
    context_sha256: str | None = None
    context_text: str | None = None
    judge_text: str | None = None
    overall_line_coverage: float = 0.0


# ---------------------------------------------------------------------------
# Strategy A: deterministic grep + excerpt baseline
# ---------------------------------------------------------------------------


def grep_retrieve(index: CodeIndex, en_terms: list[str], budget_tokens: int) -> RetrievalResult:
    """Simulate the pre-index agent loop: grep each term, then read excerpts."""
    result = RetrievalResult(
        strategy="grep", text="", token_estimate=0, budget_tokens=budget_tokens
    )
    files = _python_files(index.root)
    greps = 0
    hits: list[tuple[str, int]] = []
    seen_hits: set[tuple[str, int]] = set()
    for term in en_terms:
        term_l = term.lower()
        matched: list[tuple[str, int]] = []
        for path, lines in files.items():
            for number, line in enumerate(lines, start=1):
                if term_l in line.lower():
                    matched.append((path, number))
                    if len(matched) >= GREP_PER_TERM_LIMIT:
                        break
            if len(matched) >= GREP_PER_TERM_LIMIT:
                break
        if not matched:
            continue
        greps += 1
        for hit in matched:
            if hit not in seen_hits:
                seen_hits.add(hit)
                hits.append(hit)
    if not hits:
        return result

    # Read stage: expand hits into excerpts grouped per file until budget.
    by_file: dict[str, list[int]] = {}
    for path, number in hits:
        by_file.setdefault(path, []).append(number)
    blocks: list[str] = []
    for path in sorted(by_file):
        lines = files.get(path) or []
        line_set: set[int] = set()
        for number in by_file[path]:
            line_set.update(
                range(max(1, number - GREP_CONTEXT_LINES), number + GREP_CONTEXT_LINES + 1)
            )
        rendered_spans = _merge_lines(sorted(line_set))
        for start, end in rendered_spans:
            excerpt = "\n".join(lines[start - 1 : end])
            block = f"### {path}:{start}-{end}\n{excerpt}"
            cost = estimate_text_tokens(block) + 2
            if result.token_estimate + cost > budget_tokens:
                result.truncated = True
                break
            result.token_estimate += cost
            blocks.append(block)
            result.spans.setdefault(path, set()).update(range(start, end + 1))
    # One grep call per term plus one read call per touched file.
    result.tool_calls = greps + len(result.spans)
    result.text = "\n\n".join(blocks)
    return result


def _merge_lines(numbers: list[int]) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for number in numbers:
        if spans and number <= spans[-1][1] + 1:
            spans[-1] = (spans[-1][0], number)
        else:
            spans.append((number, number))
    return spans


def _python_files(root: Path) -> dict[str, list[str]]:
    files: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIRS or part.startswith(".") for part in path.parts):
            continue
        try:
            rel = str(path.relative_to(root))
            files[rel] = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except (OSError, ValueError):
            continue
    return files


# ---------------------------------------------------------------------------
# Strategy B: keyword-selected whole files, read from the beginning
# ---------------------------------------------------------------------------


def file_retrieve(index: CodeIndex, en_terms: list[str], budget_tokens: int) -> RetrievalResult:
    """Rank files by query-term matches, then include raw file prefixes.

    This baseline uses no symbol index or ground-truth labels for selection.
    It emulates opening likely files directly and pasting their contents into
    the prompt. A file that exceeds the remaining budget is cut at a line
    boundary; no later files are considered after that cut.
    """
    result = RetrievalResult(
        strategy="file", text="", token_estimate=0, budget_tokens=budget_tokens
    )
    terms = list(dict.fromkeys(term.strip().lower() for term in en_terms if term.strip()))
    if not terms:
        return result

    ranked: list[tuple[int, int, int, str, list[str]]] = []
    for path, lines in _python_files(index.root).items():
        source = "\n".join(lines).lower()
        matching = [term for term in terms if term in source or term in path.lower()]
        if matching:
            path_hits = sum(term in path.lower() for term in matching)
            frequency = sum(min(source.count(term), 10) for term in matching)
            ranked.append((-len(matching), -path_hits, -frequency, path, lines))
    ranked.sort()
    if not ranked:
        return result

    blocks: list[str] = []
    for _, _, _, path, lines in ranked:
        header = f"### {path} (from line 1)\n"
        separator_cost = estimate_text_tokens("\n\n") if blocks else 0
        remaining = budget_tokens - result.token_estimate - separator_cost
        if estimate_text_tokens(header) >= remaining:
            result.truncated = True
            break

        low, high = 0, len(lines)
        while low < high:
            mid = (low + high + 1) // 2
            block = header + "\n".join(lines[:mid])
            if estimate_text_tokens(block) <= remaining:
                low = mid
            else:
                high = mid - 1
        if low == 0:
            result.truncated = True
            break

        block = header + "\n".join(lines[:low])
        blocks.append(block)
        result.token_estimate += separator_cost + estimate_text_tokens(block)
        result.spans[path] = set(range(1, low + 1))
        if low < len(lines):
            result.truncated = True
            break

    result.text = "\n\n".join(blocks)
    result.token_estimate = estimate_text_tokens(result.text)
    # One keyword-based file selection plus one read per included file.
    result.tool_calls = 1 + len(result.spans)
    return result


# ---------------------------------------------------------------------------
# Strategy C: symbol index + budgeted context assembly
# ---------------------------------------------------------------------------


def symbol_retrieve(
    index: CodeIndex, query: str, budget_tokens: int, *, include_dependencies: bool = True
) -> RetrievalResult:
    config = ContextPackConfig(include_dependencies=include_dependencies)
    pack = ContextBuilder(index, config).build(query, budget_tokens)
    spans: dict[str, set[int]] = {}
    for path, start, end in pack.spans:
        spans.setdefault(path, set()).update(range(start, end + 1))
    return RetrievalResult(
        strategy="symbol" if include_dependencies else "symbol_no_deps",
        text=pack.text,
        token_estimate=pack.token_estimate,
        budget_tokens=pack.budget_tokens,
        spans=spans,
        tool_calls=1,
        truncated=pack.truncated,
    )


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def compute_recall(
    index: CodeIndex,
    task: EvalTask,
    result: RetrievalResult,
) -> TaskMetrics:
    symbol_map = {s.qualified_name: s for s in index.list_symbols(limit=100000)}

    def recall_of(qualified_names: list[str]) -> tuple[float, int, int]:
        hits = 0
        known = 0
        for qualified in qualified_names:
            symbol = symbol_map.get(qualified)
            if symbol is None:
                continue
            known += 1
            covered = result.spans.get(symbol.path, set())
            if any(line in covered for line in range(symbol.line, symbol.line + DEF_SPAN_LINES)):
                hits += 1
        return (hits / known if known else 0.0), hits, known

    primary_recall, _, _ = recall_of(task.primary_symbols)
    overall_recall, _, _ = recall_of([*task.primary_symbols, *task.dep_symbols])
    relevant_files = set(task.relevant_files)
    file_hits = len(relevant_files & set(result.spans))
    file_recall = file_hits / len(relevant_files) if relevant_files else 0.0

    coverage = []
    for qualified in dict.fromkeys([*task.primary_symbols, *task.dep_symbols]):
        symbol = symbol_map.get(qualified)
        if symbol is not None:
            lines = set(range(symbol.line, symbol.end_line + 1))
            coverage.append(len(lines & result.spans.get(symbol.path, set())) / len(lines))

    return TaskMetrics(
        task_id=task.id,
        strategy=result.strategy,
        token_estimate=result.token_estimate,
        budget_tokens=result.budget_tokens,
        primary_recall=primary_recall,
        overall_recall=overall_recall,
        file_recall=file_recall,
        tool_calls=result.tool_calls,
        truncated=result.truncated,
        overall_line_coverage=sum(coverage) / len(coverage) if coverage else 0.0,
    )


# ---------------------------------------------------------------------------
# Optional generation dimension: same model answers, same model judges
# ---------------------------------------------------------------------------

ANSWER_SYSTEM = "You are a code assistant. Answer strictly based on the provided code context."

ANSWER_TEMPLATE = """## Code context
{context}

## Question
{question}

Answer in Chinese in at most 350 Chinese characters.
Cite file paths and function names from the context."""

JUDGE_TEMPLATE = """You are grading an answer about a codebase.

## Question
{question}

## Reference ground truth (relevant symbols)
{ground_truth}

## Answer to grade
{answer}

Grade usefulness from 1 to 5:
1 = wrong or misleading, 2 = mostly wrong, 3 = partially useful,
4 = useful and mostly correct, 5 = precise, complete, well grounded in the right symbols.

Reply with exactly one line: "score: N" where N is 1-5."""


async def generate_answer(client, question: str, context_text: str) -> str:
    """Stream one completion and collect the text (same client for both strategies)."""
    from yecoding.types import Message

    content = ANSWER_TEMPLATE.format(context=context_text, question=question)
    messages = [Message(role="user", content=content)]
    text = ""
    async for event in client.chat(messages, [], system_prompt=ANSWER_SYSTEM):
        if event.get("type") == "text_delta":
            text += str(event.get("text") or "")
        elif event.get("type") == "error":
            raise RuntimeError(f"generation failed: {event.get('error')}")
    return text.strip()


async def judge_answer_with_evidence(client, task: EvalTask, answer: str) -> tuple[float, str]:
    from yecoding.types import Message

    ground_truth = "\n".join(
        [f"- primary: {q}" for q in task.primary_symbols]
        + [f"- dependency: {q}" for q in task.dep_symbols]
        + [f"- file: {f}" for f in task.relevant_files]
    )
    messages = [
        Message(
            role="user",
            content=JUDGE_TEMPLATE.format(
                question=task.query, ground_truth=ground_truth, answer=answer
            ),
        )
    ]
    text = ""
    async for event in client.chat(messages, [], system_prompt="You are a strict grader."):
        if event.get("type") == "text_delta":
            text += str(event.get("text") or "")
        elif event.get("type") == "error":
            raise RuntimeError(f"judge failed: {event.get('error')}")
    match = re.search(r"score:\s*([1-5])", text)
    if not match:
        raise RuntimeError(f"unparseable judge reply: {text[:200]}")
    return float(match.group(1)), text.strip()


async def judge_answer(client, task: EvalTask, answer: str) -> float:
    score, _ = await judge_answer_with_evidence(client, task, answer)
    return score
