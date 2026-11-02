"""Token-budgeted code context assembly.

Turns symbol-index retrieval results into one LLM-ready text block under a
fixed token budget. The packer is deterministic and follows the thesis strategy
of packing by priority:

1. primary symbol signatures (the key functions/classes for the query),
2. dependency closure signatures (call chains and related interfaces),
3. source excerpts of the top-ranked symbols,
4. module summaries (docstrings) of every file involved.

Anything that no longer fits is dropped in reverse priority order and reported
via ``ContextPack.truncated``. Token accounting reuses the CJK-aware estimator
from ``yecoding.context`` so the same budget math governs conversation history
and retrieved code context.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from yecoding.context import estimate_text_tokens
from yecoding.rag.code_index import CodeIndex
from yecoding.rag.parser import KIND_CLASS, KIND_FUNCTION, KIND_METHOD, Symbol

SOURCE_KINDS = frozenset({KIND_CLASS, KIND_FUNCTION, KIND_METHOD})


@dataclass(slots=True, frozen=True)
class ContextPackConfig:
    max_symbols: int = 8
    max_dependencies_per_symbol: int = 12
    source_top_k: int = 3
    max_source_lines_per_symbol: int = 40
    header_reserve_tokens: int = 96
    include_dependencies: bool = True


@dataclass(slots=True)
class ContextPack:
    text: str
    token_estimate: int
    budget_tokens: int
    symbols_included: list[str] = field(default_factory=list)
    dependency_count: int = 0
    source_symbols: list[str] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    truncated: bool = False
    #: Source provenance as (path, start_line, end_line) triples, 1-based
    #: inclusive. Signature/call-chain entries contribute single-line spans.
    spans: list[tuple[str, int, int]] = field(default_factory=list)


class ContextBuilder:
    """Assemble ranked code symbols into a budgeted, prioritized context block."""

    def __init__(self, index: CodeIndex, config: ContextPackConfig | None = None):
        self.index = index
        self.config = config or ContextPackConfig()

    def build(self, query: str, budget_tokens: int) -> ContextPack:
        budget = max(self.config.header_reserve_tokens + 32, int(budget_tokens))
        pack = ContextPack(text="", token_estimate=0, budget_tokens=budget)
        ranked = self.index.ranked_symbols(query, limit=self.config.max_symbols)
        if not ranked:
            return pack

        remaining = budget - self.config.header_reserve_tokens
        parts: list[str] = []

        remaining = self._pack_signatures(pack, parts, ranked, remaining)
        if self.config.include_dependencies:
            remaining = self._pack_call_chains(pack, parts, ranked, remaining)
        remaining = self._pack_sources(pack, parts, ranked, remaining)
        self._pack_file_summaries(pack, parts, remaining)

        body = "\n".join(parts)
        if not body:
            return pack
        pack.token_estimate = estimate_text_tokens(body) + self.config.header_reserve_tokens
        pack.text = (
            f'<code-context query="{_sanitize(query)}" budget_tokens={pack.budget_tokens} '
            f'tokens={pack.token_estimate} trust="indexed-workspace-data">\n'
            f"{body}\n</code-context>"
        )
        return pack

    # ------------------------------------------------------------------
    # Packing stages, in priority order
    # ------------------------------------------------------------------

    def _start_section(self, pack: ContextPack, title: str, remaining: int) -> int | None:
        """Charge the section header upfront; None means it does not fit."""
        cost = estimate_text_tokens(title) + 1
        if cost > remaining:
            pack.truncated = True
            return None
        return remaining - cost

    def _pack_signatures(
        self, pack: ContextPack, parts: list[str], ranked: list[Symbol], remaining: int
    ) -> int:
        header_remaining = self._start_section(pack, "## Matching symbols", remaining)
        if header_remaining is None:
            return remaining
        lines: list[str] = ["## Matching symbols"]
        remaining = header_remaining
        for symbol in ranked:
            entry = f"- {symbol.path}:{symbol.line} [{symbol.kind}] {symbol.qualified_name}"
            if symbol.signature:
                entry += f" — {symbol.signature}"
            cost = estimate_text_tokens(entry) + 1
            if cost > remaining:
                pack.truncated = True
                continue
            remaining -= cost
            pack.symbols_included.append(symbol.qualified_name)
            pack.files.append(symbol.path)
            pack.spans.append((symbol.path, symbol.line, symbol.line))
            lines.append(entry)
        if len(lines) > 1:
            parts.append("\n".join(lines))
        return remaining

    def _pack_call_chains(
        self, pack: ContextPack, parts: list[str], ranked: list[Symbol], remaining: int
    ) -> int:
        header_remaining = self._start_section(pack, "## Call chains", remaining)
        if header_remaining is None:
            return remaining
        seen: set[tuple[str, int]] = {(s.path, s.line) for s in ranked}
        lines: list[str] = ["## Call chains"]
        remaining = header_remaining
        for symbol in ranked:
            relations: list[tuple[str, str, Symbol]] = [
                ("calls", symbol.name, dep)
                for dep in self.index.callees(
                    symbol.qualified_name,
                    path=symbol.path,
                    limit=self.config.max_dependencies_per_symbol,
                )
            ]
            relations += [
                ("called by", symbol.name, dep)
                for dep in self.index.callers(
                    symbol.qualified_name,
                    path=symbol.path,
                    limit=self.config.max_dependencies_per_symbol,
                )
            ]
            for role, primary_name, dep in relations:
                if (dep.path, dep.line) in seen:
                    continue
                seen.add((dep.path, dep.line))
                entry = f"- {primary_name} {role} {dep.qualified_name} ({dep.path}:{dep.line})"
                if dep.signature:
                    entry += f" — {dep.signature}"
                cost = estimate_text_tokens(entry) + 1
                if cost > remaining:
                    pack.truncated = True
                    continue
                remaining -= cost
                pack.dependency_count += 1
                pack.files.append(dep.path)
                pack.spans.append((dep.path, dep.line, dep.line))
                lines.append(entry)
        if len(lines) > 1:
            parts.append("\n".join(lines))
        return remaining

    def _pack_sources(
        self, pack: ContextPack, parts: list[str], ranked: list[Symbol], remaining: int
    ) -> int:
        header_remaining = self._start_section(pack, "## Source excerpts", remaining)
        if header_remaining is None:
            return remaining
        blocks: list[str] = ["## Source excerpts"]
        remaining = header_remaining
        for symbol in ranked[: self.config.source_top_k]:
            if symbol.kind not in SOURCE_KINDS:
                continue
            end = min(symbol.end_line, symbol.line + self.config.max_source_lines_per_symbol - 1)
            source = self.index.read_lines(symbol.path, symbol.line, end)
            if not source:
                continue
            body = "\n".join(source)
            omitted = symbol.end_line - end
            if omitted > 0:
                body += f"\n... [{omitted} more lines omitted]"
            block = f"### {symbol.qualified_name} ({symbol.path}:{symbol.line}-{end})\n{body}"
            cost = estimate_text_tokens(block) + 2
            if cost > remaining:
                pack.truncated = True
                break
            remaining -= cost
            pack.source_symbols.append(symbol.qualified_name)
            pack.spans.append((symbol.path, symbol.line, end))
            blocks.append(block)
        if len(blocks) > 1:
            parts.append("\n".join(blocks))
        return remaining

    def _pack_file_summaries(self, pack: ContextPack, parts: list[str], remaining: int) -> None:
        if not pack.files:
            return
        header_remaining = self._start_section(pack, "## File summaries", remaining)
        if header_remaining is None:
            return
        lines: list[str] = ["## File summaries"]
        remaining = header_remaining
        for path in dict.fromkeys(pack.files):
            file_sym = self.index.file_symbol(path)
            docstring = file_sym.docstring if file_sym else None
            summary = docstring.splitlines()[0] if docstring else "(no module docstring)"
            entry = f"- {path} — {summary}"
            cost = estimate_text_tokens(entry) + 1
            if cost > remaining:
                pack.truncated = True
                continue
            remaining -= cost
            lines.append(entry)
        if len(lines) > 1:
            parts.append("\n".join(lines))


def _sanitize(query: str) -> str:
    return " ".join(query.split()).replace('"', "'")
