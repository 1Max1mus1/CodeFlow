"""
Tests for the generate_test operation feature.

Coverage:
  1. app_detector   — finds FastAPI/APIRouter instances in source files
  2. parser         — app_instances populated in ParsedProject
  3. analyzer       — _analyze_generate_test returns correct questions
  4. generator      — _generate_test_diffs calls AI and returns a FileDiff (AI mocked)
  5. router (HTTP)  — full POST /operation flow with generate_test type (AI mocked)
"""
import os
import sys
import types
import textwrap
import tempfile
import pytest
import pytest_asyncio

# ── Make backend/src importable ───────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.services.parser.app_detector import detect_app_instances
from src.services.parser import parse_project
from src.services.ai.analyzer import analyze_operation
from src.models.domain import (
    Operation, ParsedProject, FunctionNode, SchemaNode,
    EntryPoint, AppInstance, ParamInfo,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

TEST_PROJECT_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "../../example/TestProject")
)

DUMMY_FN = FunctionNode(
    id="main.py::create_new_task",
    name="create_new_task",
    file_path="main.py",
    class_name=None,
    is_async=False,
    params=[ParamInfo(name="data", type="TaskCreate", default=None, is_optional=False)],
    return_type="Task",
    source_code="def create_new_task(data: TaskCreate) -> Task: ...",
    start_line=1,
    end_line=3,
    calls=[],
    called_by=[],
    uses_schemas=[],
)

DUMMY_PROJECT = ParsedProject(
    id="proj-test",
    name="TestProject",
    root_path=TEST_PROJECT_PATH,
    language="python",
    functions=[DUMMY_FN],
    schemas=[],
    external_apis=[],
    call_edges=[],
    data_flow_edges=[],
    entry_points=[
        EntryPoint(
            id="entry::POST::/tasks",
            label="POST /tasks",
            function_id=DUMMY_FN.id,
            entry_type="fastapi_route",
        )
    ],
    app_instances=[
        AppInstance(var_name="app", file_path="main.py", instance_type="fastapi")
    ],
)

DUMMY_OPERATION = Operation(
    id="op-test01",
    session_id="sess-test",
    project_id="proj-test",
    type="generate_test",
    target_node_id=DUMMY_FN.id,
    new_node_id=None,
    status="analyzing",
    ai_questions=[],
    generated_diffs=None,
    error_message=None,
)


# ─────────────────────────────────────────────────────────────────────────────
# 1. app_detector unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAppDetector:
    def _write_tmp(self, source: str) -> tuple[str, str]:
        """Write source to a temp file, return (abs_path, rel_path)."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(textwrap.dedent(source))
            return fh.name, "main.py"

    def test_detects_fastapi_instance(self):
        abs_path, rel_path = self._write_tmp("""
            from fastapi import FastAPI
            app = FastAPI()
        """)
        try:
            result = detect_app_instances(abs_path, rel_path)
        finally:
            os.unlink(abs_path)

        assert len(result) == 1
        assert result[0].var_name == "app"
        assert result[0].instance_type == "fastapi"
        assert result[0].file_path == rel_path

    def test_detects_apirouter_instance(self):
        abs_path, rel_path = self._write_tmp("""
            from fastapi import APIRouter
            router = APIRouter(prefix="/tasks")
        """)
        try:
            result = detect_app_instances(abs_path, rel_path)
        finally:
            os.unlink(abs_path)

        assert len(result) == 1
        assert result[0].var_name == "router"
        assert result[0].instance_type == "apirouter"

    def test_detects_dotted_import(self):
        """fastapi.FastAPI() style should also be detected."""
        abs_path, rel_path = self._write_tmp("""
            import fastapi
            app = fastapi.FastAPI()
        """)
        try:
            result = detect_app_instances(abs_path, rel_path)
        finally:
            os.unlink(abs_path)

        assert len(result) == 1
        assert result[0].instance_type == "fastapi"

    def test_no_false_positives(self):
        """Plain class instantiation should not be detected."""
        abs_path, rel_path = self._write_tmp("""
            class MyApp:
                pass
            app = MyApp()
        """)
        try:
            result = detect_app_instances(abs_path, rel_path)
        finally:
            os.unlink(abs_path)

        assert result == []

    def test_empty_file(self):
        abs_path, rel_path = self._write_tmp("")
        try:
            result = detect_app_instances(abs_path, rel_path)
        finally:
            os.unlink(abs_path)
        assert result == []

    def test_syntax_error_file(self):
        abs_path, rel_path = self._write_tmp("def broken(: pass")
        try:
            result = detect_app_instances(abs_path, rel_path)
        finally:
            os.unlink(abs_path)
        assert result == []


# ─────────────────────────────────────────────────────────────────────────────
# 2. Parser integration — app_instances in ParsedProject
# ─────────────────────────────────────────────────────────────────────────────

class TestParserAppInstances:
    def test_testproject_has_app_instance(self):
        """parse_project on TestProject should detect the FastAPI app in main.py."""
        if not os.path.isdir(TEST_PROJECT_PATH):
            pytest.skip(f"TestProject not found at {TEST_PROJECT_PATH}")

        project = parse_project(TEST_PROJECT_PATH)

        assert hasattr(project, "app_instances"), "ParsedProject missing app_instances field"
        assert len(project.app_instances) >= 1, "Should detect at least one FastAPI app"

        app = project.app_instances[0]
        assert app.instance_type == "fastapi"
        assert app.var_name == "app"
        assert "main.py" in app.file_path

    def test_testproject_functions_parsed(self):
        """Sanity check — TestProject has functions and entry points."""
        if not os.path.isdir(TEST_PROJECT_PATH):
            pytest.skip(f"TestProject not found at {TEST_PROJECT_PATH}")

        project = parse_project(TEST_PROJECT_PATH)
        assert len(project.functions) > 0
        assert len(project.entry_points) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Analyzer unit tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAnalyzeGenerateTest:
    @pytest.mark.asyncio
    async def test_returns_awaiting_user(self):
        result = await analyze_operation(DUMMY_OPERATION, DUMMY_PROJECT)
        assert result.status == "awaiting_user"

    @pytest.mark.asyncio
    async def test_has_two_questions(self):
        result = await analyze_operation(DUMMY_OPERATION, DUMMY_PROJECT)
        assert len(result.ai_questions) == 2

    @pytest.mark.asyncio
    async def test_scenario_question_has_options(self):
        result = await analyze_operation(DUMMY_OPERATION, DUMMY_PROJECT)
        q_scenario = next(q for q in result.ai_questions if q.id == "q-scenario")
        assert q_scenario.options is not None
        assert len(q_scenario.options) >= 2

    @pytest.mark.asyncio
    async def test_filepath_question_default_contains_source_stem(self):
        result = await analyze_operation(DUMMY_OPERATION, DUMMY_PROJECT)
        q_fp = next(q for q in result.ai_questions if q.id == "q-filepath")
        # Default option should reference the source file stem "main"
        assert q_fp.options is not None
        assert any("main" in opt for opt in q_fp.options)

    @pytest.mark.asyncio
    async def test_unknown_function_returns_error_question(self):
        bad_op = DUMMY_OPERATION.model_copy(
            update={"target_node_id": "nonexistent::fn"}
        )
        result = await analyze_operation(bad_op, DUMMY_PROJECT)
        assert result.status == "awaiting_user"
        assert len(result.ai_questions) == 1
        assert result.ai_questions[0].options == ["Cancel"]


# ─────────────────────────────────────────────────────────────────────────────
# 4. Generator unit test — AI mocked
# ─────────────────────────────────────────────────────────────────────────────

MOCK_TEST_CONTENT = '''\
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_create_new_task_success():
    """Success path: create a valid task."""
    payload = {"title": "test", "status": "pending"}
    resp = client.post("/tasks", json=payload)
    assert resp.status_code == 201
'''


class TestGenerateTestDiffs:
    @pytest.mark.asyncio
    async def test_generates_diff_for_new_file(self, monkeypatch, tmp_path):
        """Generator should produce a FileDiff with old_content='' for a new test file."""
        from src.services.ai import generator as gen_module

        # Patch _make_client to return a mock that yields MOCK_TEST_CONTENT
        class _MockChoice:
            class message:
                content = MOCK_TEST_CONTENT

        class _MockCompletion:
            choices = [_MockChoice()]

        class _MockChat:
            class completions:
                @staticmethod
                async def create(**kwargs):
                    return _MockCompletion()

        class _MockClient:
            chat = _MockChat()

        monkeypatch.setattr(gen_module, "_make_client", lambda: _MockClient())

        # Give the operation answered questions
        answered_op = DUMMY_OPERATION.model_copy(update={
            "ai_questions": [
                q.model_copy(update={"user_answer": ans})
                for q, ans in zip(
                    (await analyze_operation(DUMMY_OPERATION, DUMMY_PROJECT)).ai_questions,
                    ["成功 + 错误路径（推荐）", "tests/test_main.py"],
                )
            ]
        })

        # Use a project with a real-looking root so os.path.exists works
        project = DUMMY_PROJECT.model_copy(update={"root_path": str(tmp_path)})

        from src.services.ai.generator import generate_diffs
        result = await generate_diffs(answered_op, project)

        assert result.status == "ready"
        assert result.generated_diffs is not None
        assert len(result.generated_diffs) == 1

        diff = result.generated_diffs[0]
        assert diff.file_path == "tests/test_main.py"
        assert diff.old_content == ""          # new file
        assert "TestClient" in diff.new_content

    @pytest.mark.asyncio
    async def test_existing_file_used_as_old_content(self, monkeypatch, tmp_path):
        """If the test file already exists, old_content should be its current content."""
        from src.services.ai import generator as gen_module

        existing_content = "# existing tests\n"
        test_file = tmp_path / "tests" / "test_main.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text(existing_content, encoding="utf-8")

        class _MockChoice:
            class message:
                content = MOCK_TEST_CONTENT

        class _MockCompletion:
            choices = [_MockChoice()]

        class _MockChat:
            class completions:
                @staticmethod
                async def create(**kwargs):
                    return _MockCompletion()

        class _MockClient:
            chat = _MockChat()

        monkeypatch.setattr(gen_module, "_make_client", lambda: _MockClient())

        answered_op = DUMMY_OPERATION.model_copy(update={
            "ai_questions": [
                q.model_copy(update={"user_answer": ans})
                for q, ans in zip(
                    (await analyze_operation(DUMMY_OPERATION, DUMMY_PROJECT)).ai_questions,
                    ["成功 + 错误路径（推荐）", "tests/test_main.py"],
                )
            ]
        })

        project = DUMMY_PROJECT.model_copy(update={"root_path": str(tmp_path)})

        from src.services.ai.generator import generate_diffs
        result = await generate_diffs(answered_op, project)

        diff = result.generated_diffs[0]
        assert diff.old_content == existing_content


# ─────────────────────────────────────────────────────────────────────────────
# 5. HTTP router integration test — AI mocked via monkeypatch
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_router_submit_generate_test(monkeypatch):
    """POST /operation with generate_test type should return awaiting_user + 2 questions."""
    from httpx import AsyncClient, ASGITransport
    from src.application import create_app
    from src.services.session import store
    fastapi_app = create_app()

    # Seed project + session into the in-memory store
    store.save_project(DUMMY_PROJECT)

    from src.models.domain import GraphSession, NodePosition
    session = GraphSession(
        id="sess-http-test",
        project_id="proj-test",
        active_entry_point_id="entry::POST::/tasks",
        visible_node_ids=[DUMMY_FN.id],
        node_positions={DUMMY_FN.id: NodePosition(x=0, y=0)},
        pending_operation_id=None,
    )
    store.save_session(session)

    async with AsyncClient(
        transport=ASGITransport(app=fastapi_app), base_url="http://test"
    ) as client:
        resp = await client.post("/operation", json={
            "sessionId": "sess-http-test",
            "operationType": "generate_test",
            "targetNodeId": DUMMY_FN.id,
            "newNodeId": None,
        })

    assert resp.status_code == 200, resp.text
    data = resp.json()
    op = data["operation"]
    assert op["status"] == "awaiting_user"
    assert len(op["aiQuestions"]) == 2
    ids = {q["id"] for q in op["aiQuestions"]}
    assert "q-scenario" in ids
    assert "q-filepath" in ids
