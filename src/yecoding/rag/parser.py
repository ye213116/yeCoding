"""Structural parsing of Python source files.

Extracts files, classes, functions, variables, imports, and best-effort call
relations from Python source using the standard ``ast`` module. The output feeds
the symbol index (``yecoding.rag.code_index``) that backs dependency-aware code
retrieval.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass

KIND_FILE = "file"
KIND_CLASS = "class"
KIND_FUNCTION = "function"
KIND_METHOD = "method"
KIND_VARIABLE = "variable"

RELATION_IMPORT = "import"
RELATION_CALL = "call"
RELATION_INHERITS = "inherits"

MAX_SIGNATURE_CHARS = 200
MAX_DOCSTRING_CHARS = 500


@dataclass(slots=True)
class Symbol:
    path: str
    name: str
    qualified_name: str
    kind: str
    line: int
    end_line: int
    signature: str | None = None
    docstring: str | None = None
    parent: str | None = None


@dataclass(slots=True)
class Relation:
    """A best-effort reference between code entities.

    ``dst`` is the dotted name exactly as written (``os.path.join``,
    ``self.helper``); resolving it to concrete symbols is the index's job.
    """

    dst: str
    kind: str
    line: int
    src: str | None = None
    src_path: str = ""


@dataclass(slots=True)
class ParsedModule:
    path: str
    module: str
    symbols: list[Symbol]
    relations: list[Relation]


def module_name(rel_path: str) -> str:
    """Derive the module name from a root-relative file path."""
    normalized = rel_path.replace("\\", "/")
    parent, _, stem = normalized.rpartition("/")
    if stem == "__init__.py":
        return parent.rpartition("/")[2] or "__init__"
    if stem.endswith(".py"):
        stem = stem[:-3]
    return stem


def parse_python_module(rel_path: str, source: str) -> ParsedModule:
    """Parse one Python file into symbols and relations.

    Raises ``SyntaxError`` for unparseable source; callers decide the fallback.
    """
    if source.startswith("\ufeff"):
        source = source[1:]
    tree = ast.parse(source)
    collector = _SymbolCollector(module_name(rel_path), rel_path)
    collector.visit(tree)
    return ParsedModule(
        path=rel_path,
        module=collector.module,
        symbols=collector.symbols,
        relations=collector.relations,
    )


class _SymbolCollector(ast.NodeVisitor):
    def __init__(self, module: str, path: str):
        self.module = module
        self.path = path
        self.symbols: list[Symbol] = []
        self.relations: list[Relation] = []
        # ("class" | "function", qualified name) of enclosing definitions.
        self.stack: list[tuple[str, str]] = []

    def visit_Module(self, node: ast.Module) -> None:
        end_line = node.body[-1].end_lineno if node.body else 1
        self.symbols.append(
            Symbol(
                path=self.path,
                name=self.module,
                qualified_name=self.module,
                kind=KIND_FILE,
                line=1,
                end_line=end_line or 1,
                docstring=_clip(ast.get_docstring(node), MAX_DOCSTRING_CHARS),
            )
        )
        self.generic_visit(node)

    # -- definitions ------------------------------------------------------

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified = self._qualified(node.name)
        bases = []
        for base in node.bases:
            dotted = _dotted_name(base)
            if dotted:
                bases.append(dotted)
                self.relations.append(
                    Relation(
                        dst=dotted,
                        kind=RELATION_INHERITS,
                        line=node.lineno,
                        src=qualified,
                        src_path=self.path,
                    )
                )
        signature = f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
        self.symbols.append(
            Symbol(
                path=self.path,
                name=node.name,
                qualified_name=qualified,
                kind=KIND_CLASS,
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                signature=_clip(signature, MAX_SIGNATURE_CHARS),
                docstring=_clip(ast.get_docstring(node), MAX_DOCSTRING_CHARS),
                parent=self._enclosing(),
            )
        )
        self.stack.append(("class", qualified))
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node, is_async=True)

    def _visit_function(self, node, *, is_async: bool) -> None:
        qualified = self._qualified(node.name)
        kind = KIND_METHOD if self._in_class_body() else KIND_FUNCTION
        keyword = "async def" if is_async else "def"
        returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        signature = f"{keyword} {node.name}({ast.unparse(node.args)}){returns}"
        self.symbols.append(
            Symbol(
                path=self.path,
                name=node.name,
                qualified_name=qualified,
                kind=kind,
                line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                signature=_clip(signature, MAX_SIGNATURE_CHARS),
                docstring=_clip(ast.get_docstring(node), MAX_DOCSTRING_CHARS),
                parent=self._enclosing(),
            )
        )
        self.stack.append(("function", qualified))
        self.generic_visit(node)
        self.stack.pop()

    # -- variables (module and class level only) ---------------------------

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._captures_variables():
            for target in node.targets:
                if isinstance(target, ast.Name):
                    self._add_variable(target.id, node.lineno, node.end_lineno, value=node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self._captures_variables() and isinstance(node.target, ast.Name):
            self._add_variable(
                node.target.id,
                node.lineno,
                node.end_lineno,
                annotation=node.annotation,
                value=node.value,
            )
        self.generic_visit(node)

    def _add_variable(self, name: str, lineno: int, end_lineno: int, **parts) -> None:
        try:
            rendered = name
            if parts.get("annotation") is not None:
                rendered += f": {ast.unparse(parts['annotation'])}"
            if parts.get("value") is not None:
                rendered += f" = {ast.unparse(parts['value'])}"
        except Exception:
            rendered = name
        self.symbols.append(
            Symbol(
                path=self.path,
                name=name,
                qualified_name=self._qualified(name),
                kind=KIND_VARIABLE,
                line=lineno,
                end_line=end_lineno or lineno,
                signature=_clip(rendered, MAX_SIGNATURE_CHARS),
                parent=self._enclosing(),
            )
        )

    # -- imports and calls --------------------------------------------------

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.relations.append(
                Relation(
                    dst=alias.name,
                    kind=RELATION_IMPORT,
                    line=node.lineno,
                    src=self._current_scope(),
                    src_path=self.path,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        prefix = "." * node.level + (node.module or "")
        for alias in node.names:
            dotted = f"{prefix}.{alias.name}" if prefix else alias.name
            self.relations.append(
                Relation(
                    dst=dotted,
                    kind=RELATION_IMPORT,
                    line=node.lineno,
                    src=self._current_scope(),
                    src_path=self.path,
                )
            )

    def visit_Call(self, node: ast.Call) -> None:
        dotted = _dotted_name(node.func)
        if dotted:
            self.relations.append(
                Relation(
                    dst=dotted,
                    kind=RELATION_CALL,
                    line=node.lineno,
                    src=self._current_scope(),
                    src_path=self.path,
                )
            )
        self.generic_visit(node)

    # -- scope helpers --------------------------------------------------------

    def _qualified(self, name: str) -> str:
        # Stack entries already carry fully qualified names.
        return f"{self.stack[-1][1]}.{name}" if self.stack else f"{self.module}.{name}"

    def _enclosing(self) -> str | None:
        return self.stack[-1][1] if self.stack else None

    def _current_scope(self) -> str | None:
        return self.stack[-1][1] if self.stack else None

    def _in_class_body(self) -> bool:
        return bool(self.stack) and self.stack[-1][0] == "class"

    def _captures_variables(self) -> bool:
        # Only module-level and class-level assignments become symbols; keeping
        # function-local variables out avoids drowning the index in noise.
        return not self.stack or self._in_class_body()


def _dotted_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        if base:
            return f"{base}.{node.attr}"
    return None


def _clip(text: str | None, limit: int) -> str | None:
    if text is None:
        return None
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: limit - 3] + "..."
    return text or None
