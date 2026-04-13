"""Extract FunctionNode list from a single .py file using the ast module."""
import ast
import textwrap
from src.models.domain import FunctionNode, ParamInfo


def extract_functions(abs_file_path: str, rel_file_path: str) -> list[FunctionNode]:
    """Parse a Python file and return all top-level and class-method functions.

    Args:
        abs_file_path: Absolute path used for reading the file.
        rel_file_path: Path relative to project root, used in node IDs.

    Returns:
        List of FunctionNode (calls/called_by left empty — populated by call_resolver).
    """
    try:
        source = abs_file_path and open(abs_file_path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    source_lines = source.splitlines()
    extractor = _FunctionExtractor(source, source_lines, rel_file_path)
    extractor.visit(tree)
    return extractor.functions


class _FunctionExtractor(ast.NodeVisitor):
    def __init__(self, source: str, source_lines: list[str], rel_file_path: str) -> None:
        self.source = source
        self.source_lines = source_lines
        self.rel_file_path = rel_file_path
        self.functions: list[FunctionNode] = []
        self._class_stack: list[str] = []

    # ── Class context tracking ────────────────────────────────────────────────

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    # ── Function visitors ─────────────────────────────────────────────────────

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._extract(node, is_async=False)
        # Do NOT recurse into nested functions — only top-level and class methods

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._extract(node, is_async=True)

    # ── Core extraction ───────────────────────────────────────────────────────

    def _extract(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        class_name = self._class_stack[-1] if self._class_stack else None

        fn_id = (
            f"{self.rel_file_path}::{class_name}::{node.name}"
            if class_name
            else f"{self.rel_file_path}::{node.name}"
        )

        return_type = ast.unparse(node.returns) if node.returns else None
        source_code = self._get_source_with_decorators(node)
        params = self._extract_params(node.args)

        self.functions.append(
            FunctionNode(
                id=fn_id,
                name=node.name,
                file_path=self.rel_file_path,
                class_name=class_name,
                is_async=is_async,
                params=params,
                return_type=return_type,
                source_code=source_code,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                calls=[],
                called_by=[],
                uses_schemas=[],
            )
        )

    def _get_source_with_decorators(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> str:
        """Return source lines including any decorators above the function."""
        start = node.lineno  # def/async def line (1-indexed)
        if node.decorator_list:
            start = node.decorator_list[0].lineno
        end = node.end_lineno or node.lineno
        return "\n".join(self.source_lines[start - 1 : end])

    def _extract_params(self, args: ast.arguments) -> list[ParamInfo]:
        params: list[ParamInfo] = []
        all_args = args.posonlyargs + args.args
        n_defaults = len(args.defaults)
        default_offset = len(all_args) - n_defaults

        for i, arg in enumerate(all_args):
            if arg.arg in ("self", "cls"):
                continue
            type_str = ast.unparse(arg.annotation) if arg.annotation else None
            has_default = i >= default_offset
            default_str = (
                ast.unparse(args.defaults[i - default_offset]) if has_default else None
            )
            params.append(
                ParamInfo(
                    name=arg.arg,
                    type=type_str,
                    default=default_str,
                    is_optional=has_default,
                )
            )

        # keyword-only args
        for j, kwarg in enumerate(args.kwonlyargs):
            kw_default = args.kw_defaults[j]
            params.append(
                ParamInfo(
                    name=kwarg.arg,
                    type=ast.unparse(kwarg.annotation) if kwarg.annotation else None,
                    default=ast.unparse(kw_default) if kw_default else None,
                    is_optional=kw_default is not None,
                )
            )

        return params
