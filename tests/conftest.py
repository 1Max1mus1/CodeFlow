import sys
import os

# Make backend/src importable from tests/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

# Load backend/.env into os.environ so MOONSHOT_API_KEY is available for skipif checks
_env_file = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
if os.path.isfile(_env_file):
    with open(_env_file, encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())
