"""
Tests for PLAN_route_test_ux.md — P0 + P1 implementation.

Coverage:
  1. port_detector  — all pattern variants + edge cases
  2. domain model   — ParsedProject.suggested_port field
  3. parser integration — suggested_port populated end-to-end
  4. HTTP API       — /project/parse response contains suggestedPort (camelCase)
"""
import os
import sys
import textwrap
import tempfile
import pytest

# ── Make backend/src importable ───────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.parser.port_detector import (
    detect_suggested_port,
    _scan_file_for_port,
)
from src.services.parser import parse_project
from src.models.domain import ParsedProject
from src.application import create_app
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _write_py(tmp_dir: str, filename: str, source: str) -> tuple[str, str]:
    """Write source to a temp .py file; return (abs_path, rel_path)."""
    abs_path = os.path.join(tmp_dir, filename)
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(source))
    return abs_path, filename


# ─────────────────────────────────────────────────────────────────────────────
# 1. port_detector unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPortDetector:

    def test_uvicorn_run_keyword_port(self, tmp_path):
        """Pattern A: uvicorn.run(app, port=8080)"""
        abs_path = tmp_path / "main.py"
        abs_path.write_text("import uvicorn\nuvicorn.run(app, port=8080)\n")
        result = _scan_file_for_port(str(abs_path))
        assert result == 8080

    def test_uvicorn_run_with_host_and_port(self, tmp_path):
        """Pattern A2: uvicorn.run('main:app', host='0.0.0.0', port=9000)"""
        abs_path = tmp_path / "main.py"
        abs_path.write_text(
            "import uvicorn\nuvicorn.run('main:app', host='0.0.0.0', port=9000)\n"
        )
        result = _scan_file_for_port(str(abs_path))
        assert result == 9000

    def test_uvicorn_run_inside_name_main_block(self, tmp_path):
        """Pattern C: port inside if __name__ == '__main__' block"""
        abs_path = tmp_path / "server.py"
        abs_path.write_text(
            "import uvicorn\n"
            "if __name__ == '__main__':\n"
            "    uvicorn.run(app, reload=True, port=5050)\n"
        )
        result = _scan_file_for_port(str(abs_path))
        assert result == 5050

    def test_app_run_flask_style(self, tmp_path):
        """Pattern D: app.run(port=5000)"""
        abs_path = tmp_path / "app.py"
        abs_path.write_text("app.run(host='0.0.0.0', port=5000, debug=True)\n")
        result = _scan_file_for_port(str(abs_path))
        assert result == 5000

    def test_no_port_returns_none(self, tmp_path):
        """No run() call → None"""
        abs_path = tmp_path / "noop.py"
        abs_path.write_text("x = 1 + 1\n")
        result = _scan_file_for_port(str(abs_path))
        assert result is None

    def test_run_without_port_kwarg_returns_none(self, tmp_path):
        """uvicorn.run(app) with no port keyword → None"""
        abs_path = tmp_path / "main.py"
        abs_path.write_text("import uvicorn\nuvicorn.run(app)\n")
        result = _scan_file_for_port(str(abs_path))
        assert result is None

    def test_port_as_variable_not_detected(self, tmp_path):
        """uvicorn.run(app, port=PORT_VAR) — variable, not literal → None"""
        abs_path = tmp_path / "main.py"
        abs_path.write_text(
            "PORT = 8000\nuvicorn.run(app, port=PORT)\n"
        )
        result = _scan_file_for_port(str(abs_path))
        assert result is None

    def test_port_out_of_range_rejected(self, tmp_path):
        """port=0 and port=99999 are out of valid range → None"""
        for bad_port in (0, 99999):
            abs_path = tmp_path / f"p{bad_port}.py"
            abs_path.write_text(f"uvicorn.run(app, port={bad_port})\n")
            assert _scan_file_for_port(str(abs_path)) is None

    def test_syntax_error_file_returns_none(self, tmp_path):
        """Unparseable file should not raise, returns None"""
        abs_path = tmp_path / "broken.py"
        abs_path.write_text("def (broken syntax\n")
        result = _scan_file_for_port(str(abs_path))
        assert result is None

    def test_missing_file_returns_none(self):
        """Non-existent file path → None, no exception"""
        result = _scan_file_for_port("/nonexistent/path/file.py")
        assert result is None

    def test_detect_suggested_port_returns_first_match(self, tmp_path):
        """detect_suggested_port picks the first file with a port"""
        f1 = tmp_path / "a.py"
        f2 = tmp_path / "b.py"
        f1.write_text("x = 1\n")                          # no port
        f2.write_text("uvicorn.run(app, port=7777)\n")    # has port
        py_files = [(str(f1), "a.py"), (str(f2), "b.py")]
        assert detect_suggested_port(py_files) == 7777

    def test_detect_suggested_port_empty_list(self):
        """Empty file list → None"""
        assert detect_suggested_port([]) is None

    def test_detect_suggested_port_none_when_no_ports(self, tmp_path):
        """All files without port → None"""
        f = tmp_path / "plain.py"
        f.write_text("pass\n")
        assert detect_suggested_port([(str(f), "plain.py")]) is None


# ─────────────────────────────────────────────────────────────────────────────
# 2. domain model — suggested_port field
# ─────────────────────────────────────────────────────────────────────────────

class TestDomainModel:

    def test_suggested_port_defaults_to_none(self):
        """ParsedProject.suggested_port should default to None."""
        project = ParsedProject(
            id="p1", name="test", root_path="/tmp/x", language="python",
            functions=[], schemas=[], external_apis=[],
            call_edges=[], data_flow_edges=[], entry_points=[],
        )
        assert project.suggested_port is None

    def test_suggested_port_accepts_integer(self):
        """ParsedProject.suggested_port stores a positive integer."""
        project = ParsedProject(
            id="p1", name="test", root_path="/tmp/x", language="python",
            functions=[], schemas=[], external_apis=[],
            call_edges=[], data_flow_edges=[], entry_points=[],
            suggested_port=8080,
        )
        assert project.suggested_port == 8080

    def test_suggested_port_serialises_to_camel_case(self):
        """model_dump(by_alias=True) must produce suggestedPort (camelCase)."""
        project = ParsedProject(
            id="p1", name="test", root_path="/tmp/x", language="python",
            functions=[], schemas=[], external_apis=[],
            call_edges=[], data_flow_edges=[], entry_points=[],
            suggested_port=3000,
        )
        data = project.model_dump(by_alias=True)
        assert "suggestedPort" in data
        assert data["suggestedPort"] == 3000

    def test_suggested_port_none_serialises_to_null(self):
        """None suggested_port serialises as null (camelCase key still present)."""
        project = ParsedProject(
            id="p1", name="test", root_path="/tmp/x", language="python",
            functions=[], schemas=[], external_apis=[],
            call_edges=[], data_flow_edges=[], entry_points=[],
        )
        data = project.model_dump(by_alias=True)
        assert "suggestedPort" in data
        assert data["suggestedPort"] is None


# ─────────────────────────────────────────────────────────────────────────────
# 3. Parser integration — suggested_port populated end-to-end
# ─────────────────────────────────────────────────────────────────────────────

class TestParserIntegration:

    def test_parser_detects_port_from_uvicorn_run(self, tmp_path):
        """Full parse_project run: project with uvicorn.run → suggestedPort set."""
        main_py = tmp_path / "main.py"
        main_py.write_text(
            "from fastapi import FastAPI\n"
            "import uvicorn\n\n"
            "app = FastAPI()\n\n"
            "@app.get('/health')\n"
            "def health(): return {'ok': True}\n\n"
            "if __name__ == '__main__':\n"
            "    uvicorn.run(app, host='0.0.0.0', port=8765)\n"
        )
        project = parse_project(str(tmp_path))
        assert project.suggested_port == 8765

    def test_parser_returns_none_when_no_port(self):
        """TestProject has no uvicorn.run → suggested_port is None."""
        test_project_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "../../example/TestProject")
        )
        if not os.path.isdir(test_project_path):
            pytest.skip("TestProject not found")
        project = parse_project(test_project_path)
        assert project.suggested_port is None

    def test_parser_multifile_picks_first_port(self, tmp_path):
        """When multiple files have ports, the first found wins."""
        (tmp_path / "a_first.py").write_text(
            "import uvicorn\nuvicorn.run('app:app', port=1111)\n"
        )
        (tmp_path / "b_second.py").write_text(
            "import uvicorn\nuvicorn.run('app:app', port=2222)\n"
        )
        project = parse_project(str(tmp_path))
        # Port must be one of the two declared; exact file ordering is OS-dependent
        assert project.suggested_port in (1111, 2222)


# ─────────────────────────────────────────────────────────────────────────────
# 4. HTTP API — /project/parse returns suggestedPort in JSON
# ─────────────────────────────────────────────────────────────────────────────

class TestHTTPAPI:

    @pytest.fixture(scope="class")
    def client(self):
        app = create_app()
        return TestClient(app)

    def test_parse_project_response_has_suggested_port_key(self, client, tmp_path):
        """POST /project/parse always returns suggestedPort key (null or int)."""
        main_py = tmp_path / "main.py"
        main_py.write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n\n"
            "@app.get('/')\n"
            "def root(): return {}\n"
        )
        resp = client.post("/project/parse", json={"rootPath": str(tmp_path)})
        assert resp.status_code == 200
        body = resp.json()
        assert "project" in body
        assert "suggestedPort" in body["project"]

    def test_parse_project_response_suggested_port_null_when_no_uvicorn(self, client, tmp_path):
        """No uvicorn.run in project → suggestedPort is null in JSON."""
        (tmp_path / "app.py").write_text(
            "from fastapi import FastAPI\napp = FastAPI()\n"
        )
        resp = client.post("/project/parse", json={"rootPath": str(tmp_path)})
        assert resp.status_code == 200
        assert resp.json()["project"]["suggestedPort"] is None

    def test_parse_project_response_suggested_port_integer_when_uvicorn(self, client, tmp_path):
        """uvicorn.run with port=6543 → suggestedPort is 6543 in JSON."""
        (tmp_path / "main.py").write_text(
            "from fastapi import FastAPI\n"
            "import uvicorn\n"
            "app = FastAPI()\n\n"
            "@app.get('/')\n"
            "def root(): return {}\n\n"
            "if __name__ == '__main__':\n"
            "    uvicorn.run(app, port=6543)\n"
        )
        resp = client.post("/project/parse", json={"rootPath": str(tmp_path)})
        assert resp.status_code == 200
        assert resp.json()["project"]["suggestedPort"] == 6543
