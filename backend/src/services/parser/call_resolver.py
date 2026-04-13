"""Build call edges by resolving cross-file function calls via AST walking."""
import ast
import textwrap
from src.models.domain import FunctionNode, CallEdge


def resolve_calls(
    functions: list[FunctionNode],
) -> tuple[list[FunctionNode], list[CallEdge]]:
    """Populate calls/called_by on each FunctionNode and return CallEdge list.

    Strategy (best-effort for Phase 1):
    1. Build name indices from the full function list.
    2. For each function, parse its source_code AST and walk for ast.Call nodes.
    3. Resolve each callee to a known FunctionNode ID using the indices.
    4. Cross-file resolution uses (class_name, method_name) pairs first,
       then falls back to simple name matching.

    Only calls whose callees exist in the project function list are recorded.
    External library calls (magic_pdf, asyncio, etc.) are silently ignored.
    """
    # ── Build lookup indices ─────────────────────────────────────────────────
    # simple function name → list of IDs (multiple files may have same name)
    name_to_ids: dict[str, list[str]] = {}
    # (ClassName, method_name) → function ID
    class_method_to_id: dict[tuple[str, str], str] = {}

    for fn in functions:
        name_to_ids.setdefault(fn.name, []).append(fn.id)
        if fn.class_name:
            class_method_to_id[(fn.class_name, fn.name)] = fn.id

    fn_by_id: dict[str, FunctionNode] = {fn.id: fn for fn in functions}
    call_edges: list[CallEdge] = []

    for fn in functions:
        callee_ids = _find_callees(fn, name_to_ids, class_method_to_id)

        for callee_id in callee_ids:
            if callee_id == fn.id:
                continue  # skip self-recursion edges for clarity
            if callee_id not in fn_by_id:
                continue

            fn.calls.append(callee_id)
            fn_by_id[callee_id].called_by.append(fn.id)

            call_edges.append(
                CallEdge(
                    id=f"call::{fn.id}::{callee_id}",
                    source_id=fn.id,
                    target_id=callee_id,
                    call_line=0,  # line tracking inside source_code deferred
                    edge_type="call",
                )
            )

    return list(fn_by_id.values()), call_edges


# ── Internal helpers ──────────────────────────────────────────────────────────

def _find_callees(
    fn: FunctionNode,
    name_to_ids: dict[str, list[str]],
    class_method_to_id: dict[tuple[str, str], str],
) -> list[str]:
    """Return deduplicated list of callee IDs found in fn.source_code."""
    try:
        dedented = textwrap.dedent(fn.source_code)
        tree = ast.parse(dedented)
    except SyntaxError:
        return []

    found: list[str] = []
    seen: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee_id = _resolve_callee(node.func, fn, name_to_ids, class_method_to_id)
        if callee_id and callee_id not in seen:
            seen.add(callee_id)
            found.append(callee_id)

    return found


def _resolve_callee(
    func_node: ast.expr,
    caller: FunctionNode,
    name_to_ids: dict[str, list[str]],
    class_method_to_id: dict[tuple[str, str], str],
) -> str | None:
    """Try to resolve a call node to a known FunctionNode ID."""

    # ── Simple call: func_name() ──────────────────────────────────────────────
    if isinstance(func_node, ast.Name):
        return _resolve_by_name(func_node.id, caller, name_to_ids)

    # ── Attribute call: obj.method() or Class.method() ───────────────────────
    if isinstance(func_node, ast.Attribute):
        method_name = func_node.attr

        # Try (ClassName, method_name) exact match first
        if isinstance(func_node.value, ast.Name):
            class_or_obj = func_node.value.id
            key = (class_or_obj, method_name)
            if key in class_method_to_id:
                return class_method_to_id[key]

        # Fall back to simple method name resolution
        return _resolve_by_name(method_name, caller, name_to_ids)

    return None


def _resolve_by_name(
    name: str,
    caller: FunctionNode,
    name_to_ids: dict[str, list[str]],
) -> str | None:
    """Resolve a plain function name to an ID.

    Preference order:
    1. Exact match in the same file.
    2. Unique match across the project.
    3. First match (ambiguous — best effort).
    """
    ids = name_to_ids.get(name)
    if not ids:
        return None
    if len(ids) == 1:
        return ids[0]

    # Prefer same-file matches
    same_file = [fid for fid in ids if fid.startswith(caller.file_path + "::")]
    if same_file:
        return same_file[0]

    return ids[0]
