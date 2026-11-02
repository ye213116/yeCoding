from __future__ import annotations

import asyncio
import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
from typer.testing import CliRunner

from yecoding.agent import QueryEngine
from yecoding.agent.repair import BudgetClient, BudgetExhausted, VerifiedRepair
from yecoding.config import load_config
from yecoding.entrypoints.cli import app
from yecoding.memory import MemoryManager
from yecoding.runtime.api import _engine_events
from yecoding.sandbox.docker import DockerSandbox
from yecoding.sandbox.workspace import RepairWorkspace, assert_safe_tree, inventory
from yecoding.tools import ToolRegistry
from yecoding.tools.base import ToolContext


class ScriptedClient:
    """Protocol fixture, not a product model: Docker still executes every acceptance test."""

    model_name = "scripted-test-client"
    provider_name = "test"
    max_context_window = 32_000

    def __init__(self, *, succeed=True, tamper=False):
        self.succeed = succeed
        self.tamper = tamper
        self.attempts = 0
        self.seen = []

    async def chat(self, messages, tools, *, system_prompt):
        self.seen.append((system_prompt, tools, messages))
        if "Role: worker." in system_prompt and messages[-1].role != "tool":
            self.attempts += 1
            if self.tamper:
                name = "bash"
                args = {"command": "echo '# bypass' > tests/test_fix.py"}
            else:
                name = "write_file"
                result = 2 if self.succeed and self.attempts >= 2 else -self.attempts
                args = {"path": "calc.py", "content": f"def add(a, b):\n    return {result}\n"}
            yield {
                "type": "tool_call_delta",
                "tool_call": {
                    "index": 0,
                    "id": f"edit-{self.attempts}",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(args),
                    },
                },
            }
            yield {"type": "message_end", "stop_reason": "tool_use"}
        else:
            # Even an overconfident reviewer cannot override real failing tests.
            yield {"type": "text_delta", "text": "Approved. Everything is fixed."}
            yield {"type": "message_end", "stop_reason": "end_turn"}
        yield {"type": "usage", "usage": {"input_tokens": 20, "output_tokens": 10}}


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "project"
    root.mkdir()
    (root / "calc.py").write_text("def add(a, b):\n    return 0\n")
    (root / "tests").mkdir()
    (root / "tests/test_fix.py").write_text(
        "import unittest\nfrom calc import add\n"
        "class TestAdd(unittest.TestCase):\n"
        "    def test_add(self):\n        self.assertEqual(add(1, 1), 2)\n"
    )
    config = load_config(project_root=root, env={})
    config.repair.test_commands = ["python -m unittest discover -s tests -v"]
    config.repair.artifacts_dir = str(tmp_path / "artifacts")
    config.memory.long_term_db_path = str(tmp_path / "memory.db")
    config.policy.audit_log_path = str(tmp_path / "audit.jsonl")
    config.repair.max_attempts = 2
    return root, config


def workflow(project, client=None):
    root, config = project
    return VerifiedRepair(llm_client=client or ScriptedClient(), config=config, cwd=str(root))


async def complete(repair):
    return [event async for event in repair.run("Fix addition returning incorrect results")][-1][
        "report"
    ]


def test_workspace_snapshot_excludes_environment_and_preserves_source(project):
    root, _ = project
    (root / ".env").write_text("TOKEN=must-not-be-copied")
    snapshot = RepairWorkspace(root)
    try:
        assert not (snapshot.work / ".env").exists()
        (snapshot.work / "calc.py").write_text("def add(a, b):\n    return a + b\n")
        patch, _, changes = snapshot.candidate()
        assert changes == ["calc.py"]
        assert "return a + b" in patch
        assert "return 0" in (root / "calc.py").read_text()
    finally:
        snapshot.close()


def test_protected_tests_cannot_be_exported(project):
    root, _ = project
    snapshot = RepairWorkspace(root)
    try:
        (snapshot.work / "tests/test_fix.py").write_text("# removed test")
        with pytest.raises(ValueError, match="fixed tests"):
            snapshot.candidate()
    finally:
        snapshot.close()


def test_symlinks_rejected_even_inside_ignored_directories(tmp_path):
    (tmp_path / ".yecoding").mkdir()
    (tmp_path / ".yecoding/leak").symlink_to("/etc/passwd")
    with pytest.raises(ValueError, match="link"):
        assert_safe_tree(tmp_path)


def test_fixed_test_write_and_path_escape_denied_at_tool_boundary(project):
    repair = workflow(project)
    registry = repair._registry(project[0])
    context = ToolContext(cwd=str(project[0]), config=repair.config)
    for path in ["tests/test_fix.py", "../outside.py"]:
        with pytest.raises(ValueError):
            asyncio.run(registry.get("write_file").execute({"path": path, "content": ""}, context))
    assert "write_file" not in repair._registry(project[0], readonly=True).list_names()
    assert "bash" not in repair._registry(project[0], readonly=True).list_names()
    assert "save_skill" not in registry.list_names()


def test_export_patch_replays_add_delete_and_missing_newline(project, tmp_path):
    root, _ = project
    (root / "remove.py").write_text("remove me")
    snapshot = RepairWorkspace(root)
    try:
        (snapshot.work / "calc.py").write_text("fixed")
        (snapshot.work / "new.py").write_text("new")
        (snapshot.work / "remove.py").unlink()
        patch, files, _ = snapshot.candidate()
        target = tmp_path / "apply"
        snapshot.materialize(target, snapshot.base)
        result = subprocess.run(
            ["git", "apply", "--unsafe-paths", "-"],
            input=patch,
            text=True,
            capture_output=True,
            cwd=target,
        )
        assert result.returncode == 0, result.stderr
        assert inventory(target) == files
    finally:
        snapshot.close()


def test_shared_model_budget_stops_before_next_request(project):
    _, config = project
    options = deepcopy(config.repair)
    options.max_llm_calls = 1
    client = BudgetClient(ScriptedClient(), options)

    async def run():
        _ = [event async for event in client.chat([], [], system_prompt="test")]
        with pytest.raises(BudgetExhausted):
            _ = [event async for event in client.chat([], [], system_prompt="test")]

    asyncio.run(run())
    assert client.calls == 1
    assert client.usage.total_tokens == 30


def test_repair_requires_explicit_acceptance_commands(project):
    project[1].repair.test_commands = []
    with pytest.raises(ValueError, match="fixed test_commands"):
        asyncio.run(complete(workflow(project)))


def test_cli_requires_test_and_exposes_repair_command(project):
    runner = CliRunner()
    help_result = runner.invoke(app, ["repair", "--help"])
    assert help_result.exit_code == 0
    assert "--test" in help_result.output
    result = runner.invoke(app, ["repair", "fix", "--cwd", str(project[0])])
    assert result.exit_code != 0
    assert "--test" in result.output


def test_repair_configuration_loads(project):
    root, _ = project
    (root / ".yecoding").mkdir()
    (root / ".yecoding/config.json").write_text(
        json.dumps(
            {
                "repair": {"test_commands": ["python tests/check.py"], "max_attempts": 2},
            }
        )
    )
    config = load_config(root, env={})
    assert config.repair.max_attempts == 2
    assert config.repair.test_commands == ["python tests/check.py"]


def test_cli_preserves_configured_repair_budgets(project, monkeypatch):
    root, _ = project
    (root / ".yecoding").mkdir()
    (root / ".yecoding/config.json").write_text(
        json.dumps(
            {
                "llm": {"api_key": "test-key"},
                "repair": {
                    "test_commands": ["python check.py"],
                    "max_attempts": 1,
                    "timeout": 5,
                    "strategy": "single",
                },
            }
        )
    )
    captured = {}

    class Workflow:
        def __init__(self, **kwargs):
            captured["options"] = kwargs["options"]

        async def run(self, _message):
            yield {"type": "done", "report": {"status": "verified"}}

    monkeypatch.setattr("yecoding.agent.repair.VerifiedRepair", Workflow)
    result = CliRunner().invoke(app, ["repair", "fix", "--cwd", str(root), "--json"])
    assert result.exit_code == 0, result.output
    assert captured["options"].max_attempts == 1
    assert captured["options"].timeout == 5
    assert captured["options"].strategy == "single"


def test_stale_repair_memory_is_not_injected(project):
    repair = workflow(project)
    repair.workspace = RepairWorkspace(project[0])
    try:
        memory = repair._memory()
        memory.save(json.dumps({"task": "addition", "base_hash": "old"}), kind="repair")
        valid = memory.save(
            json.dumps(
                {
                    "task": "addition",
                    "base_hash": repair.workspace.base_hash,
                }
            ),
            kind="repair",
        )
        recalled = repair._recall("addition")
        assert "old" not in recalled
        assert repair.report["recalled_memory_ids"] == [valid]
    finally:
        repair.workspace.close()


def test_runtime_repair_failure_is_an_error_event():
    class Engine:
        async def repair(self, _message):
            yield {"type": "done", "report": {"status": "no_progress", "artifacts": "/tmp/run"}}

    async def run():
        return [event async for event in _engine_events(Engine(), "repair", "fix")]

    events = asyncio.run(run())
    assert events[-1]["type"] == "error"
    assert "no_progress" in str(events[-1]["error"])


docker = pytest.mark.skipif(
    os.environ.get("YECODING_TEST_DOCKER") != "1",
    reason="set YECODING_TEST_DOCKER=1 with Docker and python:3.11-slim preloaded",
)


@docker
def test_real_docker_feedback_repair_and_memory(project):
    repair = workflow(project)
    original = inventory(project[0])
    report = asyncio.run(complete(repair))
    assert report["status"] == "verified", report
    assert len(report["attempts"]) == 2
    assert not report["attempts"][0]["passed"]
    assert report["attempts"][1]["passed"]
    assert report["saved_memory_id"]
    assert {skill["name"] for skill in report["skills"]} == {
        "repair-reproduce",
        "repair-minimal",
        "repair-verify",
    }
    assert inventory(project[0]) == original
    assert not repair.workspace.work.exists()
    artifact = Path(report["artifacts"])
    assert (artifact / "candidate.patch").is_file()
    saved = json.loads((artifact / "report.json").read_text())
    assert saved["usage"]["total_tokens"] > 0
    assert (
        MemoryManager(project[1].memory.long_term_db_path, str(project[0])).list()[0].kind
        == "repair"
    )


@docker
def test_reviewer_cannot_override_real_failing_tests(project):
    report = asyncio.run(complete(workflow(project, ScriptedClient(succeed=False))))
    assert report["status"] == "attempts_exhausted"
    assert all(not attempt["passed"] for attempt in report["attempts"])
    assert "saved_memory_id" not in report
    assert not (Path(report["artifacts"]) / "candidate.patch").exists()


@docker
def test_shell_test_tampering_is_rejected(project):
    report = asyncio.run(complete(workflow(project, ScriptedClient(tamper=True))))
    assert report["status"] == "attempts_exhausted"
    assert all(attempt["category"] == "invalid_patch" for attempt in report["attempts"])


@docker
def test_docker_isolation_and_no_host_environment(project, monkeypatch):
    monkeypatch.setenv("REPAIR_SECRET_SENTINEL", "host-value")
    sandbox = DockerSandbox()
    root = project[0]
    result = asyncio.run(
        sandbox.execute(
            root,
            (
                'test -z "$REPAIR_SECRET_SENTINEL" && '
                "test ! -e /var/run/docker.sock && "
                "touch /workspace/created && "
                "! touch /outside-workspace && "
                "python -c 'import socket; socket.create_connection((\"1.1.1.1\", 443), timeout=1)'"
            ),
        )
    )
    assert not result.passed  # network is disabled
    assert (root / "created").exists()
    readonly = asyncio.run(sandbox.execute(root, "touch /workspace/forbidden", readonly=True))
    assert not readonly.passed
    assert not (root / "forbidden").exists()


@docker
def test_docker_timeout_cleans_container(project):
    sandbox = TrackingSandbox(timeout=0.5)
    result = asyncio.run(sandbox.execute(project[0], "sleep 60 & wait"))
    assert result.timed_out
    assert result.category == "timeout"
    remaining = subprocess.check_output(
        ["docker", "ps", "-aq", "--filter", f"name=^/{sandbox.last_name}$"],
        text=True,
    )
    assert not remaining.strip()


@docker
def test_docker_cancel_cleans_container(project):
    sandbox = TrackingSandbox()

    async def run():
        job = asyncio.create_task(sandbox.execute(project[0], "sleep 60"))
        await asyncio.sleep(0.5)
        job.cancel()
        with pytest.raises(asyncio.CancelledError):
            await job

    asyncio.run(run())
    remaining = subprocess.check_output(
        ["docker", "ps", "-aq", "--filter", f"name=^/{sandbox.last_name}$"],
        text=True,
    )
    assert not remaining.strip()


@docker
def test_missing_image_fails_closed_before_model_call(project):
    project[1].repair.image = "yecoding-nonexistent-image:missing"
    report = asyncio.run(complete(workflow(project)))
    assert report["status"] == "environment_error"
    assert report["llm_calls"] == 0


@docker
def test_sdk_uses_same_repair_workflow(project):
    root, config = project
    config.features.memory = False
    engine = QueryEngine(
        llm_client=ScriptedClient(),
        tool_registry=ToolRegistry(),
        config=config,
        cwd=str(root),
    )
    report = engine.repair_complete("Fix addition")
    assert report["status"] == "verified"
    assert "saved_memory_id" not in report


class TrackingSandbox(DockerSandbox):
    def arguments(self, workspace, name, command, *, readonly=False):
        self.last_name = name
        return super().arguments(workspace, name, command, readonly=readonly)


@docker
def test_passing_baseline_is_not_claimed_as_a_repair(project):
    (project[0] / "calc.py").write_text("def add(a, b):\n    return 2\n")
    report = asyncio.run(complete(workflow(project)))
    assert report["status"] == "baseline_passed"
    assert report["llm_calls"] == 0
    assert not report["attempts"]


@docker
def test_budget_exhaustion_persists_report(project):
    project[1].repair.max_llm_calls = 1
    report = asyncio.run(complete(workflow(project)))
    assert report["status"] == "budget_exhausted"
    assert report["llm_calls"] == 1
    assert (Path(report["artifacts"]) / "report.json").exists()


@docker
def test_model_claim_without_patch_stops_as_no_progress(project):
    repair = workflow(project)

    async def no_edit(*args, **kwargs):
        return "All fixed"

    repair._agent = no_edit
    report = asyncio.run(complete(repair))
    assert report["status"] == "no_progress"


@docker
def test_wall_clock_deadline_cleans_up_and_persists_evidence(project):
    project[1].repair.test_commands = ["sleep 60"]
    project[1].repair.timeout = 0.5
    repair = workflow(project)
    repair.sandbox = TrackingSandbox()
    report = asyncio.run(complete(repair))
    assert report["status"] == "timeout"
    assert not repair.workspace.work.exists()
    assert (Path(report["artifacts"]) / "report.json").exists()
    remaining = subprocess.check_output(
        ["docker", "ps", "-aq", "--filter", f"name=^/{repair.sandbox.last_name}$"],
        text=True,
    )
    assert not remaining.strip()


@docker
def test_large_container_output_is_drained_but_bounded(project):
    result = asyncio.run(
        DockerSandbox().execute(
            project[0],
            "python -c 'print(\"x\" * 200000)'",
        )
    )
    assert result.passed
    assert "[output truncated]" in result.stdout
    assert len(result.stdout) < 21_000
