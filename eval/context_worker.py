"""One isolated, fully accounted agent attempt. Invoked by context_benchmark."""

from __future__ import annotations

import asyncio
import importlib.metadata
import importlib.util
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from eval.context_protocol import configure, control_fingerprint, digest, save

ROOT = Path(__file__).resolve().parent.parent


class BudgetExceeded(RuntimeError):
    pass


class Budget:
    def __init__(self, limits, recorder):
        from yecoding.types import Usage

        self.limits = limits
        self.recorder = recorder
        self.calls = 0
        self.accounted_calls = set()
        self.usage = Usage()
        self.started = time.monotonic()
        self.provider_blocked = False
        self.exhausted = False

    def reserve(self):
        if (
            self.calls >= self.limits["calls"]
            or self.usage.total_tokens >= self.limits["tokens"]
            or time.monotonic() - self.started >= self.limits["seconds"]
        ):
            self.exhausted = True
            raise BudgetExceeded("task call/token/time budget exhausted")
        self.calls += 1
        return self.calls

    def charge(self, usage):
        from yecoding.types import Usage

        usage = dict(usage)
        details = usage.get("prompt_tokens_details") or {}
        if details.get("cached_tokens") and not usage.get("cache_hit_tokens"):
            usage.setdefault("prompt_cache_hit_tokens", details["cached_tokens"])
            usage.setdefault(
                "prompt_cache_miss_tokens",
                max(0, usage.get("prompt_tokens", 0) - details["cached_tokens"]),
            )
        self.usage = self.usage + Usage.from_mapping(usage)
        if Usage.from_mapping(usage).total_tokens:
            self.accounted_calls.add(self.calls)

    def error(self, error):
        text = str(error).lower()
        self.provider_blocked |= getattr(error, "status_code", None) in {
            401,
            402,
            403,
            429,
            500,
            502,
            503,
            504,
        }
        self.provider_blocked |= any(
            s in text
            for s in (
                "http 402",
                "http 401",
                "http 403",
                "http 429",
                "http 500",
                "http 502",
                "http 503",
                "http 504",
                "authenticationerror",
                "ratelimiterror",
                "insufficient balance",
                "could not connect",
                "request timed out",
                "apiconnectionerror",
                "insufficient_quota",
            )
        )


class BudgetClient:
    def __init__(self, client, budget):
        self.client = client
        self.budget = budget
        self.recorder = budget.recorder

    def __getattr__(self, name):
        return getattr(self.client, name)

    async def chat(self, messages, tools, *, system_prompt):
        call = self.budget.reserve()
        self.recorder.emit("budget.request", call=call)
        async for event in self.client.chat(messages, tools, system_prompt=system_prompt):
            if event.get("type") == "usage":
                self.budget.charge(event["usage"])
            if event.get("type") == "error":
                self.budget.error(event.get("error"))
            yield event


def create_environment(task, workspace, recorder, label):
    import yaml
    from minisweagent.config import builtin_config_dir
    from minisweagent.environments.docker import DockerEnvironment

    spec = yaml.safe_load((builtin_config_dir / "benchmarks/swebench.yaml").read_text())
    spec["environment"].pop("environment_class", None)
    # File tools run as the host user. Match container ownership so shell-created
    # files remain editable, and activate conda without requiring /root access.
    spec["environment"]["env"].pop("BASH_ENV", None)
    spec["environment"]["env"]["HOME"] = "/tmp"
    spec["environment"]["interpreter"] = [
        "/opt/miniconda3/bin/conda",
        "run",
        "--no-capture-output",
        "-n",
        "testbed",
        "/bin/bash",
        "-c",
    ]

    class ObservedEnvironment(DockerEnvironment):
        def execute(self, action, cwd="", *, timeout=None):
            try:
                output = super().execute(action, cwd, timeout=timeout)
                recorder.emit("command.result", action=action, result=output)
                return output
            except Exception as exc:
                recorder.emit("command.exception", action=action, error=str(exc))
                raise

    return ObservedEnvironment(
        **spec["environment"],
        image=task["image"],
        run_args=[
            "--rm",
            "--label",
            "yecoding.context.job=" + label,
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--network=none",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--memory=4g",
            "--cpus=2",
            "--pids-limit=512",
            "--mount",
            f"type=bind,src={workspace},dst=/testbed",
        ],
    ), spec


def materialize(task, workspace, label):
    seed = subprocess.check_output(
        [
            "docker",
            "create",
            "--label",
            "yecoding.context.job=" + label,
            "--network=none",
            "--entrypoint",
            "/bin/sleep",
            task["image"],
            "60",
        ],
        text=True,
    ).strip()
    try:
        workspace.mkdir()
        subprocess.run(
            ["docker", "cp", seed + ":/testbed/.", str(workspace)],
            check=True,
            stdout=subprocess.DEVNULL,
            timeout=180,
        )
    finally:
        subprocess.run(["docker", "rm", "-f", seed], stdout=subprocess.DEVNULL, check=False)
    from yecoding.sandbox.workspace import assert_safe_tree

    assert_safe_tree(workspace)
    # Models and source tools share this actual repo; generated local state is not a patch.
    exclude = workspace / ".git/info/exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    with exclude.open("a") as stream:
        stream.write("\n/.yecoding/\n/patch.txt\n")


def registry_for(workspace, env, recorder):
    from yecoding.tools import ToolRegistry, get_builtin_tools
    from yecoding.tools.base import ToolResult

    allow = {
        "read_file",
        "write_file",
        "edit_file",
        "list_dir",
        "glob",
        "grep",
        "directory_tree",
        "get_file_info",
        "bash",
        "search_code",
        "get_context",
    }
    registry = ToolRegistry()
    for tool in get_builtin_tools():
        if tool.name not in allow:
            continue
        original_handler = tool.handler

        async def handler(payload, context, *, name=tool.name, original=original_handler):
            payload = dict(payload)
            if name == "bash":
                from yecoding.policy import CommandGuard

                if context.config.policy.command_guard_enabled:
                    CommandGuard(context.config.policy.command_blacklist).validate(
                        payload["command"]
                    )
                output = await asyncio.to_thread(
                    env.execute, {"command": payload["command"]}, timeout=60
                )
                content = output["output"]
                if output.get("exception_info"):
                    content += "\n" + output["exception_info"]
                if len(content) > 20_000:
                    content = content[:20_000] + "\n... [truncated]"
                return ToolResult(content, is_error=output["returncode"] != 0)
            from yecoding.sandbox.workspace import assert_safe_tree

            assert_safe_tree(workspace)
            if isinstance(payload.get("path"), str) and payload["path"].startswith("/testbed/"):
                payload["path"] = payload["path"][len("/testbed/") :]
            elif payload.get("path") == "/testbed":
                payload["path"] = "."
            result = await original(payload, context)
            recorder.emit("tool.result", name=name, input=payload, result=result)
            return result

        tool.handler = handler
        tool.timeout = 90
        registry.register(tool)
    return registry


async def run_yecoding(job, cfg, client, budget, env, workspace):
    from yecoding.agent.agent import Agent
    from yecoding.prompt import PromptAssembler
    from yecoding.rag import CodeIndex
    from yecoding.sandbox.workspace import assert_safe_tree
    from yecoding.snapshot import SnapshotService

    if hasattr(cfg, "context"):
        cfg.context.strategy = "legacy" if job["line"] == "original" else "evidence"
        cfg.context.evidence_tokens = job["limits"]["evidence_tokens"]
        cfg.context.deduplicate = job["line"] != "no_dedup"
        cfg.context.use_structure = job["line"] != "no_structure"
        cfg.context.trace_path = None  # the shared observer also works with frozen source
    assert_safe_tree(workspace)
    CodeIndex(workspace).rebuild()
    registry = registry_for(workspace, env, budget.recorder)
    # Normalize only generated timestamp/path fields, identically on both internal lines.
    native_dynamic = PromptAssembler.build_dynamic
    native_static = PromptAssembler.build_static
    native_snapshot = SnapshotService.create

    def snapshot(service, phase):
        assert_safe_tree(workspace)
        return native_snapshot(service, phase)

    def static(assembler):
        return native_static(assembler).replace(str(workspace), "/testbed")

    def dynamic(assembler, message):
        text = native_dynamic(assembler, message)
        text = text.replace(str(workspace), "/testbed")
        return "\n".join(
            "Current time: 2026-10-30T00:00:00+00:00" if line.startswith("Current time: ") else line
            for line in text.splitlines()
        )

    PromptAssembler.build_dynamic = dynamic
    PromptAssembler.build_static = static
    SnapshotService.create = snapshot
    prompt = job["task"]["problem_statement"] + (
        "\n\nFix the issue in the source files. Do not modify tests or build configuration. "
        "Shell commands run inside the task container in /testbed; file tools use "
        "repository-relative paths. Network access is disabled and dependencies are installed. "
        "Inspect the repository, implement the fix, and verify it with available tests."
    )
    agent = Agent(
        llm_client=BudgetClient(client, budget),
        tool_registry=registry,
        config=cfg,
        cwd=str(workspace),
        max_turns=job["limits"]["calls"],
    )
    completed = False
    last_tool_phase = False
    try:
        async with asyncio.timeout(job["limits"]["seconds"]):
            async for event in agent.run(prompt):
                budget.recorder.emit("engine.event", event=event)
                if event.get("type") == "turn_complete":
                    last_tool_phase = event.get("stop_reason") == "tool_use"
                elif event.get("type") == "tool_call":
                    last_tool_phase = True
                if event.get("type") == "error":
                    raise event["error"]
                if event.get("type") == "done":
                    completed = True
    finally:
        PromptAssembler.build_dynamic = native_dynamic
        PromptAssembler.build_static = native_static
        SnapshotService.create = native_snapshot
    if completed and last_tool_phase:
        return "budget_exhausted"
    return "completed" if completed else "incomplete"


def run_mini(job, cfg, budget, env, spec):
    from minisweagent.agents.default import DefaultAgent
    from minisweagent.models.litellm_model import LitellmModel
    from minisweagent.models.utils.actions_toolcall import BASH_TOOL

    class ObservedModel(LitellmModel):
        # Abort rather than invisibly retry a failed provider request.
        abort_exceptions = [Exception]

        def _query(self, messages, **kwargs):
            call = budget.reserve()
            budget.recorder.emit(
                "request", call=call, request={"messages": messages, "tools": [BASH_TOOL]}
            )
            try:
                response = super()._query(messages, **kwargs)
            except Exception as exc:
                budget.error(exc)
                raise
            budget.charge(response.usage.model_dump())
            budget.recorder.emit("model.response", call=call, response=response.model_dump())
            return response

    from yecoding.llm.factory import DEEPSEEK_BASE_URL, OPENAI_BASE_URL

    base_url = cfg.llm.base_url or (
        DEEPSEEK_BASE_URL if cfg.llm.provider == "deepseek" else OPENAI_BASE_URL
    )
    model_options = dict(spec["model"])
    model_options.update(model_name="openai/" + cfg.llm.model, cost_tracking="ignore_errors")
    model_options["model_kwargs"] = {
        **model_options.get("model_kwargs", {}),
        "temperature": 0,
        "max_tokens": job["limits"]["output_tokens"],
        "api_key": cfg.llm.api_key,
        "api_base": base_url,
        "num_retries": 0,
        "timeout": 120,
    }
    agent_options = dict(spec["agent"])
    agent_options.update(
        step_limit=job["limits"]["calls"],
        cost_limit=0,
        wall_time_limit_seconds=job["limits"]["seconds"],
        output_path=None,
    )
    agent = DefaultAgent(ObservedModel(**model_options), env, **agent_options)
    result = agent.run(job["task"]["problem_statement"])
    budget.recorder.emit("mini.trajectory", trajectory=agent.serialize())
    if budget.exhausted:
        return "budget_exhausted"
    return (
        "completed"
        if result.get("exit_status") == "Submitted"
        else result.get("exit_status", "incomplete")
    )


def export_patch(env, base_commit):
    # Interpret model-controlled Git metadata only in the isolated task container.
    output = env.execute(
        {
            "command": (
                "git -c core.fsmonitor=false -c core.hooksPath=/dev/null "
                "add --intent-to-add -- . && "
                "git -c core.fsmonitor=false -c core.hooksPath=/dev/null "
                "diff --no-ext-diff --no-textconv --binary "
                + shlex.quote(base_commit)
                + " -- . ':(exclude).yecoding' ':(exclude)patch.txt'"
            )
        },
        timeout=60,
    )
    if output["returncode"] != 0:
        raise RuntimeError("candidate export failed in task container")
    return output["output"]


def main():
    global ROOT
    job_file = Path(sys.argv[1]).resolve()
    job = json.loads(job_file.read_text())
    ROOT = Path(job["source_root"])
    directory = job_file.parent
    os.environ["MSWEA_GLOBAL_CONFIG_DIR"] = str(directory / "mini-config")
    os.environ["MSWEA_SILENT_STARTUP"] = "1"
    source = Path(job["experiment"]) / "baseline/src" if job["line"] == "original" else ROOT / "src"
    sys.path.insert(0, str(source))
    from yecoding.config import load_config
    from yecoding.llm import create_llm_client

    # Load the same observation code even when the application comes from frozen HEAD.
    spec = importlib.util.spec_from_file_location(
        "context_observer", ROOT / "src/yecoding/context/trace.py"
    )
    observer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(observer)
    cfg = load_config(job["config_root"])
    configure(cfg, job["limits"])
    protocol = json.loads((Path(job["experiment"]) / "protocol.json").read_text())
    if control_fingerprint(cfg) != protocol["control_fingerprint"]:
        raise ValueError("model or control configuration changed after protocol freeze")
    packages = sorted(
        f"{d.metadata['Name']}=={d.version}" for d in importlib.metadata.distributions()
    )
    if packages != protocol["packages"]:
        raise ValueError("evaluation dependencies changed after freeze")
    if protocol.get("price_snapshot"):
        cfg.llm.prices = protocol["price_snapshot"]["prices"]
    scratch = Path(tempfile.mkdtemp(prefix="yecoding-context-task-"))
    workspace = scratch / "workspace"
    save(directory / "workspace.json", {"path": str(workspace)})
    cfg.policy.audit_log_path = str(directory / "audit.jsonl")
    recorder = observer.TraceRecorder(directory / "events.jsonl", secrets=(cfg.llm.api_key,))
    budget = Budget(job["limits"], recorder)
    client = create_llm_client(cfg.llm)
    observed = observer.ObservedClient(client, recorder)
    env = None
    result = {k: job[k] for k in ("id", "instance_id", "line", "repeat")}
    result.update(status="starting", completed=False, resolved=None)
    phase = "setup"
    try:
        if not cfg.llm.api_key:
            raise ValueError("model key is not configured")
        materialize(job["task"], workspace, digest(job_file))
        env, native_config = create_environment(job["task"], workspace, recorder, digest(job_file))
        phase = "agent"
        if job["line"] == "mini":
            status = run_mini(job, cfg, budget, env, native_config)
        else:
            status = asyncio.run(run_yecoding(job, cfg, observed, budget, env, workspace))
        result.update(status=status, completed=status == "completed")
    except BudgetExceeded:
        result["status"] = "budget_exhausted"
    except TimeoutError:
        result["status"] = "timeout"
    except Exception as exc:
        budget.error(exc)
        result["status"] = "environment_error" if phase == "setup" else "error"
        recorder.emit("run.error", error=str(exc))
    finally:
        try:
            patch = export_patch(env, job["task"]["base_commit"]) if env else ""
            (directory / "final.patch").write_text(patch)
        except Exception as exc:
            (directory / "final.patch").write_text("")
            recorder.emit("candidate.error", error=str(exc))
            result["candidate_error"] = True
        finally:
            if env:
                env.cleanup()
        result.update(
            usage=budget.usage.to_dict(),
            llm_calls=budget.calls,
            seconds=time.monotonic() - budget.started,
            provider_blocked=budget.provider_blocked,
            usage_incomplete=len(budget.accounted_calls) < budget.calls,
        )
        if client.price_profile:
            known_cost = client.calculate_cost(budget.usage, currency="usd").total_cost
            result["known_cost_usd"] = known_cost
            result["cost_usd"] = None if result["usage_incomplete"] else known_cost
        recorder.emit("run.completed", result=result)
        save(directory / "result.json", result)
        # Preserve accountable logs and patch; scratch workspaces can be regenerated.
        if workspace.exists():
            shutil.rmtree(workspace)
        scratch.rmdir()


if __name__ == "__main__":
    main()
