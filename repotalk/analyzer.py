"""AST-based static analysis — extract imports, functions, classes, calls."""

from __future__ import annotations

import ast
import hashlib
import logging
from pathlib import Path

from repotalk.models import (
    ArgumentInfo,
    ClassInfo,
    FileAnalysis,
    FunctionInfo,
    ImportInfo,
    VariableInfo,
)

logger = logging.getLogger(__name__)


def analyze_file(file_path: Path, root: Path) -> FileAnalysis:
    """Perform full AST analysis on a single Python file."""
    source = file_path.read_text(errors="replace")
    file_hash = hashlib.sha256(source.encode()).hexdigest()
    relative = str(file_path.relative_to(root))
    module_name = _path_to_module(file_path, root)

    analysis = FileAnalysis(
        file_path=str(file_path),
        relative_path=relative,
        module_name=module_name,
        file_hash=file_hash,
        line_count=source.count("\n") + 1,
    )

    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError as e:
        analysis.errors.append(f"SyntaxError: {e}")
        return analysis

    analysis.module_docstring = ast.get_docstring(tree)

    # Extract __all__ if present
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    analysis.all_exports = _extract_all(node.value)

    visitor = _FileVisitor(module_name, root)
    visitor.visit(tree)

    analysis.imports = visitor.imports
    analysis.functions = visitor.functions
    analysis.classes = visitor.classes
    analysis.variables = visitor.variables

    return analysis


class _FileVisitor(ast.NodeVisitor):
    """AST visitor that extracts all relevant code structures."""

    def __init__(self, module_name: str, root: Path):
        self.module_name = module_name
        self.root = root
        self.imports: list[ImportInfo] = []
        self.functions: list[FunctionInfo] = []
        self.classes: list[ClassInfo] = []
        self.variables: list[VariableInfo] = []
        self._scope_stack: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append(
                ImportInfo(
                    module=alias.name,
                    names=[alias.name.split(".")[-1]],
                    alias=alias.asname,
                    is_relative=False,
                    is_internal=self._is_internal(alias.name),
                    line=node.lineno,
                )
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        names = [a.name for a in node.names] if node.names else []
        self.imports.append(
            ImportInfo(
                module=module,
                names=names,
                is_relative=bool(node.level and node.level > 0),
                is_internal=self._is_internal(module) or (node.level is not None and node.level > 0),
                line=node.lineno,
            )
        )

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._process_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._process_function(node, is_async=True)

    def _process_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool
    ) -> None:
        # Only collect top-level functions (not nested inside other functions)
        if self._scope_stack and self._scope_stack[-1] == "function":
            return

        qualified = f"{self.module_name}.{node.name}" if self.module_name else node.name
        is_method = bool(self._scope_stack and self._scope_stack[-1] == "class")

        func = FunctionInfo(
            name=node.name,
            qualified_name=qualified,
            args=_extract_args(node.args),
            return_type=_unparse_annotation(node.returns),
            decorators=[_unparse_decorator(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node),
            is_method=is_method,
            is_async=is_async,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            calls=_extract_calls(node),
            complexity=_estimate_complexity(node),
        )

        if is_method:
            # Methods get added to the current class in visit_ClassDef
            self._current_methods.append(func)
        else:
            self.functions.append(func)

        self._scope_stack.append("function")
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualified = f"{self.module_name}.{node.name}" if self.module_name else node.name
        bases = [_unparse_node(b) for b in node.bases]

        self._current_methods: list[FunctionInfo] = []
        class_vars = _extract_class_variables(node)

        self._scope_stack.append("class")
        self.generic_visit(node)
        self._scope_stack.pop()

        cls = ClassInfo(
            name=node.name,
            qualified_name=qualified,
            bases=bases,
            decorators=[_unparse_decorator(d) for d in node.decorator_list],
            docstring=ast.get_docstring(node),
            methods=self._current_methods,
            class_variables=class_vars,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
        )
        self.classes.append(cls)

    def visit_Assign(self, node: ast.Assign) -> None:
        if self._scope_stack:
            return
        for target in node.targets:
            if isinstance(target, ast.Name) and not target.id.startswith("_"):
                self.variables.append(
                    VariableInfo(
                        name=target.id,
                        value_repr=_safe_unparse(node.value),
                        line=node.lineno,
                    )
                )

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if self._scope_stack:
            return
        if isinstance(node.target, ast.Name):
            self.variables.append(
                VariableInfo(
                    name=node.target.id,
                    annotation=_unparse_annotation(node.annotation),
                    value_repr=_safe_unparse(node.value) if node.value else None,
                    line=node.lineno,
                )
            )

    def _is_internal(self, module: str) -> bool:
        """Heuristic: internal if it shares a top-level package with this module."""
        if not module or not self.module_name:
            return False
        top = self.module_name.split(".")[0]
        return module.startswith(top)


# --- Helper functions ---


def _path_to_module(file_path: Path, root: Path) -> str:
    """Convert file path to Python module name."""
    relative = file_path.relative_to(root)
    parts = list(relative.parts)
    if parts[-1] == "__init__.py":
        parts = parts[:-1]
    else:
        parts[-1] = parts[-1].removesuffix(".py")
    return ".".join(parts)


def _extract_args(arguments: ast.arguments) -> list[ArgumentInfo]:
    """Extract argument info from function arguments node."""
    result: list[ArgumentInfo] = []
    all_args = arguments.posonlyargs + arguments.args + arguments.kwonlyargs

    # Compute defaults alignment (defaults are right-aligned to args)
    num_positional = len(arguments.posonlyargs) + len(arguments.args)
    defaults = [None] * (num_positional - len(arguments.defaults)) + list(arguments.defaults)
    kw_defaults = list(arguments.kw_defaults)

    for i, arg in enumerate(arguments.posonlyargs + arguments.args):
        default = defaults[i] if i < len(defaults) else None
        result.append(
            ArgumentInfo(
                name=arg.arg,
                annotation=_unparse_annotation(arg.annotation),
                default=_safe_unparse(default) if default else None,
            )
        )

    for i, arg in enumerate(arguments.kwonlyargs):
        default = kw_defaults[i] if i < len(kw_defaults) else None
        result.append(
            ArgumentInfo(
                name=arg.arg,
                annotation=_unparse_annotation(arg.annotation),
                default=_safe_unparse(default) if default else None,
            )
        )

    if arguments.vararg:
        result.append(
            ArgumentInfo(
                name=f"*{arguments.vararg.arg}",
                annotation=_unparse_annotation(arguments.vararg.annotation),
            )
        )
    if arguments.kwarg:
        result.append(
            ArgumentInfo(
                name=f"**{arguments.kwarg.arg}",
                annotation=_unparse_annotation(arguments.kwarg.annotation),
            )
        )

    return result


def _extract_calls(node: ast.AST) -> list[str]:
    """Extract all function/method calls within a node."""
    calls: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = _unparse_node(child.func)
            if name:
                calls.append(name)
    return list(dict.fromkeys(calls))  # dedupe preserving order


def _extract_class_variables(node: ast.ClassDef) -> list[str]:
    """Extract class-level variable names."""
    variables: list[str] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, ast.Assign):
            for target in child.targets:
                if isinstance(target, ast.Name):
                    variables.append(target.id)
        elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
            variables.append(child.target.id)
    return variables


def _unparse_annotation(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    return _safe_unparse(node)


def _unparse_decorator(node: ast.expr) -> str:
    return _safe_unparse(node) or ""


def _unparse_node(node: ast.expr) -> str:
    return _safe_unparse(node) or ""


def _safe_unparse(node: ast.AST | None) -> str | None:
    if node is None:
        return None
    try:
        return ast.unparse(node)
    except Exception:
        return None


def _extract_all(node: ast.expr) -> list[str] | None:
    """Extract __all__ list if it's a simple list of strings."""
    if isinstance(node, ast.List):
        result = []
        for elt in node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                result.append(elt.value)
        return result
    return None


def _estimate_complexity(node: ast.AST) -> int:
    """Simple cyclomatic complexity estimate."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    return complexity
