"""Compare actual loop requests against the immutable pre-refactor source."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from eval.context_protocol import BASELINE

SCRIPT = """
import asyncio,json,sys
from dataclasses import asdict
from yecoding.agent.agent import Agent
from yecoding.agent.query import query
from yecoding.config import YeCodingConfig
from yecoding.prompt import PromptAssembler
from yecoding.tools import ToolRegistry
from yecoding.tools.base import Tool,ToolResult
from yecoding.types import Message
cfg=YeCodingConfig()
cfg.features.memory=cfg.features.skill=cfg.features.mcp=False
cfg.llm.max_tokens=100
cfg.memory.compression_reserve_tokens=50
cfg.llm.api_key="test-secret"
if sys.argv[3]=="trace" and hasattr(cfg,"context"):
    cfg.context.trace_path=sys.argv[2]+"/trace.jsonl"
PromptAssembler.build_dynamic=lambda self,message:"fixed dynamic context"
class Client:
    model_name="fixture"
    provider_name="fixture"
    max_context_window=4000
    price_profile=None
    def __init__(self): self.calls=[]
    async def chat(self,messages,tools,*,system_prompt):
        self.calls.append({"messages":[asdict(m) for m in messages],
                           "tools":tools,"system_prompt":system_prompt})
        number=len(self.calls)
        if number<=5:
            yield {"type":"tool_call_delta","tool_call":{"index":0,"id":f"c{number}",
                   "function":{"name":"inspect","arguments":"{}"}}}
            yield {"type":"message_end","stop_reason":"tool_use"}
        else:
            yield {"type":"text_delta","text":"done"}
            yield {"type":"message_end","stop_reason":"end_turn"}
async def handler(payload,context): return ToolResult("tool evidence "*800)
registry=ToolRegistry()
registry.register(Tool("inspect","Inspect",{"type":"object"},handler))
client=Client()
history=[Message("user","old task"),Message("assistant","old findings "*400)]
async def run():
    if sys.argv[1]=="react":
        agent=Agent(llm_client=client,tool_registry=registry,config=cfg,cwd=sys.argv[2],
                    system_prompt="fixed system")
        agent.history=history
        stream=agent._run_react("current task")
    else:
        stream=query(llm_client=client,tool_registry=registry,config=cfg,cwd=sys.argv[2],
                     system_prompt="fixed system",user_message="current task",history=history)
    async for event in stream: pass
asyncio.run(run())
print(json.dumps(client.calls))
"""


@pytest.fixture(scope="module")
def frozen_source(tmp_path_factory):
    root = tmp_path_factory.mktemp("frozen-context")
    body = subprocess.check_output(["git", "archive", BASELINE, "src/"])
    with tarfile.open(fileobj=io.BytesIO(body)) as archive:
        archive.extractall(root, filter="data")
    return root / "src"


@pytest.mark.parametrize("mode", ["react", "query"])
@pytest.mark.parametrize("trace", ["trace", "no-trace"])
def test_legacy_loop_sends_same_requests_as_frozen_head(frozen_source, tmp_path, mode, trace):
    current = Path(__file__).resolve().parents[1] / "src"
    results = []
    for source in [frozen_source, current]:
        environment = {**os.environ, "PYTHONPATH": str(source)}
        output = subprocess.check_output(
            [sys.executable, "-c", SCRIPT, mode, str(tmp_path), trace], env=environment, text=True
        )
        results.append(json.loads(output))
    assert len(results[0]) == len(results[1]) == 6
    assert results[0] == results[1]
