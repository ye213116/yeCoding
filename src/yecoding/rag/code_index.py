from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from yecoding.rag.parser import (
    KIND_FILE,
    KIND_METHOD,
    ParsedModule,
    Symbol,
    parse_python_module,
)

TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".java",
    ".kt",
    ".go",
    ".rs",
    ".md",
    ".toml",
    ".yaml",
    ".yml",
    ".json",
    ".xml",
    ".html",
    ".css",
    ".scss",
    ".sql",
    ".sh",
}

SKIP_DIRS = {".git", ".venv", "node_modules", "dist", "build", "target", "__pycache__"}

SELF_PREFIX = "self."
MRO_DEPTH_LIMIT = 10


@dataclass(slots=True)
class CodeSearchResult:
    path: str
    line: int
    snippet: str


@dataclass(slots=True)
class CodeDependencyResult:
    """A ranked symbol hit together with its dependency snippet closure."""

    primary: CodeSearchResult
    symbol: Symbol
    dependencies: list[CodeSearchResult]


class CodeIndex:
    """SQLite-backed code index: AST symbol table plus line-level text fallback.

    ``rebuild`` parses every Python file into symbols (files, classes,
    functions, methods, variables) and best-effort relations (imports, calls,
    inheritance) stored in ``symbols``/``edges`` tables, and keeps per-line
    chunks of every indexed file in ``code_chunks`` for plain text search.
    ``search`` ranks symbol matches first, then fills the remaining slots with
    line matches, deduplicating overlaps. Call relations whose target cannot be
    resolved unambiguously keep ``dst_symbol_id`` NULL; the parser deliberately
    records them as "possible" edges.
    """

    def __init__(self, root: str | Path, db_path: str | Path | None = None):
        self.root = Path(root).resolve()
        self.db_path = (
            Path(db_path).expanduser()
            if db_path
            else self.root / ".yecoding" / "code_index.sqlite3"
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def rebuild(self, path: str | Path | None = None) -> int:
        base = self._resolve(path or self.root)
        files = [base] if base.is_file() else list(self._iter_files(base))
        with self._connect() as conn:
            for table in ("code_chunks", "symbols", "edges"):
                conn.execute(f"delete from {table} where root = ?", (str(self.root),))
            count = 0
            for file_path in files:
                rel = str(file_path.relative_to(self.root))
                try:
                    source = file_path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                count += self._index_lines(conn, rel, source)
                if file_path.suffix.lower() == ".py":
                    count += self._index_symbols(conn, rel, source)
            self._resolve_edges(conn)
            return count

    def _index_lines(self, conn: sqlite3.Connection, rel: str, source: str) -> int:
        count = 0
        for line_number, line in enumerate(source.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            conn.execute(
                "insert into code_chunks(root, path, line, content) values (?, ?, ?, ?)",
                (str(self.root), rel, line_number, stripped),
            )
            count += 1
        return count

    def _index_symbols(self, conn: sqlite3.Connection, rel: str, source: str) -> int:
        try:
            module: ParsedModule = parse_python_module(rel, source)
        except (SyntaxError, ValueError, RecursionError):
            return 0
        for symbol in module.symbols:
            conn.execute(
                """
                insert into symbols(
                    root, path, name, qualified_name, kind,
                    line, end_line, signature, docstring, parent
                )
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(self.root),
                    symbol.path,
                    symbol.name,
                    symbol.qualified_name,
                    symbol.kind,
                    symbol.line,
                    symbol.end_line,
                    symbol.signature,
                    symbol.docstring,
                    symbol.parent,
                ),
            )
        for relation in module.relations:
            conn.execute(
                """
                insert into edges(root, src, src_path, dst, dst_symbol_id, kind, line)
                values (?, ?, ?, ?, null, ?, ?)
                """,
                (
                    str(self.root),
                    relation.src,
                    relation.src_path,
                    relation.dst,
                    relation.kind,
                    relation.line,
                ),
            )
        return len(module.symbols)

    def _resolve_edges(self, conn: sqlite3.Connection) -> None:
        root = str(self.root)
        by_name: dict[str, list[tuple[int, str]]] = {}
        for symbol_id, name, path in conn.execute(
            "select id, name, path from symbols where root = ? and kind != ?",
            (root, KIND_FILE),
        ):
            by_name.setdefault(name, []).append((int(symbol_id), str(path)))

        simple = conn.execute(
            """
            select id, src_path, dst from edges
            where root = ? and dst_symbol_id is null
              and kind in ('call', 'inherits') and instr(dst, '.') = 0
            """,
            (root,),
        ).fetchall()
        for edge_id, src_path, dst in simple:
            resolved = self._pick_candidate(by_name.get(dst) or [], str(src_path))
            if resolved is not None:
                conn.execute(
                    "update edges set dst_symbol_id = ? where id = ?", (resolved, int(edge_id))
                )

        members = conn.execute(
            """
            select id, src, src_path, dst from edges
            where root = ? and dst_symbol_id is null
              and kind = 'call' and dst like 'self.%'
            """,
            (root,),
        ).fetchall()
        for edge_id, src, src_path, dst in members:
            resolved = self._resolve_self_member(conn, src, str(src_path), dst[len(SELF_PREFIX) :])
            if resolved is not None:
                conn.execute(
                    "update edges set dst_symbol_id = ? where id = ?", (resolved, int(edge_id))
                )

    @staticmethod
    def _pick_candidate(candidates: list[tuple[int, str]], src_path: str) -> int | None:
        same_file = [symbol_id for symbol_id, path in candidates if path == src_path]
        if len(same_file) == 1:
            return same_file[0]
        if not same_file and len(candidates) == 1:
            return candidates[0][0]
        return None

    def _resolve_self_member(
        self, conn: sqlite3.Connection, src: str | None, src_path: str, attr: str
    ) -> int | None:
        """Resolve ``self.attr`` by walking the enclosing class and its bases."""
        if not src:
            return None
        root = str(self.root)
        row = conn.execute(
            "select parent from symbols where root = ? and path = ? and qualified_name = ?",
            (root, src_path, src),
        ).fetchone()
        parent = str(row[0]) if row and row[0] else None
        visited: set[str] = set()
        while parent and parent not in visited and len(visited) < MRO_DEPTH_LIMIT:
            visited.add(parent)
            row = conn.execute(
                """
                select id from symbols
                where root = ? and path = ? and qualified_name = ? and kind = ?
                """,
                (root, src_path, f"{parent}.{attr}", KIND_METHOD),
            ).fetchone()
            if row:
                return int(row[0])
            base_row = conn.execute(
                """
                select s.qualified_name from edges e
                join symbols s on s.root = e.root and s.id = e.dst_symbol_id
                where e.root = ? and e.kind = 'inherits' and e.src = ? and e.src_path = ?
                limit 1
                """,
                (root, parent, src_path),
            ).fetchone()
            parent = str(base_row[0]) if base_row else None
        return None

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 20) -> list[CodeSearchResult]:
        terms = [term.lower() for term in query.split() if term.strip()]
        if not terms:
            return []
        results: list[CodeSearchResult] = []
        seen: set[tuple[str, int]] = set()
        for result in self._search_symbols(terms, limit):
            results.append(result)
            seen.add((result.path, result.line))
        if len(results) < limit:
            for result in self._search_chunks(terms, limit):
                if (result.path, result.line) in seen:
                    continue
                results.append(result)
                seen.add((result.path, result.line))
                if len(results) >= limit:
                    break
        return results

    def search_with_dependencies(
        self, query: str, limit: int = 10, *, max_dependencies: int = 12
    ) -> list[CodeDependencyResult]:
        """Ranked symbol matches, each expanded with callee and caller snippets."""
        terms = [term.lower() for term in query.split() if term.strip()]
        if not terms:
            return []
        results: list[CodeDependencyResult] = []
        for _score, symbol in self._ranked_symbols(terms, limit):
            primary = CodeSearchResult(
                path=symbol.path,
                line=symbol.line,
                snippet=symbol.signature or f"{symbol.kind} {symbol.name}",
            )
            dependencies: dict[tuple[str, int], CodeSearchResult] = {}
            related = [
                *self.callees(symbol.qualified_name, path=symbol.path),
                *self.callers(symbol.qualified_name, path=symbol.path),
            ]
            for dep in related:
                dependencies.setdefault(
                    (dep.path, dep.line),
                    CodeSearchResult(
                        path=dep.path,
                        line=dep.line,
                        snippet=dep.signature or f"{dep.kind} {dep.name}",
                    ),
                )
            results.append(
                CodeDependencyResult(
                    primary=primary,
                    symbol=symbol,
                    dependencies=list(dependencies.values())[:max_dependencies],
                )
            )
        return results

    def callees(
        self, qualified_name: str, *, path: str | None = None, limit: int = 50
    ) -> list[Symbol]:
        """Symbols invoked by the given function/method (resolved edges only)."""
        conditions = "e.root = ? and e.kind = 'call' and e.src = ?"
        params: list[object] = [str(self.root), qualified_name]
        if path:
            conditions += " and e.src_path = ?"
            params.append(path)
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                select distinct s.path, s.name, s.qualified_name, s.kind,
                       s.line, s.end_line, s.signature, s.docstring, s.parent
                from edges e
                join symbols s on s.root = e.root and s.id = e.dst_symbol_id
                where {conditions}
                order by s.path, s.line
                limit ?
                """,
                params,
            ).fetchall()
        return [_row_to_symbol(row) for row in rows]

    def callers(
        self, qualified_name: str, *, path: str | None = None, limit: int = 50
    ) -> list[Symbol]:
        """Symbols whose body invokes the given function/method."""
        with self._connect() as conn:
            if path:
                target_ids = [
                    int(row[0])
                    for row in conn.execute(
                        "select id from symbols where root = ? and path = ? and qualified_name = ?",
                        (str(self.root), path, qualified_name),
                    )
                ]
            else:
                target_ids = [
                    int(row[0])
                    for row in conn.execute(
                        "select id from symbols where root = ? and qualified_name = ?",
                        (str(self.root), qualified_name),
                    )
                ]
            if not target_ids:
                return []
            placeholders = ",".join("?" * len(target_ids))
            rows = conn.execute(
                f"""
                select distinct s.path, s.name, s.qualified_name, s.kind,
                       s.line, s.end_line, s.signature, s.docstring, s.parent
                from edges e
                join symbols s on s.root = e.root
                    and s.path = e.src_path and s.qualified_name = e.src
                where e.root = ? and e.kind = 'call' and e.dst_symbol_id in ({placeholders})
                order by s.path, s.line
                limit ?
                """,
                (str(self.root), *target_ids, limit),
            ).fetchall()
        return [_row_to_symbol(row) for row in rows]

    def list_symbols(self, *, kind: str | None = None, limit: int = 500) -> list[Symbol]:
        conditions = "root = ?"
        params: list[object] = [str(self.root)]
        if kind:
            conditions += " and kind = ?"
            params.append(kind)
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                select path, name, qualified_name, kind,
                       line, end_line, signature, docstring, parent
                from symbols
                where {conditions}
                order by path, line
                limit ?
                """,
                params,
            ).fetchall()
        return [_row_to_symbol(row) for row in rows]

    def ranked_symbols(self, query: str, limit: int = 10) -> list[Symbol]:
        """Symbols ranked by relevance to the query, matching ANY term.

        Multi-word natural-language queries rarely have every term inside one
        symbol, so ranking sums per-term scores and keeps any symbol hit by at
        least one term.
        """
        terms = [term.lower() for term in query.split() if term.strip()]
        if not terms:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                select path, name, qualified_name, kind,
                       line, end_line, signature, docstring, parent
                from symbols
                where root = ?
                """,
                (str(self.root),),
            ).fetchall()
        scored: list[tuple[int, Symbol]] = []
        for row in rows:
            symbol = _row_to_symbol(row)
            score = _score_symbol_any(terms, symbol)
            if score > 0:
                scored.append((score, symbol))
        scored.sort(key=lambda item: (-item[0], item[1].path, item[1].line))
        return [symbol for _score, symbol in scored[:limit]]

    def file_symbol(self, path: str) -> Symbol | None:
        """The ``file``-kind symbol (with module docstring) for a relative path."""
        with self._connect() as conn:
            row = conn.execute(
                """
                select path, name, qualified_name, kind,
                       line, end_line, signature, docstring, parent
                from symbols
                where root = ? and path = ? and kind = ?
                limit 1
                """,
                (str(self.root), path, KIND_FILE),
            ).fetchone()
        return _row_to_symbol(row) if row else None

    def read_lines(self, rel_path: str, start: int, end: int) -> list[str]:
        """Raw source lines for a root-relative path, 1-based inclusive bounds."""
        try:
            file_path = self._resolve(rel_path)
        except ValueError:
            return []
        if not file_path.is_file():
            return []
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            return []
        start = max(int(start), 1)
        end = max(int(end), start)
        return lines[start - 1 : end]

    def _search_symbols(self, terms: list[str], limit: int) -> list[CodeSearchResult]:
        return [
            CodeSearchResult(
                path=symbol.path,
                line=symbol.line,
                snippet=symbol.signature or f"{symbol.kind} {symbol.name}",
            )
            for _score, symbol in self._ranked_symbols(terms, limit)
        ]

    def _ranked_symbols(self, terms: list[str], limit: int) -> list[tuple[int, Symbol]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select path, name, qualified_name, kind,
                       line, end_line, signature, docstring, parent
                from symbols
                where root = ?
                """,
                (str(self.root),),
            ).fetchall()
        scored: list[tuple[int, Symbol]] = []
        for row in rows:
            symbol = _row_to_symbol(row)
            score = _score_symbol(terms, symbol)
            if score > 0:
                scored.append((score, symbol))
        scored.sort(key=lambda item: (-item[0], item[1].path, item[1].line))
        return scored[:limit]

    def _search_chunks(self, terms: list[str], limit: int) -> list[CodeSearchResult]:
        rows: list[tuple[str, int, str]]
        with self._connect() as conn:
            like = f"%{terms[0]}%"
            rows = conn.execute(
                """
                select path, line, content
                from code_chunks
                where root = ? and lower(content) like ?
                order by path, line
                limit 500
                """,
                (str(self.root), like),
            ).fetchall()
        results: list[CodeSearchResult] = []
        for path, line, content in rows:
            lowered = content.lower()
            if all(term in lowered for term in terms):
                results.append(CodeSearchResult(path, int(line), content))
            if len(results) >= limit:
                break
        return results

    # ------------------------------------------------------------------
    # Filesystem and schema helpers
    # ------------------------------------------------------------------

    def _iter_files(self, base: Path):
        for path in base.rglob("*"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
                yield path

    def _resolve(self, value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = self.root / path
        resolved = path.resolve()
        resolved.relative_to(self.root)
        return resolved

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists code_chunks (
                    id integer primary key autoincrement,
                    root text not null,
                    path text not null,
                    line integer not null,
                    content text not null
                )
                """
            )
            conn.execute(
                "create index if not exists idx_code_chunks_root_path on code_chunks(root, path)"
            )
            conn.execute(
                "create index if not exists idx_code_chunks_root_content "
                "on code_chunks(root, content)"
            )
            conn.execute(
                """
                create table if not exists symbols (
                    id integer primary key autoincrement,
                    root text not null,
                    path text not null,
                    name text not null,
                    qualified_name text not null,
                    kind text not null,
                    line integer not null,
                    end_line integer not null,
                    signature text,
                    docstring text,
                    parent text
                )
                """
            )
            conn.execute("create index if not exists idx_symbols_root on symbols(root)")
            conn.execute("create index if not exists idx_symbols_root_name on symbols(root, name)")
            conn.execute(
                "create index if not exists idx_symbols_root_qualified "
                "on symbols(root, qualified_name)"
            )
            conn.execute(
                """
                create table if not exists edges (
                    id integer primary key autoincrement,
                    root text not null,
                    src text,
                    src_path text not null,
                    dst text not null,
                    dst_symbol_id integer,
                    kind text not null,
                    line integer not null
                )
                """
            )
            conn.execute("create index if not exists idx_edges_root on edges(root)")
            conn.execute("create index if not exists idx_edges_root_dst on edges(root, dst)")
            conn.execute("create index if not exists idx_edges_root_src on edges(root, src)")
            conn.execute(
                "create index if not exists idx_edges_root_dst_symbol on edges(root, dst_symbol_id)"
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)


def _score_symbol(terms: list[str], symbol: Symbol) -> int:
    """All terms must match somewhere; exact name hits rank highest."""
    total = 0
    for term in terms:
        term_score = _score_term(term, symbol)
        if term_score == 0:
            return 0
        total += term_score
    return total


def _score_symbol_any(terms: list[str], symbol: Symbol) -> int:
    """Sum scores of matching terms; symbols hit by no term score zero."""
    return sum(_score_term(term, symbol) for term in terms)


def _score_term(term: str, symbol: Symbol) -> int:
    name_l = symbol.name.lower()
    qual_l = symbol.qualified_name.lower()
    sig_l = (symbol.signature or "").lower()
    doc_l = (symbol.docstring or "").lower()
    if name_l == term:
        return 100
    if name_l.startswith(term):
        return 60
    if term in name_l:
        return 40
    if term in qual_l:
        return 20
    if term in sig_l:
        return 8
    if term in doc_l:
        return 4
    return 0


def _row_to_symbol(row: tuple) -> Symbol:
    return Symbol(
        path=str(row[0]),
        name=str(row[1]),
        qualified_name=str(row[2]),
        kind=str(row[3]),
        line=int(row[4]),
        end_line=int(row[5]),
        signature=row[6],
        docstring=row[7],
        parent=row[8],
    )
