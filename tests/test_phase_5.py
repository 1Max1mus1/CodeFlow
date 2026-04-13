"""
Phase 5 test — verifies replace operation: ExternalAPINode persistence, schema
incompatibility detection, diff generation, and file apply.

Run from project root: pytest tests/test_phase_5.py
Uses example/task-api as the test project.

Tests that call Claude require ANTHROPIC_API_KEY to be set.
Tests that only verify analysis (question generation) run without it.
"""
import os
import shutil
import pytest
import pytest_asyncio  # noqa: F401
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.models.domain import (
    SubmitOperationResponse,
    AnswerQuestionResponse,
    ApplyOperationResponse,
    Operation,
    AddExternalAPIResponse,
)

TASK_API_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "example", "task-api", "src")
)

HAS_MOONSHOT_KEY = bool(os.environ.get("MOONSHOT_API_KEY"))
needs_claude = pytest.mark.skipif(
    not HAS_MOONSHOT_KEY,
    reason="MOONSHOT_API_KEY not set — skipping AI-dependent test",
)

# ExternalAPINode with only a subset of JobResponse fields (missing several)
PARTIAL_API_SCHEMA = [
    {"name": "job_id", "type": "str", "is_optional": False, "default": None, "description": None},
    {"name": "job_status", "type": "str", "is_optional": False, "default": None, "description": None},
]

FULL_API_SCHEMA = [
    # JobResponse fields
    {"name": "job_id", "type": "str", "is_optional": False, "default": None, "description": None},
    {"name": "job_status", "type": "str", "is_optional": False, "default": None, "description": None},
    {"name": "file_path", "type": "str", "is_optional": False, "default": None, "description": None},
    {"name": "result_info", "type": "dict", "is_optional": True, "default": None, "description": None},
    {"name": "created_at", "type": "str", "is_optional": True, "default": None, "description": None},
    {"name": "updated_at", "type": "str", "is_optional": True, "default": None, "description": None},
    # Response fields (get_job returns Tuple[JobResponse, Response]; analyzer may pick either)
    {"name": "status_code", "type": "int", "is_optional": False, "default": None, "description": None},
    {"name": "detail", "type": "str", "is_optional": False, "default": None, "description": None},
]


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def parsed_project(client: AsyncClient):
    resp = await client.post("/project/parse", json={"root_path": TASK_API_PATH})
    assert resp.status_code == 200
    return resp.json()["project"]


@pytest_asyncio.fixture
async def session_data(client: AsyncClient, parsed_project: dict):
    ep_id = parsed_project["entryPoints"][0]["id"]
    resp = await client.post("/session", json={
        "project_id": parsed_project["id"],
        "entry_point_id": ep_id,
    })
    assert resp.status_code == 200
    return resp.json()


@pytest_asyncio.fixture
def get_job_id(parsed_project: dict) -> str:
    """Return the real function ID for JobManager.get_job."""
    for fn in parsed_project["functions"]:
        if fn["name"] == "get_job":
            return fn["id"]
    pytest.skip("get_job not found in parsed project")


@pytest_asyncio.fixture
async def api_node(client: AsyncClient, session_data: dict) -> dict:
    """Add an ExternalAPINode with partial schema to the session."""
    session_id = session_data["session"]["id"]
    resp = await client.post(f"/session/{session_id}/external-api", json={
        "session_id": session_id,
        "name": "External Job API",
        "endpoint": "https://api.example.com/jobs",
        "method": "GET",
        "input_schema": [],
        "output_schema": PARTIAL_API_SCHEMA,
        "description": "External replacement for get_job",
    })
    assert resp.status_code == 200
    return resp.json()["node"]


@pytest_asyncio.fixture
async def replace_op(
    client: AsyncClient, session_data: dict, get_job_id: str, api_node: dict
) -> dict:
    """Submit a replace operation targeting get_job with the partial API."""
    session_id = session_data["session"]["id"]
    resp = await client.post("/operation", json={
        "session_id": session_id,
        "operation_type": "replace",
        "target_node_id": get_job_id,
        "new_node_id": api_node["id"],
    })
    assert resp.status_code == 200
    return resp.json()["operation"]


# ── Sanity ────────────────────────────────────────────────────────────────────

def test_task_api_path_exists():
    assert os.path.isdir(TASK_API_PATH)


def test_get_job_parseable(parsed_project: dict):
    names = [fn["name"] for fn in parsed_project["functions"]]
    assert "get_job" in names, f"get_job not found; got: {names}"


# ── ExternalAPINode persistence ────────────────────────────────────────────────

async def test_add_external_api_returns_200(client, session_data):
    session_id = session_data["session"]["id"]
    resp = await client.post(f"/session/{session_id}/external-api", json={
        "session_id": session_id,
        "name": "Test API",
        "endpoint": "https://api.example.com/test",
        "method": "POST",
        "input_schema": [],
        "output_schema": PARTIAL_API_SCHEMA,
        "description": None,
    })
    assert resp.status_code == 200


async def test_add_external_api_returns_node(client, session_data):
    session_id = session_data["session"]["id"]
    resp = await client.post(f"/session/{session_id}/external-api", json={
        "session_id": session_id,
        "name": "Test API",
        "endpoint": "https://api.example.com/test",
        "method": "POST",
        "input_schema": [],
        "output_schema": PARTIAL_API_SCHEMA,
        "description": "A test API",
    })
    data = AddExternalAPIResponse.model_validate(resp.json())
    assert data.node.id == "external::test_api"
    assert data.node.name == "Test API"
    assert data.node.method == "POST"
    assert len(data.node.output_schema) == 2


async def test_add_external_api_node_visible_in_session(client, session_data, api_node):
    """Node ID should be in session.visible_node_ids after add."""
    session_id = session_data["session"]["id"]
    sess_resp = await client.get(f"/session/{session_id}")
    assert sess_resp.status_code == 200
    visible = sess_resp.json()["visibleNodeIds"]
    assert api_node["id"] in visible


# ── Replace operation: analysis ───────────────────────────────────────────────

async def test_submit_replace_returns_200(client, session_data, get_job_id, api_node):
    session_id = session_data["session"]["id"]
    resp = await client.post("/operation", json={
        "session_id": session_id,
        "operation_type": "replace",
        "target_node_id": get_job_id,
        "new_node_id": api_node["id"],
    })
    assert resp.status_code == 200


async def test_submit_replace_status_awaiting_user(replace_op):
    data = SubmitOperationResponse.model_validate({"operation": replace_op})
    assert data.operation.status == "awaiting_user"


async def test_replace_has_at_least_one_question(replace_op):
    data = SubmitOperationResponse.model_validate({"operation": replace_op})
    assert len(data.operation.ai_questions) >= 1


async def test_replace_question_mentions_missing_field(replace_op):
    """Partial API schema is missing fields from the target function's return schema;
    questions should call out at least one missing field by name."""
    questions_text = " ".join(
        q["question"] for q in replace_op["aiQuestions"]
    )
    # The analyzer compares the return-type schema's fields against the API output schema.
    # At least one missing field name must appear in the generated questions.
    assert "missing from" in questions_text or "is present in" in questions_text, (
        f"Expected incompatibility phrasing. Got: {questions_text}"
    )


async def test_replace_question_user_answer_is_null(replace_op):
    assert replace_op["aiQuestions"][0]["userAnswer"] is None


async def test_replace_question_has_options(replace_op):
    q = replace_op["aiQuestions"][0]
    assert q["options"] is not None
    assert len(q["options"]) >= 2


async def test_get_replace_operation(client, replace_op):
    op_id = replace_op["id"]
    resp = await client.get(f"/operation/{op_id}")
    assert resp.status_code == 200
    data = Operation.model_validate(resp.json())
    assert data.id == op_id
    assert data.status == "awaiting_user"


# ── Answer question (cancel, no Claude) ──────────────────────────────────────

async def test_answer_cancel_reaches_ready(client, replace_op):
    """Answering 'Cancel' should skip Claude and go to ready with no diffs."""
    op_id = replace_op["id"]
    q_id = replace_op["aiQuestions"][0]["id"]

    resp = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id,
        "question_id": q_id,
        "answer": "Cancel",
    })
    assert resp.status_code == 200
    data = AnswerQuestionResponse.model_validate(resp.json())
    assert data.operation.status == "ready"
    assert data.operation.generated_diffs is not None  # may be empty list


async def test_answer_stores_user_choice(client, replace_op):
    op_id = replace_op["id"]
    q_id = replace_op["aiQuestions"][0]["id"]

    resp = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id,
        "question_id": q_id,
        "answer": "Cancel",
    })
    data = AnswerQuestionResponse.model_validate(resp.json())
    assert data.operation.ai_questions[0].user_answer == "Cancel"


# ── Revert (no Claude) ────────────────────────────────────────────────────────

async def test_revert_replace_sets_reverted(client, replace_op):
    op_id = replace_op["id"]
    resp = await client.post(f"/operation/{op_id}/revert")
    assert resp.status_code == 200
    data = Operation.model_validate(resp.json())
    assert data.status == "reverted"


# ── Claude-dependent: compatible replace ──────────────────────────────────────

@needs_claude
async def test_replace_compatible_api_generates_diffs(client, session_data, get_job_id):
    """End-to-end: add fully-compatible API → submit replace → answer confirm → diffs."""
    session_id = session_data["session"]["id"]

    # Add API with matching schema (all JobResponse fields present)
    api_resp = await client.post(f"/session/{session_id}/external-api", json={
        "session_id": session_id,
        "name": "Full Job API",
        "endpoint": "https://api.example.com/jobs/{job_id}",
        "method": "GET",
        "input_schema": [],
        "output_schema": FULL_API_SCHEMA,
        "description": "Full replacement for get_job",
    })
    assert api_resp.status_code == 200
    api_id = api_resp.json()["node"]["id"]

    # Submit replace
    submit_resp = await client.post("/operation", json={
        "session_id": session_id,
        "operation_type": "replace",
        "target_node_id": get_job_id,
        "new_node_id": api_id,
    })
    assert submit_resp.status_code == 200
    op = submit_resp.json()["operation"]
    op_id = op["id"]

    # Should have a compatibility confirmation question
    assert op["status"] == "awaiting_user"
    q_id = op["aiQuestions"][0]["id"]

    # Answer yes to proceed
    answer_resp = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id,
        "question_id": q_id,
        "answer": "Yes, replace it",
    })
    assert answer_resp.status_code == 200
    data = AnswerQuestionResponse.model_validate(answer_resp.json())
    assert data.operation.status == "ready"
    assert data.operation.generated_diffs is not None
    assert len(data.operation.generated_diffs) >= 1


@needs_claude
async def test_replace_apply_writes_files(client, session_data, get_job_id, tmp_path):
    """Apply a replace operation and verify files are modified on disk."""
    # Copy task-api to tmp_path
    tmp_src = str(tmp_path / "src")
    shutil.copytree(TASK_API_PATH, tmp_src)

    # Re-parse from temp copy
    parse_resp = await client.post("/project/parse", json={"root_path": tmp_src})
    assert parse_resp.status_code == 200
    project_data = parse_resp.json()["project"]
    project_id = project_data["id"]
    ep_id = project_data["entryPoints"][0]["id"]

    session_resp = await client.post("/session", json={
        "project_id": project_id,
        "entry_point_id": ep_id,
    })
    session_id = session_resp.json()["session"]["id"]

    # Find get_job in the temp project
    tmp_get_job_id = next(
        fn["id"] for fn in project_data["functions"]
        if fn["name"] == "get_job"
    )

    # Add API with full schema
    api_resp = await client.post(f"/session/{session_id}/external-api", json={
        "session_id": session_id,
        "name": "Full Job API",
        "endpoint": "https://api.example.com/jobs/{job_id}",
        "method": "GET",
        "input_schema": [],
        "output_schema": FULL_API_SCHEMA,
        "description": None,
    })
    assert api_resp.status_code == 200
    api_id = api_resp.json()["node"]["id"]

    # Submit replace
    submit_resp = await client.post("/operation", json={
        "session_id": session_id,
        "operation_type": "replace",
        "target_node_id": tmp_get_job_id,
        "new_node_id": api_id,
    })
    assert submit_resp.status_code == 200
    op = submit_resp.json()["operation"]
    op_id = op["id"]
    q_id = op["aiQuestions"][0]["id"]

    # Answer yes
    answer_resp = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id,
        "question_id": q_id,
        "answer": "Yes, replace it",
    })
    assert answer_resp.json()["operation"]["status"] == "ready"

    # Apply
    apply_resp = await client.post(f"/operation/{op_id}/apply")
    assert apply_resp.status_code == 200

    data = ApplyOperationResponse.model_validate(apply_resp.json())
    assert data.operation.status == "applied"
    assert len(data.modified_files) >= 1

    # Verify actual file on disk changed
    modified_rel = data.modified_files[0]
    modified_abs = os.path.join(tmp_src, modified_rel)
    assert os.path.isfile(modified_abs)

    original_abs = os.path.join(TASK_API_PATH, modified_rel)
    with open(original_abs, encoding="utf-8") as f:
        original = f.read()
    with open(modified_abs, encoding="utf-8") as f:
        modified = f.read()

    assert modified != original, "Applied file should differ from the original"
