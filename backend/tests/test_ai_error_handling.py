from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.routers import operation as operation_router
from src.services.ai.mimo import MimoAPIError


TASK_API_PATH = Path(__file__).resolve().parents[2] / "example" / "task-api" / "src"


@pytest.mark.asyncio
async def test_answer_question_returns_failed_operation_for_mimo_error(monkeypatch):
    async def raise_mimo_error(operation, project):
        raise MimoAPIError(
            "raw provider failure",
            user_message="MiMo Token Plan China authentication failed.",
            status_code=401,
        )

    monkeypatch.setattr(operation_router, "generate_diffs", raise_mimo_error)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        parse_resp = await client.post(
            "/project/parse",
            json={"root_path": str(TASK_API_PATH)},
        )
        assert parse_resp.status_code == 200
        project = parse_resp.json()["project"]

        session_resp = await client.post(
            "/session",
            json={
                "project_id": project["id"],
                "entry_point_id": project["entryPoints"][0]["id"],
            },
        )
        assert session_resp.status_code == 200

        target_id = next(
            fn["id"] for fn in project["functions"] if fn["name"] == "_upload_to_blob"
        )
        submit_resp = await client.post(
            "/operation",
            json={
                "session_id": session_resp.json()["session"]["id"],
                "operation_type": "delete",
                "target_node_id": target_id,
                "new_node_id": None,
            },
        )
        assert submit_resp.status_code == 200
        operation = submit_resp.json()["operation"]

        answer_resp = await client.post(
            f"/operation/{operation['id']}/answer",
            json={
                "operation_id": operation["id"],
                "question_id": operation["aiQuestions"][0]["id"],
                "answer": "Skip the calls (remove call lines entirely)",
            },
        )

    assert answer_resp.status_code == 200
    payload = answer_resp.json()["operation"]
    assert payload["status"] == "failed"
    assert payload["errorMessage"] == "MiMo Token Plan China authentication failed."
