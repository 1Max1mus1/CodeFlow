"""Detect the uvicorn/ASGI/WSGI startup port from Python source files.

Scans project .py files for patterns like:
    uvicorn.run(app, port=8080)
    uvicorn.run("main:app", host="0.0.0.0", port=8080)
    app.run(port=5000)

Returns the first statically-determinable integer port, or None.
"""
import ast
from pathlib import Path


def detect_suggested_port(py_files: list[tuple[str, str]]) -> int | None:
    """Return the first detected startup port from the given file list.

    Args:
        py_files: List of (abs_path, rel_path) tuples, in scan order.

    Returns:
        An integer port number (1–65535), or None if not found.
    """
    for abs_path, _ in py_files:
        port = _scan_file_for_port(abs_path)
        if port is not None:
            return port
    return None


def _scan_file_for_port(abs_path: str) -> int | None:
    try:
        source = Path(abs_path).read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, SyntaxError, UnicodeDecodeError):
        return None

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_run_call(node.func):
            continue
        port = _extract_port_kwarg(node)
        if port is not None:
            return port
    return None


def _is_run_call(func: ast.expr) -> bool:
    """Match `.run(...)` attribute calls and bare `run(...)` name calls."""
    if isinstance(func, ast.Attribute) and func.attr == "run":
        return True
    if isinstance(func, ast.Name) and func.id == "run":
        return True
    return False


def _extract_port_kwarg(call: ast.Call) -> int | None:
    """Extract the integer value of the `port=` keyword argument, if present."""
    for kw in call.keywords:
        if kw.arg == "port" and isinstance(kw.value, ast.Constant):
            v = kw.value.value
            if isinstance(v, int) and 1 <= v <= 65535:
                return v
    return None
