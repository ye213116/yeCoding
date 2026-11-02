from __future__ import annotations

import asyncio

from yecoding.config import load_config
from yecoding.tools import ToolRegistry, get_builtin_tools
from yecoding.tools.base import Tool, ToolContext, ToolResult
from yecoding.tools.builtins import save_memory, search_memory
from yecoding.tools.executor import ToolExecutor


def test_read_write_file_tool(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    config = load_config(project_root=tmp_path)
    config.policy.hitl_mode = "never"
    registry = ToolRegistry()
    registry.register_all(get_builtin_tools())
    context = ToolContext(cwd=str(tmp_path), config=config)

    async def run():
        write = registry.get("write_file")
        read = registry.get("read_file")
        assert write and read
        write_result = await write.execute(
            {"path": "hello.txt", "content": "hello\nworld\n"},
            context,
        )
        read_result = await read.execute({"path": "hello.txt"}, context)
        return write_result, read_result

    write_result, read_result = asyncio.run(run())
    assert not write_result.is_error
    assert "1: hello" in read_result.content
    assert "2: world" in read_result.content


def test_tool_batch_preserves_write_then_read_order(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    config = load_config(project_root=tmp_path)
    config.policy.hitl_mode = "never"
    registry = ToolRegistry()
    registry.register_all(get_builtin_tools())
    calls = [
        {
            "id": str(index),
            "function": {"name": name, "arguments": arguments},
        }
        for index, (name, arguments) in enumerate(
            [
                ("write_file", {"path": "sample.txt", "content": "first"}),
                ("read_file", {"path": "sample.txt"}),
                ("write_file", {"path": "sample.txt", "content": "second"}),
                ("read_file", {"path": "sample.txt"}),
            ]
        )
    ]

    results = asyncio.run(
        ToolExecutor(registry).execute_all(calls, ToolContext(cwd=str(tmp_path), config=config))
    )

    assert [result.tool_use_id for result in results] == ["0", "1", "2", "3"]
    assert [result.content for result in results[1::2]] == ["1: first", "1: second"]


def test_adjacent_read_tools_still_run_concurrently(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    config = load_config(project_root=tmp_path)
    active = 0
    peak = 0

    async def read(payload, context):  # noqa: ARG001
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        await asyncio.sleep(0.01)
        active -= 1
        return ToolResult(content=payload["value"])

    registry = ToolRegistry()
    registry.register(Tool(name="parallel_read", description="Read", parameters={}, handler=read))
    calls = [
        {"id": str(index), "function": {"name": "parallel_read", "arguments": {"value": value}}}
        for index, value in enumerate(("first", "second"))
    ]

    results = asyncio.run(
        ToolExecutor(registry).execute_all(calls, ToolContext(cwd=str(tmp_path), config=config))
    )

    assert peak == 2
    assert [result.content for result in results] == ["first", "second"]


def test_builtin_tools_include_memory_recall_and_skill_sedimentation():
    names = {tool.name for tool in get_builtin_tools()}

    assert "search_memory" in names
    assert "save_skill" in names


def test_memory_tools_save_metadata_and_recall_relevant_items(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    config = load_config(project_root=tmp_path)
    context = ToolContext(cwd=str(tmp_path), config=config)

    saved = asyncio.run(
        save_memory(
            {
                "content": "用户偏好用 uv 执行 Python 测试",
                "kind": "preference",
                "importance": 0.9,
            },
            context,
        )
    )
    recalled = asyncio.run(search_memory({"query": "怎么执行测试"}, context))

    assert not saved.is_error
    assert not recalled.is_error
    assert "uv" in recalled.content
    assert "preference" in recalled.content
