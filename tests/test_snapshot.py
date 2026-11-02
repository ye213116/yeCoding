from __future__ import annotations

import shutil
from pathlib import Path

from yecoding.snapshot import SnapshotService


def test_snapshot_restore(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    project = tmp_path / "project"
    project.mkdir()
    file_path = project / "note.txt"
    file_path.write_text("before", encoding="utf-8")

    service = SnapshotService(project)
    first = service.create("pre-turn")
    file_path.write_text("after", encoding="utf-8")

    restored = service.restore(first.id)

    assert restored.id == first.id
    assert file_path.read_text(encoding="utf-8") == "before"


def test_snapshot_storage_inside_project_is_never_copied_or_deleted(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    file_path = tmp_path / "note.txt"
    file_path.write_text("before")
    service = SnapshotService(tmp_path)
    original = shutil.copytree

    def no_recursive_copy(source, destination, *args, **kwargs):
        assert not Path(destination).is_relative_to(Path(source)), "snapshot copies its own storage"
        return original(source, destination, *args, **kwargs)

    monkeypatch.setattr(shutil, "copytree", no_recursive_copy)
    record = service.create("pre-turn")
    assert not (record.path / "home").exists()
    file_path.write_text("after")
    service.restore(record.id)
    assert file_path.read_text() == "before"
    assert service.index_path.exists()
