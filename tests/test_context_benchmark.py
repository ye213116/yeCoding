from __future__ import annotations

import json

import pytest

from eval.context_protocol import schedule, select_tasks, summarize


def test_sampling_is_deterministic_balanced_and_does_not_consult_solutions():
    tasks = [
        {"instance_id": f"{repo}-{i}", "repo": repo, "patch": "secret gold"}
        for repo in ["a", "b", "c", "d", "e"]
        for i in range(10)
    ]
    selected = select_tasks(tasks, 20, 20261030)
    assert selected == select_tasks(list(reversed(tasks)), 20, 20261030)
    assert {repo: sum(t["repo"] == repo for t in selected) for repo in "abcde"} == {
        repo: 4 for repo in "abcde"
    }
    changed = [{**t, "patch": "different gold"} for t in tasks]
    assert [t["instance_id"] for t in selected] == [
        t["instance_id"] for t in select_tasks(changed, 20, 20261030)
    ]
    with pytest.raises(ValueError, match="eligible"):
        select_tasks(tasks, 100, 20261030)


def test_schedule_has_exact_main_and_ablation_counts_and_rotates_order():
    tasks = [f"instance-{i}" for i in range(20)]
    main = schedule(tasks)
    full = schedule(tasks, ablations=True)
    assert len(main) == len({r["id"] for r in main}) == 180
    assert len(full) == len({r["id"] for r in full}) == 300
    assert {r["line"] for r in main} == {"original", "evidence", "mini"}
    assert main[0]["line"] != main[3]["line"]


def test_statistics_keep_failed_run_costs_and_bootstrap_by_task():
    records = []
    for repeat in range(1, 4):
        for task in ["one", "two"]:
            for line in ["original", "evidence"]:
                resolved = not (line == "evidence" and task == "two")
                tokens = 100 if line == "original" else 50
                records.append(
                    {
                        "instance_id": task,
                        "repeat": repeat,
                        "line": line,
                        "resolved": resolved,
                        "completed": resolved,
                        "seconds": 1,
                        "cost_usd": 1,
                        "usage": {
                            "input_tokens": tokens,
                            "output_tokens": 10,
                            "total_tokens": tokens + 10,
                        },
                    }
                )
    result = summarize(records, bootstrap=200)
    assert result["by_line"]["evidence"]["resolved"] == 3
    assert result["by_line"]["evidence"]["cost_estimate_usd"] == 6
    paired = result["paired_vs_original"]["evidence"]
    assert paired["tasks"] == 2  # six repetitions are not six independent tasks
    assert paired["task_bootstrap_95pct"] == [-50, -50]
    assert len(paired["both_solved_pairs"]) == 3


def test_crashed_worker_preserves_received_usage_and_marks_unknown_remaining_cost(tmp_path):
    from eval.context_benchmark import recover_attempt

    events = [
        {"type": "request"},
        {
            "type": "model.event",
            "event": {
                "type": "usage",
                "usage": {
                    "input_tokens": 123,
                    "output_tokens": 7,
                },
            },
        },
        {"type": "request"},
    ]
    (tmp_path / "events.jsonl").write_text(
        "\n".join(json.dumps(e) for e in events) + '\n{"truncated":'
    )
    result = recover_attempt(tmp_path, {"instance_id": "task"}, "timeout")
    assert result["usage"]["total_tokens"] == 130
    assert result["llm_calls"] == 2
    assert result["cost_usd"] is None
    assert result["usage_incomplete"]
    assert (tmp_path / "final.patch").read_text() == ""


def test_run_cannot_call_model_when_environment_preflight_failed(tmp_path):
    from eval.context_benchmark import run

    (tmp_path / "protocol.json").write_text(json.dumps({"prepared": False}))
    with pytest.raises(ValueError, match="environment preflight"):
        run(tmp_path, "dev")


def test_budgets_account_cached_usage_and_stop_before_an_extra_request():
    from eval.context_protocol import DEFAULTS
    from eval.context_worker import Budget, BudgetExceeded

    budget = Budget({**DEFAULTS, "calls": 2}, None)
    assert budget.reserve() == 1
    budget.charge(
        {
            "prompt_tokens": 40,
            "completion_tokens": 5,
            "prompt_tokens_details": {"cached_tokens": 10},
        }
    )
    assert budget.usage.total_tokens == 45
    assert budget.usage.cache_hit_tokens == 10
    assert budget.usage.cache_miss_tokens == 30
    assert budget.reserve() == 2
    assert budget.accounted_calls == {1}
    with pytest.raises(BudgetExceeded):
        budget.reserve()
    assert budget.calls == 2


def test_control_fingerprint_excludes_credentials_but_locks_model():
    from eval.context_protocol import DEFAULTS, configure, control_fingerprint, controls
    from yecoding.config import YeCodingConfig

    config = YeCodingConfig()
    config.llm.api_key = "do-not-save-this-key"
    config.mcp.servers = [{"env": {"API_KEY": "another-private-key"}}]
    configure(config, DEFAULTS)
    original = control_fingerprint(config)
    assert "private-key" not in json.dumps(controls(config))
    assert "do-not-save" not in json.dumps(controls(config))
    config.llm.api_key = "rotated-key"
    assert control_fingerprint(config) == original
    config.llm.model = "different-model"
    assert control_fingerprint(config) != original


def test_source_freeze_uses_copies_and_detects_changes(tmp_path, monkeypatch):
    from eval import context_benchmark as benchmark

    root = tmp_path / "repo"
    (root / "src/yecoding").mkdir(parents=True)
    (root / "eval").mkdir()
    (root / "src/yecoding/module.py").write_text("constant = 1\n")
    (root / "eval/context_worker.py").write_text("constant = 2\n")
    monkeypatch.setattr(benchmark, "ROOT", root)
    manifest = {
        name: benchmark.digest(root / name)
        for name in [
            "src/yecoding/module.py",
            "eval/context_worker.py",
        ]
    }
    out = tmp_path / "frozen"
    benchmark.freeze_code(out, manifest)
    (root / "src/yecoding/module.py").write_text("constant = 999\n")
    assert (out / "improved/src/yecoding/module.py").read_text() == "constant = 1\n"
    with pytest.raises(ValueError, match="source changed"):
        benchmark.freeze_code(tmp_path / "changed", manifest)


def test_patch_export_runs_inside_environment_not_host_git(monkeypatch):
    from eval import context_worker as worker

    def forbidden(*args, **kwargs):
        raise AssertionError("host subprocess must not interpret model-controlled Git metadata")

    monkeypatch.setattr(worker.subprocess, "check_output", forbidden)
    monkeypatch.setattr(worker.subprocess, "run", forbidden)

    class Environment:
        def execute(self, action, *, timeout):
            assert "frozen-base" in action["command"]
            return {"returncode": 0, "output": "a patch generated in the container"}

    assert worker.export_patch(Environment(), "frozen-base") == "a patch generated in the container"
