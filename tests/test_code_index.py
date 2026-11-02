from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from yecoding.rag import CodeIndex, CodeSearchResult

CORE_PY = '''"""Core domain objects."""

MAX_SIZE = 10


class Engine:
    """A sample engine."""

    def __init__(self):
        self.started = False

    def start(self):
        self.helper()

    def helper(self):
        return load_config()


class TurboEngine(Engine):
    """Turbo variant inheriting from Engine."""

    def boost(self):
        return self.helper()


def load_config():
    return MAX_SIZE
'''

SERVICE_PY = '''"""Service layer."""

from core import Engine, load_config


def run():
    engine = Engine()
    engine.start()
    return load_config()
'''

PROJECT_FILES = {
    "app/core.py": CORE_PY,
    "app/service.py": SERVICE_PY,
    "notes.md": "# Notes\n\nMAX_SIZE is the engine limit.\n",
}


@pytest.fixture()
def index(tmp_path: Path) -> CodeIndex:
    for rel, content in PROJECT_FILES.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    index = CodeIndex(tmp_path)
    index.rebuild()
    return index


def _symbols_by_qualified(index: CodeIndex) -> dict[str, object]:
    return {symbol.qualified_name: symbol for symbol in index.list_symbols(limit=200)}


def test_rebuild_extracts_file_class_function_variable_symbols(index: CodeIndex):
    symbols = _symbols_by_qualified(index)

    assert symbols["core"].kind == "file"
    assert symbols["core"].docstring == "Core domain objects."
    assert symbols["core.Engine"].kind == "class"
    assert symbols["core.Engine"].signature == "class Engine"
    assert symbols["core.Engine"].docstring == "A sample engine."
    assert symbols["core.Engine.start"].kind == "method"
    assert symbols["core.Engine.start"].signature == "def start(self)"
    assert symbols["core.Engine.start"].parent == "core.Engine"
    assert symbols["core.load_config"].kind == "function"
    assert symbols["core.load_config"].signature == "def load_config()"
    assert symbols["core.MAX_SIZE"].kind == "variable"
    assert symbols["core.MAX_SIZE"].signature == "MAX_SIZE = 10"
    assert symbols["core.TurboEngine"].signature == "class TurboEngine(Engine)"
    assert symbols["service.run"].kind == "function"


def test_import_edges_are_recorded(index: CodeIndex):
    with sqlite3.connect(index.db_path) as conn:
        rows = {
            row[0] for row in conn.execute("select dst from edges where kind = 'import'").fetchall()
        }
    assert "core.Engine" in rows
    assert "core.load_config" in rows


def test_same_file_calls_resolve_to_symbols(index: CodeIndex):
    callees = {symbol.qualified_name for symbol in index.callees("core.Engine.helper")}
    assert "core.load_config" in callees


def test_self_calls_resolve_within_class(index: CodeIndex):
    callees = {symbol.qualified_name for symbol in index.callees("core.Engine.start")}
    assert "core.Engine.helper" in callees


def test_self_calls_resolve_through_base_class(index: CodeIndex):
    callees = {symbol.qualified_name for symbol in index.callees("core.TurboEngine.boost")}
    assert "core.Engine.helper" in callees


def test_cross_file_calls_resolve_via_unique_names(index: CodeIndex):
    callees = {symbol.qualified_name for symbol in index.callees("service.run")}
    assert "core.Engine" in callees
    assert "core.load_config" in callees


def test_callers_include_same_file_and_cross_file_sites(index: CodeIndex):
    callers = {symbol.qualified_name for symbol in index.callers("core.load_config")}
    assert "core.Engine.helper" in callers
    assert "service.run" in callers


def test_search_ranks_exact_symbol_matches_first(index: CodeIndex):
    results = index.search("Engine", limit=20)

    assert results
    assert isinstance(results[0], CodeSearchResult)
    assert results[0].snippet == "class Engine"
    assert results[0].path == "app/core.py"
    assert all(isinstance(result.snippet, str) and "\n" not in result.snippet for result in results)


def test_search_deduplicates_symbol_and_line_hits(index: CodeIndex):
    results = index.search("load_config", limit=20)
    seen = [(result.path, result.line) for result in results]

    assert len(seen) == len(set(seen))
    assert results[0].snippet == "def load_config()"
    assert ("app/core.py", results[0].line) in seen


def test_search_falls_back_to_line_chunks(index: CodeIndex):
    results = index.search("engine limit", limit=20)

    assert results
    assert any(result.path == "notes.md" for result in results)


def test_search_with_dependencies_expands_callees_and_callers(index: CodeIndex):
    run_results = index.search_with_dependencies("run", limit=5)
    run = next(item for item in run_results if item.symbol.qualified_name == "service.run")
    dependency_snippets = {dep.snippet for dep in run.dependencies}

    assert "class Engine" in dependency_snippets
    assert "def load_config()" in dependency_snippets

    helper_results = index.search_with_dependencies("helper", limit=5)
    helper = next(
        item for item in helper_results if item.symbol.qualified_name == "core.Engine.helper"
    )
    caller_snippets = {dep.snippet for dep in helper.dependencies}
    assert "def start(self)" in caller_snippets
    assert "def boost(self)" in caller_snippets


def test_syntax_error_file_falls_back_to_line_chunks(tmp_path: Path):
    (tmp_path / "bad.py").write_text("def broken(:\n", encoding="utf-8")
    (tmp_path / "good.py").write_text("value = 1\n", encoding="utf-8")

    index = CodeIndex(tmp_path)
    index.rebuild()

    results = index.search("broken", limit=5)
    assert results and results[0].path == "bad.py"


def test_skip_dirs_are_not_indexed(tmp_path: Path):
    vendor = tmp_path / "node_modules" / "leftpad.py"
    vendor.parent.mkdir(parents=True)
    vendor.write_text("def pad():\n    return None\n", encoding="utf-8")

    index = CodeIndex(tmp_path)
    index.rebuild()

    assert index.list_symbols(limit=50) == []
    assert index.search("pad", limit=10) == []


def test_rebuild_rejects_paths_outside_root(tmp_path: Path):
    outside = tmp_path.parent / "outside.py"
    outside.write_text("value = 1\n", encoding="utf-8")

    index = CodeIndex(tmp_path)

    with pytest.raises(ValueError):
        index.rebuild("../outside.py")


def test_rebuild_is_idempotent(index: CodeIndex):
    first = index.rebuild()
    second = index.rebuild()

    assert first == second
    symbols = index.list_symbols(limit=200)
    qualified = [symbol.qualified_name for symbol in symbols]
    assert len(qualified) == len(set(qualified))


def test_parse_python_module_on_this_repository():
    from yecoding.rag import parse_python_module

    source = Path("src/yecoding/rag/parser.py").read_text(encoding="utf-8")
    module = parse_python_module("src/yecoding/rag/parser.py", source)

    kinds = {symbol.kind for symbol in module.symbols}
    assert {"file", "class", "function"} <= kinds
    assert any(relation.dst == "ast" for relation in module.relations)
