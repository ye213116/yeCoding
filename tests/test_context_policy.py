from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import sys
import types
from copy import deepcopy
from types import SimpleNamespace

import pytest

from yecoding.config import ContextConfig, YeCodingConfig, load_config
from yecoding.context.policy import ContextPolicy, excerpt
from yecoding.context.trace import ObservedClient, TraceRecorder
from yecoding.tools.base import ToolResult
from yecoding.types import Message


def policy(tmp_path, **options):
    config = YeCodingConfig()
    config.context = ContextConfig(strategy="evidence", **options)
    config.llm.max_tokens = 100
    return ContextPolicy(config, SimpleNamespace(max_context_window=100_000), str(tmp_path))


def history(outputs):
    messages = [Message("user", "fix parser")]
    for i, text in enumerate(outputs):
        messages.extend(
            [
                Message(
                    "assistant",
                    "",
                    tool_calls=[
                        {
                            "id": f"c{i}",
                            "type": "function",
                            "function": {"name": "bash", "arguments": '{"command":"inspect"}'},
                        }
                    ],
                ),
                Message("tool", text, tool_call_id=f"c{i}"),
            ]
        )
    return messages


@pytest.mark.parametrize("window", [700, 100_000])
def test_legacy_matches_frozen_implementation(tmp_path, window):
    revision = "7a1783bc723d358090a3c9f318d7bf795903138e"
    code = subprocess.check_output(
        ["git", "show", f"{revision}:src/yecoding/context/manager.py"], text=True
    )
    module = types.ModuleType("frozen_context_manager")
    sys.modules[module.__name__] = module
    try:
        exec(compile(code, "<frozen HEAD>", "exec"), module.__dict__)
        config = YeCodingConfig()
        config.llm.max_tokens = 100
        config.memory.compression_reserve_tokens = 10
        selected = ContextPolicy(config, SimpleNamespace(max_context_window=window), str(tmp_path))
        original = module.ContextWindowManager(
            module.ContextBudget(window, 100, reserve_tokens=10),
        )
        messages = history(["x" * 6000] * 7)
        expected = original.prepare(deepcopy(messages), system_prompt="system")
        actual = selected.prepare(deepcopy(messages), system_prompt="system")
        assert actual.request_messages == expected.messages
        assert actual.history_messages == expected.messages
        assert actual.stats["after_tokens"] == expected.estimated_tokens_after
    finally:
        del sys.modules[module.__name__]


def test_dedup_preserves_history_pairing_and_protected_results(tmp_path):
    selected = policy(tmp_path)
    messages = history(["duplicate data"] * 6)
    before = deepcopy(messages)
    result = selected.prepare(messages)
    assert result.history_messages == before == messages
    assert result.request_messages[-1] == messages[-1]
    assert sum(m.content == "duplicate data" for m in result.request_messages) == 1
    assert any(d["reason"] == "duplicate" for d in result.decisions)
    assert [m.tool_call_id for m in result.request_messages] == [m.tool_call_id for m in messages]
    selected.config.context.deduplicate = False
    assert not any(d["reason"] == "duplicate" for d in selected.prepare(messages).decisions)


def test_old_source_is_invalidated_after_external_edit(tmp_path):
    path = tmp_path / "module.py"
    path.write_text("def old(): pass\n")
    selected = policy(tmp_path)
    messages = history(["def old(): pass"] + ["other"] * 5)
    selected.observe(
        messages[1].tool_calls[0],
        ToolResult(
            messages[2].content,
            provenance=[
                {
                    "path": "module.py",
                    "version": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "start": 1,
                    "end": 1,
                }
            ],
        ),
    )
    path.write_text("def new(): pass\n")
    result = selected.prepare(messages)
    assert next(d for d in result.decisions if d["call_id"] == "c0")["reason"] == "stale_source"
    assert "def old()" not in result.request_messages[2].content
    assert "def old()" in result.history_messages[2].content


def test_recent_boundary_expands_to_include_entire_parallel_tool_block(tmp_path):
    selected = policy(tmp_path, evidence_tokens=10)
    messages = history(["result"] * 5)
    calls = [{"id": f"parallel{i}"} for i in range(10)]
    block = [Message("assistant", "", tool_calls=calls)] + [
        Message("tool", "x" * 100, tool_call_id=c["id"]) for c in calls
    ]
    messages.extend(block)
    result = selected.prepare(messages)
    assert result.history_messages[-len(block) :] == block
    assert [m.tool_call_id for m in result.request_messages[-len(block) :]] == [
        m.tool_call_id for m in block
    ]
    assert result.stats["evidence_budget_overage"] > 0


def test_long_log_excerpt_keeps_actual_tail_error():
    text = "\n".join(["irrelevant " * 10] * 100 + ["FAILED test_parser: terminal_error"])
    result, spans = excerpt(text, 80)
    assert "terminal_error" in result
    assert [101, 101] in spans


def test_opaque_commands_have_no_invented_file_sources(tmp_path):
    selected = policy(tmp_path)
    messages = history(["file.py:123\n traceback"] * 5)
    selected.observe(messages[1].tool_calls[0], ToolResult(messages[2].content, is_error=True))
    assert selected.evidence["c0"].sources == []
    assert selected.evidence["c0"].is_error


def test_structure_refreshes_after_file_changes(tmp_path):
    selected = policy(tmp_path)
    (tmp_path / "a.py").write_text("def fix(): return helper()\n")
    (tmp_path / "b.py").write_text("def helper(): return 1\n")
    selected.changed_paths.add("a.py")
    selected.evidence["x"] = SimpleNamespace(sources=[{"path": "b.py"}])
    assert "b.py" in selected._related_paths("")
    (tmp_path / "b.py").write_text("def unrelated(): return 1\n")
    assert "b.py" not in selected._related_paths("")


def test_context_overflow_is_explicit(tmp_path):
    selected = policy(tmp_path)
    selected.manager.budget = SimpleNamespace(available_input_tokens=5)
    with pytest.raises(ValueError, match="context_overflow"):
        selected.prepare([Message("user", "must retain " * 100)])


def test_environment_configuration_is_public_and_validated(tmp_path):
    config = load_config(
        tmp_path,
        env={
            "YECODING_CONTEXT_STRATEGY": "evidence",
            "YECODING_EVIDENCE_TOKENS": "100",
            "YECODING_TRACE_PATH": str(tmp_path / "trace.jsonl"),
        },
    )
    assert config.context.strategy == "evidence"
    assert config.context.evidence_tokens == 100
    with pytest.raises(ValueError, match="context.strategy"):
        ContextConfig(strategy="unknown")


def test_trace_does_not_mutate_request_and_redacts_credentials(tmp_path):
    messages = [Message("user", "secret-key-value Bearer abc password=example")]
    tools = [{"function": {"name": "read"}}]

    class Client:
        async def chat(self, passed_messages, passed_tools, *, system_prompt):
            assert passed_messages is messages
            assert passed_tools is tools
            assert system_prompt == "system"
            yield {"type": "usage", "usage": {"input_tokens": 12}}

    path = tmp_path / "trace.jsonl"
    observed = ObservedClient(Client(), TraceRecorder(path, secrets=("secret-key-value",)))

    async def run():
        return [e async for e in observed.chat(messages, tools, system_prompt="system")]

    before = deepcopy(messages)
    assert asyncio.run(run())[0]["type"] == "usage"
    assert messages == before
    content = path.read_text()
    assert "secret-key-value" not in content and "Bearer abc" not in content
    assert "password=example" not in content
    rows = [json.loads(line) for line in content.splitlines()]
    assert isinstance(rows[0]["request"]["messages"][0], dict)
    assert rows[0]["request"]["tools"] == tools


@pytest.mark.parametrize("entrypoint", ["react", "query"])
def test_loops_send_selected_view_but_return_full_history(tmp_path, entrypoint):
    from yecoding.agent.agent import Agent
    from yecoding.agent.query import query
    from yecoding.tools import ToolRegistry
    from yecoding.tools.base import Tool

    body = "Repeated tool source evidence\n" * 200
    config = YeCodingConfig()
    config.features.memory = config.features.skill = config.features.mcp = False
    config.context.strategy = "evidence"
    config.llm.max_tokens = 100
    config.llm.api_key = "test-fixture-key"

    class Client:
        model_name = provider_name = "test"
        max_context_window = 100_000
        price_profile = None

        def __init__(self):
            self.calls = []

        async def chat(self, messages, tools, *, system_prompt):
            self.calls.append(deepcopy(messages))
            number = len(self.calls)
            if number <= 4:
                yield {
                    "type": "tool_call_delta",
                    "tool_call": {
                        "index": 0,
                        "id": f"c{number}",
                        "function": {"name": "inspect", "arguments": "{}"},
                    },
                }
                yield {"type": "message_end", "stop_reason": "tool_use"}
            else:
                yield {"type": "message_end", "stop_reason": "end_turn"}

    async def handler(payload, context):
        return ToolResult(body)

    registry = ToolRegistry()
    registry.register(Tool("inspect", "Inspect", {"type": "object"}, handler))
    client = Client()

    async def run():
        if entrypoint == "react":
            stream = Agent(
                llm_client=client, tool_registry=registry, config=config, cwd=str(tmp_path)
            ).run("inspect")
        else:
            stream = query(
                llm_client=client,
                tool_registry=registry,
                config=config,
                cwd=str(tmp_path),
                history=None,
                system_prompt="system",
                user_message="inspect",
            )
        return [event async for event in stream]

    events = asyncio.run(run())
    final = next(e for e in events if e["type"] == "done")
    assert sum(m.content == body for m in client.calls[-1]) == 1
    assert sum(m.content == body for m in final["messages"]) == 4
