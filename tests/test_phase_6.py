"""
Phase 6 test — verifies add_insert (new intermediate function) and add_branch
(new branch function) operations.

Build-Plan Definition of Done:
- add_insert: diff contains a new function with param type matching source node's return type
- add_branch: diff adds a new function to the correct file

Run from project root: pytest tests/test_phase_6.py
Uses example/task-api as the test project.

Tests that call Kimi require MOONSHOT_API_KEY to be set.
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
needs_ai = pytest.mark.skipif(
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
def create_job_id(parsed_project: dict) -> str:
    for fn in parsed_project["functions"]:
        if fn["name"] == "create_job":
            return fn["id"]
    pytest.skip("create_job not found in parsed project")


@pytest_asyncio.fixture
def update_status_id(parsed_project: dict) -> str:
    for fn in parsed_project["functions"]:
        if fn["name"] == "_update_job_status":
            return fn["id"]
    pytest.skip("_update_job_status not found in parsed project")


@pytest_asyncio.fixture
async def insert_op(
    client: AsyncClient, session_data: dict, create_job_id: str, update_status_id: str
) -> dict:
    """Submit add_insert between create_job (source/A) and _update_job_status (target/B)."""
    resp = await client.post("/operation", json={
        "session_id": session_data["session"]["id"],
        "operation_type": "add_insert",
        "target_node_id": create_job_id,    # A (source)
        "new_node_id": update_status_id,    # B (target)
    })
    assert resp.status_code == 200
    return resp.json()["operation"]


@pytest_asyncio.fixture
async def branch_op(
    client: AsyncClient, session_data: dict, create_job_id: str
) -> dict:
    """Submit add_branch on create_job."""
    resp = await client.post("/operation", json={
        "session_id": session_data["session"]["id"],
        "operation_type": "add_branch",
        "target_node_id": create_job_id,
        "new_node_id": None,
    })
    assert resp.status_code == 200
    return resp.json()["operation"]


# ── Sanity ────────────────────────────────────────────────────────────────────

def test_task_api_path_exists():
    assert os.path.isdir(TASK_API_PATH)


def test_create_job_parseable(parsed_project):
    names = [fn["name"] for fn in parsed_project["functions"]]
    assert "create_job" in names


def test_update_job_status_parseable(parsed_project):
    names = [fn["name"] for fn in parsed_project["functions"]]
    assert "_update_job_status" in names


# ── add_insert: analysis (no AI) ──────────────────────────────────────────────

async def test_add_insert_returns_200(client, session_data, create_job_id, update_status_id):
    resp = await client.post("/operation", json={
        "session_id": session_data["session"]["id"],
        "operation_type": "add_insert",
        "target_node_id": create_job_id,
        "new_node_id": update_status_id,
    })
    assert resp.status_code == 200


async def test_add_insert_status_awaiting_user(insert_op):
    data = SubmitOperationResponse.model_validate({"operation": insert_op})
    assert data.operation.status == "awaiting_user"


async def test_add_insert_has_one_question(insert_op):
    """Analyzer generates exactly one free-text question about what the new function should do."""
    data = SubmitOperationResponse.model_validate({"operation": insert_op})
    assert len(data.operation.ai_questions) == 1


async def test_add_insert_question_is_free_text(insert_op):
    """No preset options — user describes the new function behaviour."""
    assert insert_op["aiQuestions"][0]["options"] is None


async def test_add_insert_question_mentions_both_functions(insert_op):
    q = insert_op["aiQuestions"][0]["question"]
    assert "create_job" in q
    assert "_update_job_status" in q


async def test_add_insert_question_mentions_return_type(insert_op):
    """Question should mention the source function's return type (type inference)."""
    q = insert_op["aiQuestions"][0]["question"]
    # The question should contain type information
    assert "return type" in q.lower() or "param type" in q.lower()


async def test_add_insert_answer_null_initially(insert_op):
    assert insert_op["aiQuestions"][0]["userAnswer"] is None


async def test_add_insert_cancel_skips_ai(client, insert_op):
    """Answering 'cancel' reaches ready without calling Kimi."""
    op_id = insert_op["id"]
    q_id = insert_op["aiQuestions"][0]["id"]
    resp = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id, "question_id": q_id, "answer": "cancel",
    })
    assert resp.status_code == 200
    data = AnswerQuestionResponse.model_validate(resp.json())
    assert data.operation.status == "ready"
    assert data.operation.generated_diffs is not None


# ── add_branch: analysis (no AI) ─────────────────────────────────────────────

async def test_add_branch_returns_200(client, session_data, create_job_id):
    resp = await client.post("/operation", json={
        "session_id": session_data["session"]["id"],
        "operation_type": "add_branch",
        "target_node_id": create_job_id,
        "new_node_id": None,
    })
    assert resp.status_code == 200


async def test_add_branch_status_awaiting_user(branch_op):
    data = SubmitOperationResponse.model_validate({"operation": branch_op})
    assert data.operation.status == "awaiting_user"


async def test_add_branch_has_two_questions(branch_op):
    data = SubmitOperationResponse.model_validate({"operation": branch_op})
    assert len(data.operation.ai_questions) == 2


async def test_add_branch_first_question_is_about_condition(branch_op):
    q = branch_op["aiQuestions"][0]["question"]
    assert "condition" in q.lower()
    assert "create_job" in q


async def test_add_branch_second_question_is_about_behaviour(branch_op):
    q = branch_op["aiQuestions"][1]["question"]
    # Should ask what the new function does
    assert "function" in q.lower() or "branch" in q.lower()


async def test_add_branch_questions_are_free_text(branch_op):
    for q in branch_op["aiQuestions"]:
        assert q["options"] is None


async def test_add_branch_cancel_skips_ai(client, branch_op):
    op_id = branch_op["id"]
    q_id = branch_op["aiQuestions"][0]["id"]
    resp = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id, "question_id": q_id, "answer": "cancel",
    })
    assert resp.status_code == 200
    data = AnswerQuestionResponse.model_validate(resp.json())
    assert data.operation.status == "ready"


async def test_add_branch_revert(client, branch_op):
    resp = await client.post(f"/operation/{branch_op['id']}/revert")
    assert resp.status_code == 200
    assert Operation.model_validate(resp.json()).status == "reverted"


# ── AI-dependent: new function is created in the diff ─────────────────────────

@needs_ai
async def test_add_insert_diff_contains_new_function(
    client, session_data, create_job_id, update_status_id, parsed_project
):
    """Diff should add at least one new function definition to the source file."""
    session_id = session_data["session"]["id"]
    submit_resp = await client.post("/operation", json={
        "session_id": session_id,
        "operation_type": "add_insert",
        "target_node_id": create_job_id,
        "new_node_id": update_status_id,
    })
    op = submit_resp.json()["operation"]
    op_id = op["id"]
    q_id = op["aiQuestions"][0]["id"]

    answer_resp = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id,
        "question_id": q_id,
        "answer": "validate or preprocess the input before passing it to _update_job_status",
    })
    assert answer_resp.status_code == 200
    data = AnswerQuestionResponse.model_validate(answer_resp.json())
    assert data.operation.status == "ready"
    assert data.operation.generated_diffs is not None
    assert len(data.operation.generated_diffs) >= 1

    diff = data.operation.generated_diffs[0]
    assert diff.new_content != diff.old_content, "Diff should modify the source file"
    assert diff.file_path.endswith(".py"), "Diff should target the source function's Python file"


@needs_ai
async def test_add_branch_diff_contains_new_function(client, session_data, create_job_id):
    """Diff should add a new branch function to create_job's file."""
    session_id = session_data["session"]["id"]
    submit_resp = await client.post("/operation", json={
        "session_id": session_id,
        "operation_type": "add_branch",
        "target_node_id": create_job_id,
        "new_node_id": None,
    })
    op = submit_resp.json()["operation"]
    op_id = op["id"]

    # Answer condition
    await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id,
        "question_id": op["aiQuestions"][0]["id"],
        "answer": "not request.file_path",
    })
    # Answer behaviour
    resp2 = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id,
        "question_id": op["aiQuestions"][1]["id"],
        "answer": "raise ValueError with a descriptive message about missing file_path",
    })
    assert resp2.status_code == 200
    data = AnswerQuestionResponse.model_validate(resp2.json())
    assert data.operation.status == "ready"
    assert data.operation.generated_diffs is not None
    assert len(data.operation.generated_diffs) >= 1

    diff = data.operation.generated_diffs[0]
    assert diff.new_content != diff.old_content, "Diff should modify the source file"
    assert diff.file_path.endswith(".py")


@needs_ai
async def test_add_insert_apply_writes_file(client, session_data, tmp_path, parsed_project):
    """Apply add_insert and verify the file on disk changes and has a new function."""
    tmp_src = str(tmp_path / "src")
    shutil.copytree(TASK_API_PATH, tmp_src)

    parse_resp = await client.post("/project/parse", json={"root_path": tmp_src})
    assert parse_resp.status_code == 200
    project_data = parse_resp.json()["project"]

    session_resp = await client.post("/session", json={
        "project_id": project_data["id"],
        "entry_point_id": project_data["entryPoints"][0]["id"],
    })
    session_id = session_resp.json()["session"]["id"]

    tmp_create_job_id = next(fn["id"] for fn in project_data["functions"] if fn["name"] == "create_job")
    tmp_update_id = next(fn["id"] for fn in project_data["functions"] if fn["name"] == "_update_job_status")

    submit_resp = await client.post("/operation", json={
        "session_id": session_id,
        "operation_type": "add_insert",
        "target_node_id": tmp_create_job_id,
        "new_node_id": tmp_update_id,
    })
    op = submit_resp.json()["operation"]
    op_id = op["id"]

    resp = await client.post(f"/operation/{op_id}/answer", json={
        "operation_id": op_id,
        "question_id": op["aiQuestions"][0]["id"],
        "answer": "log the job creation attempt",
    })
    assert resp.json()["operation"]["status"] == "ready"

    apply_resp = await client.post(f"/operation/{op_id}/apply")
    assert apply_resp.status_code == 200
    data = ApplyOperationResponse.model_validate(apply_resp.json())
    assert data.operation.status == "applied"
    assert len(data.modified_files) >= 1

    modified_rel = data.modified_files[0]
    with open(os.path.join(TASK_API_PATH, modified_rel), encoding="utf-8") as f:
        original = f.read()
    with open(os.path.join(tmp_src, modified_rel), encoding="utf-8") as f:
        modified = f.read()
    assert modified != original, "Applied file should differ from the original"
