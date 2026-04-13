"""
Phase 4 test — verifies delete operation: AI question generation, diff creation, and file apply.
Run from project root: pytest tests/test_phase_4.py
Uses example/task-api as the test project.

Tests that call Claude require ANTHROPIC_API_KEY to be set.
Tests that only verify the analysis step (question generation) run without it.
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
)

TASK_API_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "example", "task-api", "src")
)

HAS_MOONSHOT_KEY = bool(os.environ.get("MOONSHOT_API_KEY"))
needs_claude = pytest.mark.skipif(
    not HAS_MOONSHOT_KEY,
    reason="MOONSHOT_API_KEY not set — skipping AI-dependent test",
)


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
def upload_to_blob_id(parsed_project: dict) -> str:
    """Return the real function ID for JobManager._upload_to_blob."""
    for fn in parsed_project["functions"]:
        if fn["name"] == "_upload_to_blob":
            return fn["id"]
    pytest.skip("_upload_to_blob not found in parsed project")


@pytest_asyncio.fixture
def function_with_callers(parsed_project: dict) -> dict:
    """Return a function that has at least one caller (calledBy not empty)."""
    for fn in parsed_project["functions"]:
        if len(fn.get("calledBy", [])) >= 1:
            return fn
    pytest.skip("No function with callers found in parsed project")


@pytest_asyncio.fixture
async def delete_op(client: AsyncClient, session_data: dict, upload_to_blob_id: str):
    """Submit a delete operation on _upload_to_blob and return the operation dict."""
    session_id = session_data["session"]["id"]
    resp = await client.post("/operation", json={
        "session_id": session_id,
        "operation_type": "delete",
        "target_node_id": upload_to_blob_id,
        "new_node_id": None,
    })
    assert resp.status_code == 200
    return resp.json()["operation"]


# ── Sanity ────────────────────────────────────────────────────────────────────

def test_task_api_path_exists():
    assert os.path.isdir(TASK_API_PATH)


def test_upload_to_blob_parseable(parsed_project: dict):
    names = [fn["name"] for fn in parsed_project["functions"]]
    assert "_upload_to_blob" in names, f"_upload_to_blob not found; got: {names}"


# ── Submit operation ──────────────────────────────────────────────────────────

async def test_submit_delete_returns_200(client, session_data, upload_to_blob_id):
    resp = await client.post("/operation", json={
        "session_id": session_data["session"]["id"],
        "operation_type": "delete",
        "target_node_id": upload_to_blob_id,
        "new_node_id": None,
    })
    assert resp.status_code == 200


async def test_submit_delete_status_awaiting_user(delete_op):
    data = SubmitOperationResponse.model_validate({"operation": delete_op})
    assert data.operation.status == "awaiting_user"


async def test_submit_delete_has_at_least_one_question(delete_op):
    data = SubmitOperationResponse.model_validate({"operation": delete_op})
    assert len(data.operation.ai_questions) >= 1


async def test_question_mentions_function_name(delete_op):
    question_text = delete_op["aiQuestions"][0]["question"]
    assert "_upload_to_blob" in question_text


async def test_question_has_options(delete_op):
    q = delete_op["aiQuestions"][0]
    assert q["options"] is not None
    assert len(q["options"]) >= 2


async def test_question_user_answer_is_null(delete_op):
    assert delete_op["aiQuestions"][0]["userAnswer"] is None


async def test_get_operation_after_submit(client, delete_op):
    op_id = delete_op["id"]
    resp = await client.get(f"/operation/{op_id}")
    assert resp.status_code == 200
    data = Operation.model_validate(resp.json())
    assert data.id == op_id
    assert data.status == "awaiting_user"


async def test_get_unknown_operation_returns_404(client):
    resp = await client.get("/operation/nonexistent-op-xyz")
    assert resp.status_code == 404


async def test_submit_unknown_session_returns_404(client, parsed_project):
    resp = await client.post("/operation", json={
        "session_id": "nonexistent-session",
        "operation_type": "delete",
        "target_node_id": parsed_project["functions"][0]["id"],
        "new_node_id": None,
    })
    assert resp.status_code == 404


# ── Answer question (no Claude) ───────────────────────────────────────────────

async def test_answer_question_stores_answer(client, delete_op):
    op_id = delete_op["id"]
    q_id = delete_op["aiQuestions"][0]["id"]

    resp = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id,
        "question_id": q_id,
        "answer": "I will handle this manually",  # produces no diffs; no Claude needed
    })
    assert resp.status_code == 200

    data = AnswerQuestionResponse.model_validate(resp.json())
    # Answer is stored
    assert data.operation.ai_questions[0].user_answer == "I will handle this manually"


async def test_answer_manually_reaches_ready(client, delete_op):
    """'I will handle this manually' skips Claude and goes directly to ready."""
    op_id = delete_op["id"]
    q_id = delete_op["aiQuestions"][0]["id"]

    resp = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id,
        "question_id": q_id,
        "answer": "I will handle this manually",
    })
    data = AnswerQuestionResponse.model_validate(resp.json())
    assert data.operation.status == "ready"
    assert data.operation.generated_diffs is not None  # may be empty list


# ── Revert (no Claude) ────────────────────────────────────────────────────────

async def test_revert_sets_reverted_status(client, delete_op):
    op_id = delete_op["id"]
    resp = await client.post(f"/operation/{op_id}/revert")
    assert resp.status_code == 200
    data = Operation.model_validate(resp.json())
    assert data.status == "reverted"


# ── Claude-dependent: real diff generation ────────────────────────────────────

@needs_claude
async def test_answer_with_skip_reaches_ready_with_diffs(client, session_data,
                                                          upload_to_blob_id, parsed_project):
    """End-to-end: submit delete → answer 'skip calls' → status ready with diffs."""
    session_id = session_data["session"]["id"]
    submit_resp = await client.post("/operation", json={
        "session_id": session_id,
        "operation_type": "delete",
        "target_node_id": upload_to_blob_id,
        "new_node_id": None,
    })
    op = submit_resp.json()["operation"]
    op_id = op["id"]
    q_id = op["aiQuestions"][0]["id"]

    answer_resp = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id,
        "question_id": q_id,
        "answer": "Skip the calls (remove call lines entirely)",
    })
    assert answer_resp.status_code == 200

    data = AnswerQuestionResponse.model_validate(answer_resp.json())
    assert data.operation.status == "ready"
    assert data.operation.generated_diffs is not None
    assert len(data.operation.generated_diffs) >= 1


@needs_claude
async def test_apply_writes_file_to_disk(client, session_data, upload_to_blob_id,
                                         parsed_project, tmp_path):
    """Apply writes modified files to disk. Uses a temp copy of task-api to avoid corruption."""
    # Copy task-api to tmp_path
    src_dir = TASK_API_PATH
    tmp_src = str(tmp_path / "src")
    shutil.copytree(src_dir, tmp_src)

    # Re-parse from the temp copy
    parse_resp = await client.post("/project/parse", json={"root_path": tmp_src})
    assert parse_resp.status_code == 200
    project_id = parse_resp.json()["project"]["id"]
    ep_id = parse_resp.json()["project"]["entryPoints"][0]["id"]

    session_resp = await client.post("/session", json={
        "project_id": project_id,
        "entry_point_id": ep_id,
    })
    session_id = session_resp.json()["session"]["id"]

    # Find _upload_to_blob in the temp project
    tmp_fn_id = next(
        fn["id"] for fn in parse_resp.json()["project"]["functions"]
        if fn["name"] == "_upload_to_blob"
    )

    # Submit delete
    submit_resp = await client.post("/operation", json={
        "session_id": session_id,
        "operation_type": "delete",
        "target_node_id": tmp_fn_id,
        "new_node_id": None,
    })
    op = submit_resp.json()["operation"]
    op_id = op["id"]
    q_id = op["aiQuestions"][0]["id"]

    # Answer
    answer_resp = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id,
        "question_id": q_id,
        "answer": "Skip the calls (remove call lines entirely)",
    })
    assert answer_resp.json()["operation"]["status"] == "ready"

    # Apply
    apply_resp = await client.post(f"/operation/{op_id}/apply")
    assert apply_resp.status_code == 200

    data = ApplyOperationResponse.model_validate(apply_resp.json())
    assert data.operation.status == "applied"
    assert len(data.modified_files) >= 1

    # Verify actual file on disk was changed
    modified_rel = data.modified_files[0]
    modified_abs = os.path.join(tmp_src, modified_rel)
    assert os.path.isfile(modified_abs)

    original_abs = os.path.join(TASK_API_PATH, modified_rel)
    with open(original_abs, encoding="utf-8") as f:
        original = f.read()
    with open(modified_abs, encoding="utf-8") as f:
        modified = f.read()

    assert modified != original, "Applied file should differ from the original"
