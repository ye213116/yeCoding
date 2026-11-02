from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest

from eval.export_review import export_review
from eval.prepare_external import prepare
from eval.run_eval import restore_report, save_report, source_manifest, validate_tasks
from yecoding.rag.code_index import CodeIndex
from yecoding.rag.evaluation import (
    EvalTask,
    compute_recall,
    file_retrieve,
    grep_retrieve,
    load_tasks,
    symbol_retrieve,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
TASKS_PATH = REPO_ROOT / "eval" / "tasks.json"


@pytest.fixture(scope="module")
def repo_index() -> CodeIndex:
    index = CodeIndex(REPO_ROOT)
    index.rebuild()
    return index


@pytest.fixture(scope="module")
def tasks():
    return load_tasks(TASKS_PATH)


def test_task_set_is_well_formed(tasks):
    assert len(tasks) >= 10
    ids = [task.id for task in tasks]
    assert len(ids) == len(set(ids))
    for task in tasks:
        assert task.query.strip()
        assert task.en_terms
        assert task.primary_symbols
        assert task.relevant_files


def test_task_set_ground_truth_exists_in_index(repo_index, tasks):
    """Every labeled symbol must exist in the AST index (label validity)."""
    known = {symbol.qualified_name for symbol in repo_index.list_symbols(limit=100000)}
    missing = [
        qualified
        for task in tasks
        for qualified in [*task.primary_symbols, *task.dep_symbols]
        if qualified not in known
    ]
    assert not missing, f"ground-truth symbols missing from index: {missing}"
    missing_files = [
        path for task in tasks for path in task.relevant_files if not (REPO_ROOT / path).is_file()
    ]
    assert not missing_files, f"ground-truth files missing from repository: {missing_files}"


def test_grep_retrieve_respects_budget_and_records_spans(repo_index, tasks):
    budget = 1500
    result = grep_retrieve(repo_index, tasks[0].en_terms, budget)

    assert result.strategy == "grep"
    assert 0 < result.token_estimate <= budget
    assert result.spans
    assert result.tool_calls >= 1
    # Deterministic: same inputs, same output.
    again = grep_retrieve(repo_index, tasks[0].en_terms, budget)
    assert again.text == result.text


def test_symbol_retrieve_returns_single_call_context(repo_index, tasks):
    result = symbol_retrieve(repo_index, tasks[0].query, 4000)

    assert result.strategy == "symbol"
    assert result.tool_calls == 1
    assert result.token_estimate <= 4000
    assert "<code-context" in result.text
    assert result.spans


def test_file_retrieve_uses_prefix_and_respects_budget(tmp_path):
    target = tmp_path / "target.py"
    target.write_text(
        "\n".join(f"target_value_{index} = {index}" for index in range(50)) + "\n",
        encoding="utf-8",
    )
    index = CodeIndex(tmp_path)
    index.rebuild()

    result = file_retrieve(index, ["target_value"], 100)

    assert result.strategy == "file"
    assert 0 < result.token_estimate <= 100
    assert result.truncated
    assert result.spans["target.py"] == set(range(1, len(result.spans["target.py"]) + 1))
    assert len(result.spans["target.py"]) < 50
    assert "target_value_0" in result.text
    assert "target_value_49" not in result.text
    assert file_retrieve(index, ["target_value"], 100).text == result.text


def test_recall_computation_on_synthetic_spans(repo_index, tasks):
    task = tasks[0]
    empty = grep_retrieve(repo_index, [], 1000)
    empty.spans = {}
    metrics = compute_recall(repo_index, task, empty)
    assert metrics.primary_recall == 0.0
    assert metrics.overall_recall == 0.0
    assert metrics.file_recall == 0.0

    # Cover the whole first ground-truth file: file recall must be partial
    # (only one of possibly several files) but positive.
    symbols = {s.qualified_name: s for s in repo_index.list_symbols(limit=100000)}
    target = symbols[task.primary_symbols[0]]
    full = grep_retrieve(repo_index, [], 1000)
    full.spans = {target.path: set(range(1, 100000))}
    metrics = compute_recall(repo_index, task, full)
    assert metrics.primary_recall > 0.0
    assert 0.0 < metrics.file_recall <= 1.0


def test_grep_and_symbol_find_known_symbol_in_fixed_fixture(tmp_path):
    # Recall on the changing repository is a measurement, not a guaranteed invariant.
    # Keep the positive-recall correctness check on a controlled, single-file fixture.
    (tmp_path / "sample.py").write_text(
        "class Parser:\n    def prepare(self, text):\n        return text.strip()\n"
    )
    repo_index = CodeIndex(tmp_path)
    repo_index.rebuild()
    task = EvalTask(
        "fixture",
        "Parser prepare",
        ["Parser", "prepare"],
        ["sample.Parser.prepare"],
        [],
        ["sample.py"],
    )
    for result in (
        grep_retrieve(repo_index, task.en_terms, 4000),
        symbol_retrieve(repo_index, task.query, 4000),
    ):
        metrics = compute_recall(repo_index, task, result)
        assert metrics.token_estimate <= 4000
        assert metrics.primary_recall > 0.0, result.strategy


def test_eval_checkpoint_resumes_only_matching_context(tmp_path, repo_index, tasks):
    task = tasks[0]
    result = grep_retrieve(repo_index, task.en_terms, 4000)
    row = compute_recall(repo_index, task, result)
    row.context_sha256 = "matching-context"
    row.answer_text = "测试回答"
    row.usefulness_score = 4.0
    output = tmp_path / "results.json"
    metadata = {"model": "fake-model", "budget_tokens": 4000}
    save_report(output, metadata, [row])

    resumed = compute_recall(repo_index, task, result)
    resumed.context_sha256 = "matching-context"
    assert restore_report(output, metadata, [resumed]) == 1
    assert resumed.answer_text == "测试回答"
    assert resumed.usefulness_score == 4.0

    stale = compute_recall(repo_index, task, result)
    stale.context_sha256 = "different-context"
    assert restore_report(output, metadata, [stale]) == 0
    assert stale.usefulness_score is None


def test_external_fixture_and_ground_truth_are_valid_offline(tmp_path):
    root = prepare(tmp_path / "upstream")
    index = CodeIndex(root)
    index.rebuild()
    external_tasks = load_tasks(REPO_ROOT / "eval/tasks-python-dotenv.json")
    assert len(external_tasks) == 12
    validate_tasks(index, external_tasks)
    with pytest.raises(FileExistsError):
        prepare(tmp_path / "upstream")


def test_task_validation_rejects_missing_labels(repo_index, tasks):
    from dataclasses import replace

    invalid = replace(tasks[0], primary_symbols=["missing.nonexistent"])
    with pytest.raises(ValueError, match="0 matches"):
        validate_tasks(repo_index, [invalid])


def test_source_manifest_captures_edits_without_reading_dotenv(tmp_path):
    source = tmp_path / "app.py"
    source.write_text("x = 1\n")
    (tmp_path / ".env").write_text("TEST_SECRET=hidden\n")
    before = source_manifest(tmp_path)
    assert set(before) == {"app.py"}
    source.write_text("x = 2\n")
    assert source_manifest(tmp_path) != before


def test_signature_recall_does_not_imply_full_line_coverage(tmp_path):
    from yecoding.rag.evaluation import EvalTask, RetrievalResult

    (tmp_path / "app.py").write_text("def target():\n    x = 1\n    return x\n")
    index = CodeIndex(tmp_path)
    index.rebuild()
    task = EvalTask("test", "target", ["target"], ["app.target"], [], ["app.py"])
    result = RetrievalResult("symbol", "def target()", 10, 1000, {"app.py": {1}})
    metric = compute_recall(index, task, result)
    assert metric.primary_recall == 1.0
    assert metric.overall_line_coverage == pytest.approx(1 / 3)


def test_review_export_hides_strategy_and_preserves_mapping(tmp_path):
    task_path = tmp_path / "tasks.json"
    task_path.write_text(
        json.dumps({"tasks": [{"id": "D01", "query": "Explain", "reference_facts": ["Fact"]}]})
    )
    report = tmp_path / "report.json"
    report.write_text(
        json.dumps(
            {
                "tasks_sha256": hashlib.sha256(task_path.read_bytes()).hexdigest(),
                "rows": [
                    {
                        "task_id": "D01",
                        "strategy": "symbol",
                        "answer_text": "Answer",
                        "usefulness_score": 5,
                    }
                ],
            }
        )
    )
    out = tmp_path / "review"
    assert export_review(report, task_path, out) == 1
    with (out / "review.csv").open(encoding="utf-8-sig", newline="") as handle:
        row = next(csv.DictReader(handle))
    assert row["answer"] == "Answer"
    assert row["reference_facts"] == "Fact"
    assert row["usefulness_1_5"] == ""
    assert "strategy" not in row
    key = json.loads((out / "review-key.json").read_text())
    assert key["rows"][row["review_id"]] == {"task_id": "D01", "strategy": "symbol"}
    with pytest.raises(FileExistsError):
        export_review(report, task_path, out)
