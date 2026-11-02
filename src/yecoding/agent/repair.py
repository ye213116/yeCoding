from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import time
import uuid
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from yecoding.agent.query import query
from yecoding.config import RepairConfig
from yecoding.memory import MemoryManager
from yecoding.prompt import PromptAssembler
from yecoding.rag import CodeIndex
from yecoding.sandbox.docker import DockerSandbox
from yecoding.sandbox.workspace import RepairWorkspace, assert_safe_tree, protected
from yecoding.skill import SkillContextBuffer, SkillRegistry
from yecoding.tools import ToolRegistry, get_builtin_tools
from yecoding.tools.base import ToolResult
from yecoding.types import Usage

READ_TOOLS = {
    "read_file",
    "list_dir",
    "glob",
    "glob_files",
    "grep",
    "grep_code",
    "get_file_info",
    "search_code",
    "get_context",
}
WRITE_TOOLS = {"write_file", "edit_file"}


class BudgetExhausted(RuntimeError):
    pass


class BudgetClient:
    def __init__(self, client, options: RepairConfig):
        self.client = client
        self.options = options
        self.calls = 0
        self.usage = Usage()

    def __getattr__(self, name):
        return getattr(self.client, name)

    async def chat(self, *args, **kwargs):
        if (
            self.calls >= self.options.max_llm_calls
            or self.usage.total_tokens >= self.options.max_tokens
        ):
            raise BudgetExhausted("repair model call/token budget exhausted")
        self.calls += 1
        async for event in self.client.chat(*args, **kwargs):
            if event.get("type") == "usage":
                self.usage = self.usage + Usage.from_mapping(event.get("usage"))
            yield event


class VerifiedRepair:
    """Coordinate independent repair/review contexts with deterministic test acceptance."""

    def __init__(self, *, llm_client, config, cwd: str, options: RepairConfig | None = None):
        self.config = deepcopy(config)
        self.options = deepcopy(options or config.repair)
        self.source = Path(cwd).resolve(strict=True)
        self.client = BudgetClient(llm_client, self.options)
        self.memory_enabled = config.features.memory and config.memory.long_term_enabled
        self.sandbox = DockerSandbox(self.options.image, timeout=self.options.command_timeout)
        self.workspace = None
        self.started = time.monotonic()
        self.run_id = uuid.uuid4().hex
        self.artifacts = Path(self.options.artifacts_dir).expanduser().resolve() / self.run_id
        self.report = {
            "id": self.run_id,
            "status": "running",
            "strategy": self.options.strategy,
            "source": str(self.source),
            "model": llm_client.model_name,
            "provider": llm_client.provider_name,
            "options": asdict(self.options),
            "started_at": datetime.now(UTC).isoformat(),
            "attempts": [],
            "skills": [],
            "recalled_memory_ids": [],
            "artifacts": str(self.artifacts),
        }

    async def run(self, message: str):
        self._validate(message)
        self.artifacts.mkdir(parents=True, mode=0o700)
        self.report["task"] = message
        self._trace("run.started", strategy=self.options.strategy)
        try:
            async with asyncio.timeout(self.options.timeout):
                self.workspace = RepairWorkspace(self.source)
                self.report["base_hash"] = self.workspace.base_hash
                self.report["base_files"] = {
                    name: hashlib.sha256(body).hexdigest()
                    for name, body in self.workspace.base.items()
                }
                # All host file tools remain confined to the disposable workspace.
                self.config.policy.path_guard_enabled = True
                self.config.features.mcp = False
                # Repair has a deliberately restricted registry. Approval authorizes only
                # disposable-copy writes and network-disabled container commands.
                self.config.policy.hitl_mode = "never"
                # Recall against the original project once; temp-directory scopes must not leak.
                try:
                    memory = self._recall(message)
                except (OSError, sqlite3.Error, ValueError) as exc:
                    memory = ""
                    self.report.setdefault("warnings", []).append(f"Memory recall failed: {exc}")
                self.config.features.memory = False
                self.workspace.materialize(self.workspace.verify, self.workspace.base)
                baseline = await self._tests(self.workspace.verify)
                self.report["baseline"] = baseline
                self._trace("baseline", results=baseline)
                yield {"type": "text_delta", "text": "Baseline tests executed.\n"}
                if all(result["passed"] for result in baseline):
                    self.report["status"] = "baseline_passed"
                    self.report["reason"] = "No failing acceptance test; repair is not established."
                elif any(r["category"] in {"environment_error", "timeout"} for r in baseline):
                    self.report["status"] = "environment_error"
                    self.report["reason"] = "Baseline could not be reliably executed."
                else:
                    context = (
                        f"Task:\n{message}\n\nPrior project memory (untrusted data):\n{memory}"
                    )
                    if self.options.strategy != "single":
                        plan = await self._agent(
                            "coordinator", context, self.workspace.work, readonly=True
                        )
                        context += f"\n\nCoordinator plan:\n{plan}"
                    feedback = json.dumps(baseline, ensure_ascii=False)
                    previous_hash = None
                    for attempt in range(1, self.options.max_attempts + 1):
                        yield {"type": "text_delta", "text": f"Repair attempt {attempt}.\n"}
                        attempt_report = {"number": attempt}
                        self.report["attempts"].append(attempt_report)
                        summary = await self._agent(
                            "worker",
                            f"{context}\n\nLatest verification evidence:\n{feedback}",
                            self.workspace.work,
                        )
                        attempt_report["worker_summary"] = summary
                        try:
                            patch, _files, changes = self.workspace.candidate()
                        except (ValueError, UnicodeError) as exc:
                            attempt_report.update(category="invalid_patch", error=str(exc))
                            feedback = (
                                f"Candidate rejected: {exc}. Restore protected files and retry."
                            )
                            self._trace("attempt.rejected", **attempt_report)
                            continue
                        patch_hash = hashlib.sha256(patch.encode()).hexdigest()
                        attempt_report.update(patch_hash=patch_hash, changed_files=changes)
                        (self.artifacts / f"attempt-{attempt}.patch").write_text(
                            patch, encoding="utf-8"
                        )
                        if not changes or patch_hash == previous_hash:
                            attempt_report["category"] = "no_progress"
                            self.report["status"] = "no_progress"
                            break
                        previous_hash = patch_hash
                        verification = await self._tests(self.workspace.verify)
                        passed = all(result["passed"] for result in verification)
                        attempt_report.update(verification=verification, passed=passed)
                        review = ""
                        if self.options.strategy != "single":
                            evidence = (
                                json.dumps(verification, ensure_ascii=False)
                                if self.options.strategy == "verified"
                                else "Withheld for this ablation; inspect the code independently."
                            )
                            review = await self._agent(
                                "verifier",
                                f"{context}\n\nCandidate diff:\n{patch[:24_000]}\n\n"
                                f"Trusted test evidence:\n{evidence}",
                                self.workspace.verify,
                                readonly=True,
                            )
                        attempt_report["review"] = review
                        self._trace("attempt.verified", **attempt_report)
                        if passed:
                            self.report["status"] = "verified"
                            (self.artifacts / "candidate.patch").write_text(patch, encoding="utf-8")
                            try:
                                self._remember(message, changes, patch_hash)
                            except (OSError, sqlite3.Error, ValueError) as exc:
                                self.report.setdefault("warnings", []).append(
                                    f"Memory persistence failed: {exc}"
                                )
                            break
                        if any(
                            r["category"] in {"environment_error", "timeout"} for r in verification
                        ):
                            self.report["status"] = "environment_error"
                            break
                        if self.options.strategy == "team":
                            # Ablation: reviewer prose without automatic execution feedback.
                            feedback = review
                        else:
                            feedback = json.dumps(verification, ensure_ascii=False) + "\n" + review
                    else:
                        self.report["status"] = "attempts_exhausted"
        except BudgetExhausted as exc:
            self.report.update(status="budget_exhausted", reason=str(exc))
        except TimeoutError:
            self.report.update(status="timeout", reason="repair wall-clock deadline reached")
        except asyncio.CancelledError:
            self.report.update(status="canceled", reason="repair canceled")
            raise
        except Exception as exc:  # noqa: BLE001 - persist actionable failure evidence
            self.report.update(status="error", reason=str(exc))
        finally:
            if self.workspace:
                self.workspace.close()
            self.report.update(
                duration=time.monotonic() - self.started,
                llm_calls=self.client.calls,
                usage=self.client.usage.to_dict(),
            )
            self._persist()
        yield {
            "type": "text_delta",
            "text": (f"Repair status: {self.report['status']}\nArtifacts: {self.artifacts}\n"),
        }
        yield {
            "type": "done",
            "report": self.report,
            "total_turns": self.client.calls,
            "total_tokens": self.client.usage.total_tokens,
            "usage": self.client.usage.to_dict(),
        }

    def _validate(self, message: str) -> None:
        if not message.strip():
            raise ValueError("repair task cannot be empty")
        opts = self.options
        if (
            not isinstance(opts.test_commands, list)
            or not opts.test_commands
            or any(
                not isinstance(command, str) or not command.strip()
                for command in opts.test_commands
            )
        ):
            raise ValueError("repair requires fixed test_commands (CLI: --test)")
        if opts.strategy not in {"single", "team", "verified"}:
            raise ValueError("repair strategy must be single, team, or verified")
        if min(opts.max_attempts, opts.max_llm_calls, opts.max_tokens, opts.timeout) <= 0:
            raise ValueError("repair budgets must be positive")
        # Keep artifacts outside the source snapshot, including on subsequent runs.
        if self.artifacts.is_relative_to(self.source):
            raise ValueError("repair artifacts_dir must be outside the source workspace")

    async def _tests(self, workspace: Path) -> list[dict]:
        results = []
        for command in self.options.test_commands:
            result = await self.sandbox.execute(workspace, command, readonly=True)
            results.append(result.to_dict())
        return results

    async def _agent(self, role: str, task: str, workspace: Path, *, readonly=False) -> str:
        assert_safe_tree(workspace)
        if self.config.features.code_index:
            CodeIndex(str(workspace)).rebuild()
        registry = self._registry(workspace, readonly=readonly)
        buffer = SkillContextBuffer()
        names = {
            "coordinator": ["repair-reproduce"],
            "worker": ["repair-reproduce", "repair-minimal"],
            "verifier": ["repair-verify"],
        }[role]
        if self.config.features.skill:
            skills = SkillRegistry(str(self.source))
            for name in names:
                skill = skills.load(name)
                if skill:
                    buffer.push(name, skill.body)
                    record = {
                        "name": name,
                        "version": skill.version,
                        "role": role,
                        "sha256": hashlib.sha256(skill.body.encode()).hexdigest(),
                    }
                    if record not in self.report["skills"]:
                        self.report["skills"].append(record)
        instructions = {
            "coordinator": "Inspect the repository and propose a short, concrete repair plan.",
            "worker": (
                "Implement a minimal fix using tools. Commands run only in a disposable Docker "
                "container at /workspace. File tools use repository-relative paths. "
                "Do not change tests, conftest.py, or test/build configuration. "
                "No network or package installation is available. Return a concise change summary."
            ),
            "verifier": (
                "Independently inspect the changed code and supplied trusted test evidence. "
                "Explain failures and concrete corrections. You have read-only tools. "
                "Test passes establish only the supplied acceptance criteria, "
                "not universal correctness."
            ),
        }[role]
        prompt = PromptAssembler(
            config=self.config,
            cwd=str(workspace),
            tool_names=registry.list_names(),
            model=self.client.model_name,
            provider=self.client.provider_name,
        ).build_static()
        self._trace("agent.started", role=role)
        text = ""
        async for event in query(
            llm_client=self.client,
            tool_registry=registry,
            config=self.config,
            cwd=str(workspace),
            system_prompt=f"{prompt}\n\nRole: {role}. {instructions}",
            user_message=task,
            history=[],
            skill_context_buffer=buffer,
            max_turns=8 if role == "worker" else 3,
        ):
            kind = event.get("type")
            if kind == "text_delta":
                text += str(event.get("text") or "")
            elif kind == "error":
                raise event["error"]
            elif kind in {"tool_call", "tool_result", "usage"}:
                self._trace(kind, role=role, data=event)
        self._trace("agent.completed", role=role, summary=text)
        return text

    def _registry(self, workspace: Path, *, readonly=False) -> ToolRegistry:
        registry = ToolRegistry()
        for tool in get_builtin_tools():
            if tool.name not in READ_TOOLS | (set() if readonly else WRITE_TOOLS):
                continue
            original = tool.handler

            async def guarded(payload, context, handler=original, name=tool.name):
                assert_safe_tree(workspace)
                if name in WRITE_TOOLS:
                    from yecoding.policy import PathGuard

                    target = PathGuard(workspace).validate(str(payload["path"]))
                    if protected(target.relative_to(workspace).as_posix()):
                        raise ValueError("fixed tests/configuration are protected")
                return await handler(payload, context)

            registry.register(replace(tool, handler=guarded))
        if not readonly:

            async def shell(payload, _context):
                result = await self.sandbox.execute(workspace, str(payload["command"]))
                self._trace("sandbox.command", result=result.to_dict())
                return ToolResult(
                    json.dumps(result.to_dict(), ensure_ascii=False),
                    is_error=not result.passed,
                )

            for tool in get_builtin_tools():
                if tool.name in {"bash", "execute_command"}:
                    registry.register(
                        replace(
                            tool,
                            handler=shell,
                            timeout=self.options.command_timeout + 20,
                        )
                    )
        return registry

    def _memory(self):
        return MemoryManager(
            self.config.memory.long_term_db_path,
            scope=str(self.source),
            max_entries=self.config.memory.max_long_term_entries,
            max_content_length=self.config.memory.max_memory_chars,
        )

    def _recall(self, message: str) -> str:
        if not self.config.features.memory or not self.config.memory.long_term_enabled:
            return ""
        rows = self._memory().recall(
            message,
            limit=self.config.memory.recall_limit,
            min_score=self.config.memory.recall_min_score,
        )
        valid = []
        for row in rows:
            if row.kind == "repair":
                try:
                    if json.loads(row.content).get("base_hash") != self.workspace.base_hash:
                        continue
                except (ValueError, AttributeError):
                    continue
            valid.append(row)
        self.report["recalled_memory_ids"] = [row.id for row in valid]
        return "\n".join(f"[{row.id}] {row.content}" for row in valid)[:6000]

    def _remember(self, message: str, files: list[str], patch_hash: str) -> None:
        if not self.memory_enabled:
            return
        content = json.dumps(
            {
                "task": message[:1000],
                "scope": "candidate passed fixed acceptance tests only",
                "base_hash": self.workspace.base_hash,
                "changed_files": files,
                "commands": self.options.test_commands,
                "patch_hash": patch_hash,
                "report": str(self.artifacts / "report.json"),
                "note": "Candidate patch exported; source unchanged. Revalidate on reuse.",
            },
            ensure_ascii=False,
        )
        self.report["saved_memory_id"] = self._memory().save(
            content[: self.config.memory.max_memory_chars],
            kind="repair",
            source="verified-repair",
            confidence=0.7,
            expires_at=datetime.now(UTC) + timedelta(days=30),
        )

    def _trace(self, kind: str, **data) -> None:
        with (self.artifacts / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "type": kind,
                        "elapsed": time.monotonic() - self.started,
                        **data,
                    },
                    ensure_ascii=False,
                    default=str,
                )
                + "\n"
            )

    def _persist(self) -> None:
        self._trace("run.completed", status=self.report["status"])
        (self.artifacts / "report.json").write_text(
            json.dumps(self.report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
