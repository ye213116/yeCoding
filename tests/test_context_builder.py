from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from yecoding.config import load_config
from yecoding.context import estimate_text_tokens
from yecoding.rag import CodeIndex, ContextBuilder, ContextPackConfig
from yecoding.tools import ToolRegistry, get_builtin_tools
from yecoding.tools.base import ToolContext

CORE_PY = '''"""Core domain objects for packing tests."""

MAX_SIZE = 10


class Engine:
    """A sample engine."""

    def __init__(self):
        self.started = False

    def start(self):
        self.helper()

    def helper(self):
        return load_config()


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


@pytest.fixture()
def index(tmp_path: Path) -> CodeIndex:
    for rel, content in {"app/core.py": CORE_PY, "app/service.py": SERVICE_PY}.items():
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    index = CodeIndex(tmp_path)
    index.rebuild()
    return index


def test_build_returns_prioritized_sections(index: CodeIndex):
    pack = ContextBuilder(index).build("run", 4000)

    assert pack.text.startswith("<code-context ")
    assert "## Matching symbols" in pack.text
    assert "## Call chains" in pack.text
    assert "## Source excerpts" in pack.text
    assert "## File summaries" in pack.text
    assert "service.run" in pack.text
    # run() calls Engine and load_config, both must appear as dependencies.
    assert "run calls core.Engine" in pack.text
    assert "run calls core.load_config" in pack.text


def test_call_chains_include_reverse_direction(index: CodeIndex):
    pack = ContextBuilder(index).build("helper", 4000)

    assert "helper calls core.load_config" in pack.text
    # Engine.start calls helper -> reverse relation must be packed too.
    assert "helper called by core.Engine.start" in pack.text


def test_dependency_ablation_keeps_retrieval_and_sources(index: CodeIndex):
    full = ContextBuilder(index).build("run", 4000)
    ablated = ContextBuilder(index, ContextPackConfig(include_dependencies=False)).build(
        "run", 4000
    )
    assert full.dependency_count > 0
    assert ablated.dependency_count == 0
    assert ablated.symbols_included == full.symbols_included
    assert ablated.source_symbols == full.source_symbols
    assert "## Call chains" not in ablated.text
    assert "core.load_config" not in ablated.text
    assert ablated.token_estimate <= ablated.budget_tokens


def test_pack_respects_token_budget(index: CodeIndex):
    pack = ContextBuilder(index).build("Engine helper run load_config", 400)

    assert pack.token_estimate <= pack.budget_tokens
    assert pack.token_estimate > 0
    assert estimate_text_tokens(pack.text) >= pack.token_estimate - 96


def test_tight_budget_keeps_signatures_and_flags_truncation(index: CodeIndex):
    pack = ContextBuilder(index).build("Engine helper run load_config", 200)

    assert pack.truncated
    # Signatures are the highest-priority stage: at least one must survive.
    assert pack.symbols_included
    assert "## Matching symbols" in pack.text


def test_source_excerpts_are_limited_to_top_k(index: CodeIndex):
    config = ContextPackConfig(source_top_k=1, max_source_lines_per_symbol=10)
    pack = ContextBuilder(index, config).build("Engine helper run load_config", 8000)

    assert len(pack.source_symbols) <= 1


def test_budget_floor_prevents_impossible_requests(index: CodeIndex):
    pack = ContextBuilder(index).build("run", 0)

    # The builder clamps to a floor instead of crashing or returning garbage.
    assert pack.budget_tokens >= 128


def test_empty_index_returns_empty_pack(tmp_path: Path):
    (tmp_path / "empty.py").write_text("x = 1\n", encoding="utf-8")
    index = CodeIndex(tmp_path)
    index.rebuild()

    pack = ContextBuilder(index).build("no_such_symbol_anywhere", 1000)

    assert pack.text == ""
    assert pack.symbols_included == []


def test_get_context_tool_registered_and_executes(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "core.py").write_text(SERVICE_PY, encoding="utf-8")
    index = CodeIndex(tmp_path)
    index.rebuild()

    config = load_config(project_root=tmp_path)
    config.policy.hitl_mode = "never"
    registry = ToolRegistry()
    registry.register_all(get_builtin_tools())
    context = ToolContext(cwd=str(tmp_path), config=config)
    tool = registry.get("get_context")
    assert tool is not None

    result = asyncio.run(tool.execute({"query": "run", "budget_tokens": 2000}, context))

    assert not result.is_error
    assert "<code-context" in result.content
    assert "run" in result.content
