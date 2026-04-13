"""Detect FastAPI routes, main() blocks, and CLI commands from parsed functions."""
import re
from src.models.domain import FunctionNode, EntryPoint

_HTTP_METHODS = ("get", "post", "put", "delete", "patch", "options", "head")

# Matches @router.post("/path") or @app.get('/path')
_ROUTE_PATTERN = re.compile(
    r'@(?:router|app)\.(' + "|".join(_HTTP_METHODS) + r')\(\s*["\']([^"\']+)["\']',
    re.IGNORECASE,
)


def detect_entry_points(functions: list[FunctionNode]) -> list[EntryPoint]:
    """Scan function source_code for FastAPI route decorators.

    Also detects module-level functions named 'main'.

    Args:
        functions: All FunctionNode objects parsed from the project.

    Returns:
        List of EntryPoint, one per detected route/main.
    """
    entry_points: list[EntryPoint] = []
    seen_ids: set[str] = set()

    for fn in functions:
        # ── FastAPI routes ────────────────────────────────────────────────────
        for match in _ROUTE_PATTERN.finditer(fn.source_code):
            http_method = match.group(1).upper()
            route_path = match.group(2)

            ep_id = f"entry::{http_method}::{route_path}"
            if ep_id in seen_ids:
                continue
            seen_ids.add(ep_id)

            entry_points.append(
                EntryPoint(
                    id=ep_id,
                    label=f"{http_method} {route_path}",
                    function_id=fn.id,
                    entry_type="fastapi_route",
                )
            )

        # ── main() function ───────────────────────────────────────────────────
        if fn.name == "main" and fn.class_name is None:
            ep_id = f"entry::main::{fn.file_path}"
            if ep_id not in seen_ids:
                seen_ids.add(ep_id)
                entry_points.append(
                    EntryPoint(
                        id=ep_id,
                        label=f"main() in {fn.file_path}",
                        function_id=fn.id,
                        entry_type="main_function",
                    )
                )

    return entry_points
