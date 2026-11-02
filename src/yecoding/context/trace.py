"""Opt-in structured observation. Values sent to the provider are never rewritten."""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from uuid import uuid4

_LOCK = threading.Lock()


def structured(value):
    if is_dataclass(value) and not isinstance(value, type):
        return structured(asdict(value))
    if isinstance(value, dict):
        return {str(k): structured(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [structured(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def fingerprint(value) -> str:
    return hashlib.sha256(
        json.dumps(structured(value), ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


class TraceRecorder:
    def __init__(self, path: str | Path, *, secrets=()):
        self.path = Path(path).expanduser()
        self.secrets = tuple(str(x) for x in secrets if x)
        self.session = uuid4().hex

    def emit(self, kind: str, **data):
        row = structured({"type": kind, "session": self.session, "time": time.time(), **data})
        row = self._redact(row)
        body = json.dumps(row, ensure_ascii=False) + "\n"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with _LOCK:
            descriptor = os.open(
                self.path,
                os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
                stream.write(body)

    def _redact(self, value):
        if isinstance(value, dict):
            return {
                k: "[REDACTED]"
                if re.search(
                    r"api.?key|authorization|password|secret|cookie|access.?token", k, re.I
                )
                else self._redact(v)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [self._redact(v) for v in value]
        if isinstance(value, str):
            for secret in self.secrets:
                value = value.replace(secret, "[REDACTED]")
            value = re.sub(r"(?i)(Bearer\s+)\S+", r"\1[REDACTED]", value)
            value = re.sub(
                r"(?i)((?:api[_-]?key|password|access[_-]?token)\s*[=:]\s*[\"']?)"
                r"[^\s,;\"']+",
                r"\1[REDACTED]",
                value,
            )
            value = re.sub(
                r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----.*?"
                r"-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
                "[REDACTED PRIVATE KEY]",
                value,
                flags=re.S,
            )
            value = re.sub(r"(https?://)[^\s/@:]+:[^\s/@]+@", r"\1[REDACTED]@", value)
        return value


class ObservedClient:
    def __init__(self, client, recorder: TraceRecorder):
        self.client = client
        self.recorder = recorder
        self._yecoding_trace_recorder = recorder

    def __getattr__(self, name):
        return getattr(self.client, name)

    async def chat(self, messages, tools, *, system_prompt):
        call = uuid4().hex
        request = {"messages": messages, "tools": tools, "system_prompt": system_prompt}
        if type(self.client).__module__ == "yecoding.llm.openai_compatible":
            request["provider_payload"] = self.client._build_payload(
                messages, tools, system_prompt=system_prompt
            )
        self.recorder.emit("request", call=call, request=request, sha256=fingerprint(request))
        started = time.monotonic()
        try:
            async for event in self.client.chat(messages, tools, system_prompt=system_prompt):
                self.recorder.emit("model.event", call=call, event=event)
                yield event
        except BaseException as exc:
            self.recorder.emit("model.exception", call=call, error=str(exc))
            raise
        finally:
            self.recorder.emit("request.ended", call=call, seconds=time.monotonic() - started)


def observe_client(client, config):
    if isinstance(client, ObservedClient) or not config.context.trace_path:
        return client
    return ObservedClient(
        client, TraceRecorder(config.context.trace_path, secrets=(config.llm.api_key,))
    )
