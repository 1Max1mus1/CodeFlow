"""Walk a project directory and return all .py file paths."""
import os

_EXCLUDED_DIRS = {
    "__pycache__", ".venv", "venv", ".git", "node_modules",
    "build", "dist", ".mypy_cache", ".pytest_cache", ".tox",
}
_EXCLUDED_FILE_PREFIXES = ("test_",)


def scan_python_files(root_path: str, exclude_tests: bool = False) -> list[str]:
    """Return absolute paths of all .py files under root_path.

    Args:
        root_path: Absolute path to the project root directory.
        exclude_tests: If True, skip files whose names start with 'test_'.

    Returns:
        Sorted list of absolute file paths.
    """
    result: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Prune excluded dirs in-place so os.walk does not recurse into them
        dirnames[:] = sorted(d for d in dirnames if d not in _EXCLUDED_DIRS)

        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            if exclude_tests and filename.startswith(_EXCLUDED_FILE_PREFIXES):
                continue
            result.append(os.path.join(dirpath, filename))

    return result
