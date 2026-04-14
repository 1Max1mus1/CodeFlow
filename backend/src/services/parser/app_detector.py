"""Detect FastAPI app / APIRouter instances in Python source files."""
import ast
from src.models.domain import AppInstance


_FASTAPI_NAMES = {"FastAPI"}
_ROUTER_NAMES = {"APIRouter"}


def detect_app_instances(abs_file_path: str, rel_file_path: str) -> list[AppInstance]:
    """Return AppInstance entries found in a single .py file.

    Matches patterns like:
        app = FastAPI(...)
        router = APIRouter(...)
        app = fastapi.FastAPI(...)
    """
    try:
        source = open(abs_file_path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    instances: list[AppInstance] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        call = node.value
        if not isinstance(call, ast.Call):
            continue

        func_name = _resolve_call_name(call.func)
        if func_name is None:
            continue

        if func_name in _FASTAPI_NAMES:
            instance_type = "fastapi"
        elif func_name in _ROUTER_NAMES:
            instance_type = "apirouter"
        else:
            continue

        for target in node.targets:
            if isinstance(target, ast.Name):
                instances.append(AppInstance(
                    var_name=target.id,
                    file_path=rel_file_path,
                    instance_type=instance_type,
                ))

    return instances


def _resolve_call_name(func_node: ast.expr) -> str | None:
    """Extract the bare class name from a Call's func node.

    Handles: FastAPI() → 'FastAPI'
             fastapi.FastAPI() → 'FastAPI'
    """
    if isinstance(func_node, ast.Name):
        return func_node.id
    if isinstance(func_node, ast.Attribute):
        return func_node.attr
    return None
