from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True)
class ExecutionResult:
    command: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    duration: float = 0.0

    @property
    def passed(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    @property
    def category(self) -> str:
        if self.timed_out:
            return "timeout"
        if self.exit_code in {125, 126, 127, 137, 143} or any(
            marker in self.stderr
            for marker in ("No module named pytest", "No module named unittest")
        ):
            return "environment_error"
        return "passed" if self.passed else "test_failure"

    def to_dict(self) -> dict:
        return {**asdict(self), "category": self.category, "passed": self.passed}


class DockerSandbox:
    """Run each command in a disposable container; never fall back to host execution."""

    def __init__(self, image: str = "python:3.11-slim", *, timeout: float = 60):
        if not image or image.startswith("-") or any(c.isspace() for c in image):
            raise ValueError("invalid sandbox image")
        if timeout <= 0:
            raise ValueError("sandbox timeout must be positive")
        self.image = image
        self.timeout = timeout

    def arguments(self, workspace: Path, name: str, command: str, *, readonly=False) -> list[str]:
        root = workspace.resolve(strict=True)
        if "," in str(root):
            raise ValueError("sandbox workspace path cannot contain commas")
        mount = f"type=bind,src={root},dst=/workspace"
        if readonly:
            mount += ",readonly"
        return [
            "docker",
            "run",
            "--rm",
            "--pull=never",
            "--name",
            name,
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=128",
            "--memory=512m",
            "--cpus=1",
            "--log-driver=none",
            "--user",
            f"{os.getuid()}:{os.getgid()}",
            "--tmpfs",
            "/tmp:rw,nosuid,size=67108864",
            "--mount",
            mount,
            "--workdir",
            "/workspace",
            "--env",
            "HOME=/tmp",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "--env",
            "PYTHONUNBUFFERED=1",
            "--env",
            "PYTHONPATH=/workspace",
            "--env",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
            "--entrypoint",
            "/bin/sh",
            self.image,
            "-c",
            command,
        ]

    async def execute(self, workspace: Path, command: str, *, readonly=False) -> ExecutionResult:
        if not command.strip():
            raise ValueError("sandbox command cannot be empty")
        name = f"yecoding-{uuid.uuid4().hex}"
        started = time.monotonic()
        proc = await asyncio.create_subprocess_exec(
            *self.arguments(workspace, name, command, readonly=readonly),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        async def drain(stream) -> str:
            captured = bytearray()
            truncated = False
            while chunk := await stream.read(8192):
                remaining = max(0, 20_000 - len(captured))
                captured.extend(chunk[:remaining])
                truncated |= len(chunk) > remaining
            return captured.decode("utf-8", errors="replace") + (
                "\n[output truncated]" if truncated else ""
            )

        readers = [asyncio.create_task(drain(proc.stdout)), asyncio.create_task(drain(proc.stderr))]
        timed_out = False
        try:
            await asyncio.wait_for(proc.wait(), self.timeout)
        except TimeoutError:
            timed_out = True
        finally:
            # Removing the named container kills descendants, including background processes.
            cleanup = asyncio.create_task(self._remove(name))
            try:
                await asyncio.shield(cleanup)
            except asyncio.CancelledError:
                await cleanup
                raise
            finally:
                if proc.returncode is None:
                    proc.kill()
                await proc.wait()
                await asyncio.gather(*readers)
        return ExecutionResult(
            command,
            124 if timed_out else proc.returncode,
            readers[0].result(),
            readers[1].result(),
            timed_out,
            time.monotonic() - started,
        )

    @staticmethod
    async def _remove(name: str) -> None:
        proc = await asyncio.create_subprocess_exec(
            "docker",
            "rm",
            "--force",
            name,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(proc.wait(), 10)
        except TimeoutError:
            proc.kill()
            await proc.wait()
