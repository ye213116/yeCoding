from __future__ import annotations

import difflib
import hashlib
import os
import shutil
import stat
import tempfile
from pathlib import Path

IGNORED = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".yecoding",
    "dist",
    "build",
    ".coverage",
}


def excluded(name: str) -> bool:
    return name in IGNORED or name.startswith(".env") or name.endswith((".pem", ".key", ".pyc"))


def assert_safe_tree(root: Path) -> None:
    count = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            count += 1
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if count > 20_000:
                raise ValueError("workspace tree exceeds safety scan limit")
            if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise ValueError("workspace contains a link or special file")


def inventory(root: Path) -> dict[str, bytes]:
    """Bounded snapshots; reject links/special files before host-side tools can follow them."""
    result = {}
    total = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            path = Path(directory) / name
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
                raise ValueError(f"workspace links and special files are unsupported: {path.name}")
        dirs[:] = sorted(name for name in dirs if not excluded(name))
        for name in sorted(files):
            if excluded(name):
                continue
            path = Path(directory) / name
            relative = path.relative_to(root).as_posix()
            if any(ord(c) < 32 for c in relative) or '"' in relative or "\\" in relative:
                raise ValueError("unsupported workspace filename")
            size = path.stat().st_size
            total += size
            if size > 2_000_000 or total > 100_000_000 or len(result) >= 10_000:
                raise ValueError("workspace snapshot exceeds file/count/size limits")
            result[relative] = path.read_bytes()
    return result


def fingerprint(files: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name, body in sorted(files.items()):
        digest.update(name.encode() + b"\0" + hashlib.sha256(body).digest())
    return digest.hexdigest()


def protected(path: str) -> bool:
    p = Path(path)
    return (
        any(part in {"tests", "test"} for part in p.parts)
        or p.name.startswith("test_")
        or p.name.endswith("_test.py")
        or p.name in {"conftest.py", "pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"}
    )


class RepairWorkspace:
    def __init__(self, source: Path):
        self.source = source.resolve(strict=True)
        self.base = inventory(self.source)
        self._temp = tempfile.TemporaryDirectory(prefix="yecoding-repair-")
        self.root = Path(self._temp.name)
        self.work = self.root / "work"
        self.verify = self.root / "verify"
        self.base_hash = fingerprint(self.base)
        self.materialize(self.work, self.base)

    @staticmethod
    def materialize(target: Path, files: dict[str, bytes]) -> None:
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        for name, body in files.items():
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)

    def candidate(self) -> tuple[str, dict[str, bytes], list[str]]:
        assert_safe_tree(self.work)
        current = inventory(self.work)
        changes = [
            name
            for name in sorted(self.base.keys() | current.keys())
            if self.base.get(name) != current.get(name)
        ]
        forbidden = [name for name in changes if protected(name)]
        if forbidden:
            raise ValueError(f"fixed tests/configuration cannot be changed: {', '.join(forbidden)}")
        patch = []
        for name in changes:
            old, new = self.base.get(name, b""), current.get(name, b"")
            if b"\0" in old + new:
                raise ValueError(f"binary changes are unsupported: {name}")
            old_text, new_text = old.decode("utf-8"), new.decode("utf-8")
            patch.append(f"diff --git a/{name} b/{name}\n")
            if name not in self.base:
                patch.append("new file mode 100644\n")
            elif name not in current:
                patch.append("deleted file mode 100644\n")
            lines = difflib.unified_diff(
                old_text.splitlines(keepends=True),
                new_text.splitlines(keepends=True),
                fromfile=f"a/{name}" if name in self.base else "/dev/null",
                tofile=f"b/{name}" if name in current else "/dev/null",
            )
            for line in lines:
                patch.append(
                    line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
                )
        self.materialize(self.verify, current)
        return "".join(patch), current, changes

    def close(self) -> None:
        self._temp.cleanup()
