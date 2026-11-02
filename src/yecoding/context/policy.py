"""Per-session context selection, independent of model and tool execution."""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path

from yecoding.context.manager import (
    ContextBudget,
    ContextWindowManager,
    estimate_text_tokens,
)
from yecoding.types import Message


@dataclass(slots=True)
class PreparedContext:
    request_messages: list[Message]
    history_messages: list[Message]
    stats: dict = field(default_factory=dict)
    decisions: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class Evidence:
    call_id: str
    name: str
    sha256: str
    sequence: int
    is_error: bool
    sources: list[dict] = field(default_factory=list)


class ContextPolicy:
    def __init__(self, config, client, cwd: str):
        self.config = config
        self.cwd = Path(cwd).resolve()
        self.evidence: dict[str, Evidence] = {}
        self.changed_paths: set[str] = set()
        self.manager = ContextWindowManager(
            ContextBudget(
                context_window=client.max_context_window,
                max_output_tokens=config.llm.max_tokens,
                compression_threshold=config.memory.compression_threshold,
                compression_target=config.memory.compression_target,
                reserve_tokens=config.memory.compression_reserve_tokens,
            ),
            max_history_messages=config.memory.max_conversation_history,
            min_recent_messages=config.memory.min_recent_messages,
            summary_max_chars=config.memory.summary_max_chars,
        )

    def observe(self, call: dict, result) -> None:
        function = call.get("function", {})
        name = str(function.get("name", ""))
        try:
            arguments = function.get("arguments", "{}")
            payload = json.loads(arguments) if isinstance(arguments, str) else arguments
        except (TypeError, ValueError):
            payload = {}
        if (
            name in {"write_file", "edit_file"}
            and not result.is_error
            and isinstance(payload, dict)
            and payload.get("path")
            and not payload.get("dry_run")
        ):
            self.changed_paths.add(self._relative(str(payload["path"])))
        self.evidence[str(call.get("id", ""))] = Evidence(
            call_id=str(call.get("id", "")),
            name=name,
            sha256=hashlib.sha256(result.content.encode()).hexdigest(),
            sequence=len(self.evidence),
            is_error=result.is_error,
            sources=deepcopy(getattr(result, "provenance", [])),
        )
        if (
            self.config.context.strategy == "evidence"
            and self.config.context.use_structure
            and self.config.features.code_index
        ):
            self._annotate_symbols(self.evidence[str(call.get("id", ""))].sources)

    def _annotate_symbols(self, sources):
        from yecoding.rag.parser import parse_python_module

        for source in sources:
            path = (self.cwd / source["path"]).resolve()
            if not path.is_relative_to(self.cwd) or path.suffix != ".py":
                continue
            try:
                body = path.read_bytes()
                if len(body) > 1_000_000 or hashlib.sha256(body).hexdigest() != source["version"]:
                    continue
                parsed = parse_python_module(source["path"], body.decode("utf-8"))
                source["symbols"] = [
                    s.qualified_name
                    for s in parsed.symbols
                    if s.kind != "file"
                    and s.line <= source.get("end", 0)
                    and s.end_line >= source.get("start", 1)
                ]
            except (OSError, SyntaxError, UnicodeError, ValueError, RecursionError):
                continue

    def prepare(self, messages, *, task="", system_prompt="", tool_definitions=None):
        tools = tool_definitions or []
        before = self.manager._estimate_request(messages, system_prompt, tools)
        if not self.config.features.context_compression:
            return PreparedContext(list(messages), list(messages), {"strategy": "disabled"})
        if self.config.context.strategy == "legacy":
            result = self.manager.prepare(
                messages, system_prompt=system_prompt, tool_definitions=tools
            )
            return PreparedContext(
                result.messages,
                result.messages,
                {
                    "strategy": "legacy",
                    "before_tokens": result.estimated_tokens_before,
                    "after_tokens": result.estimated_tokens_after,
                    "compressed": result.compressed,
                    "summarized_messages": result.summarized_messages,
                },
            )

        selected = deepcopy(messages)
        protected = self._protected(messages)
        candidates = [i for i, m in enumerate(messages) if m.role == "tool" and i not in protected]
        related = (
            self._related_paths(task)
            if self.config.context.use_structure and self.config.features.code_index
            else set()
        )
        words = set(re.findall(r"[a-zA-Z_][\w.]{2,}", task.lower()))
        latest_failure = max(
            (item.sequence for item in self.evidence.values() if item.is_error), default=-1
        )

        def priority(i):
            message = messages[i]
            item = self.evidence.get(message.tool_call_id or "")
            paths = {s["path"] for s in item.sources} if item else set()
            return (
                bool(item and item.is_error and item.sequence == latest_failure),
                bool(paths & (related | self.changed_paths)),
                len(words & set(re.findall(r"[\w.]+", str(message.content).lower()))),
                i,
            )

        seen: dict[str, str] = {}
        decisions = []
        # Preserve complete recent blocks; mark obsolete snapshots even when protected.
        for i in sorted(protected, reverse=True):
            if messages[i].role == "tool":
                message = messages[i]
                item = self.evidence.get(message.tool_call_id or "")
                stale = bool(item and any(self._stale(s) for s in item.sources))
                content_hash = hashlib.sha256(str(message.content).encode()).hexdigest()
                if stale:
                    selected[
                        i
                    ].content = "[Historical evidence omitted: source version has changed.]"
                    reason = "protected_stale"
                elif self.config.context.deduplicate and content_hash in seen:
                    selected[
                        i
                    ].content = (
                        f"[Duplicate evidence; retained in tool result {seen[content_hash]}.]"
                    )
                    reason = "duplicate"
                else:
                    seen[content_hash] = message.tool_call_id or str(i)
                    reason = "protected"
                decisions.append(
                    {
                        "call_id": message.tool_call_id,
                        "sha256": content_hash,
                        "reason": reason,
                        "retained_output_lines": (
                            [[1, len(str(message.content).splitlines())]]
                            if reason == "protected"
                            else []
                        ),
                        "omitted_output_lines": (
                            [[1, len(str(message.content).splitlines())]]
                            if reason != "protected" and str(message.content).splitlines()
                            else []
                        ),
                        "evidence": asdict(item) if item else None,
                        "before_tokens": estimate_text_tokens(str(message.content)),
                        "after_tokens": estimate_text_tokens(str(selected[i].content)),
                    }
                )
        protected_tokens = sum(
            estimate_text_tokens(str(selected[i].content))
            for i in protected
            if messages[i].role == "tool"
        )
        remaining = max(0, self.config.context.evidence_tokens - protected_tokens)
        for i in sorted(candidates, key=priority, reverse=True):
            message = messages[i]
            text = str(message.content)
            item = self.evidence.get(message.tool_call_id or "")
            digest = hashlib.sha256(text.encode()).hexdigest()
            reason = "retained"
            spans = []
            stale = bool(item and any(self._stale(s) for s in item.sources))
            if stale:
                content = "[Evidence omitted: source version changed; read the current file.]"
                reason = "stale_source"
            elif self.config.context.deduplicate and digest in seen:
                content = f"[Duplicate evidence; retained in tool result {seen[digest]}.]"
                reason = "duplicate"
            elif estimate_text_tokens(text) <= remaining:
                content = text
                remaining -= estimate_text_tokens(content)
                seen[digest] = message.tool_call_id or str(i)
                spans = [[1, len(text.splitlines())]]
            else:
                content, spans = excerpt(text, remaining)
                remaining = max(0, remaining - estimate_text_tokens(content))
                reason = "excerpt" if spans else "budget"
            selected[i].content = content
            decisions.append(
                {
                    "call_id": message.tool_call_id,
                    "sha256": digest,
                    "reason": reason,
                    "retained_output_lines": spans,
                    "omitted_output_lines": omitted_ranges(len(text.splitlines()), spans),
                    "evidence": asdict(item) if item else None,
                    "before_tokens": estimate_text_tokens(text),
                    "after_tokens": estimate_text_tokens(content),
                }
            )
        after = self.manager._estimate_request(selected, system_prompt, tools)
        # The hard model input limit is shared by both policies; never break tool pairing.
        if after > self.manager.budget.available_input_tokens:
            raise ValueError("context_overflow: protected context exceeds model input budget")
        tool_tokens = sum(
            estimate_text_tokens(str(m.content)) for m in selected if m.role == "tool"
        )
        return PreparedContext(
            selected,
            list(messages),
            {
                "strategy": "evidence",
                "before_tokens": before,
                "after_tokens": after,
                "compressed": before != after,
                "summarized_messages": 0,
                "evidence_budget": self.config.context.evidence_tokens,
                "protected_tool_tokens": protected_tokens,
                "selected_tool_tokens": tool_tokens,
                "evidence_budget_overage": max(
                    0, tool_tokens - self.config.context.evidence_tokens
                ),
            },
            decisions,
        )

    def _protected(self, messages):
        start = max(0, len(messages) - max(2, self.config.memory.min_recent_messages))
        protected = set(range(start, len(messages)))
        protected.update(i for i, m in enumerate(messages) if m.role in {"user", "system"})
        # A tool block can start before the recent-message boundary.
        for i, message in enumerate(messages):
            if message.tool_calls:
                ids = {str(c.get("id", "")) for c in message.tool_calls}
                results = {j for j, m in enumerate(messages) if m.tool_call_id in ids}
                if i in protected or results & protected:
                    protected.add(i)
                    protected.update(results)
        return protected

    def _relative(self, value):
        path = Path(value)
        if not path.is_absolute():
            return path.as_posix()
        try:
            return path.relative_to(self.cwd).as_posix()
        except ValueError:
            return value

    def _stale(self, source):
        path = (self.cwd / source["path"]).resolve()
        if not path.is_relative_to(self.cwd) and self.config.policy.path_guard_enabled:
            return True
        try:
            return hashlib.sha256(path.read_bytes()).hexdigest() != source["version"]
        except OSError:
            return True

    def _related_paths(self, task):
        # Refresh source structure after edits; no persisted index or extra model calls.
        from yecoding.rag.parser import parse_python_module

        names = set(re.findall(r"[A-Za-z_]\w*", task))
        relations = set()
        for relative in sorted(self.changed_paths):
            path = self.cwd / relative
            if path.suffix != ".py" or not path.resolve().is_relative_to(self.cwd):
                continue
            try:
                module = parse_python_module(relative, path.read_text())
                names.update(s.name for s in module.symbols)
                relations.update(r.dst.rsplit(".", 1)[-1] for r in module.relations)
            except (OSError, SyntaxError, ValueError):
                continue
        related = set(self.changed_paths)
        paths = {s["path"] for e in self.evidence.values() for s in e.sources}
        for relative in sorted(paths):
            path = self.cwd / relative
            if path.suffix != ".py" or not path.resolve().is_relative_to(self.cwd):
                continue
            try:
                module = parse_python_module(relative, path.read_text())
                if any(s.name in names | relations for s in module.symbols):
                    related.add(relative)
            except (OSError, SyntaxError, ValueError):
                continue
        return related


def excerpt(text: str, tokens: int) -> tuple[str, list[list[int]]]:
    marker = "[Evidence excerpt; omitted output lines are not available in this request.]"
    if tokens < estimate_text_tokens(marker) + 16:
        return "[Evidence omitted: selection budget exhausted.]", []
    lines = text.splitlines()
    chosen: dict[int, str] = {}
    # Tail first preserves test failures after large command output, then the header.
    order = list(reversed(range(max(0, len(lines) - 20), len(lines)))) + list(
        range(min(10, len(lines)))
    )
    remaining = tokens - estimate_text_tokens(marker) - 4
    for i in order:
        if i in chosen:
            continue
        cost = estimate_text_tokens(lines[i] + "\n")
        if cost <= remaining:
            chosen[i] = lines[i]
            remaining -= cost
    return marker + "\n" + "\n".join(chosen[i] for i in sorted(chosen)), [
        [i + 1, i + 1] for i in sorted(chosen)
    ]


def omitted_ranges(total: int, retained: list[list[int]]) -> list[list[int]]:
    missing = []
    cursor = 1
    for start, end in sorted(retained):
        if cursor < start:
            missing.append([cursor, start - 1])
        cursor = max(cursor, end + 1)
    if cursor <= total:
        missing.append([cursor, total])
    return missing
