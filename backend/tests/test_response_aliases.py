import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app
from src.models.domain import Operation
from src.services.session import store


def _save_ready_operation(operation_id: str) -> None:
    store.save_operation(
        Operation(
            id=operation_id,
            session_id="session-alias",
            project_id="project-alias",
            type="delete",
            target_node_id="fn-alias",
            new_node_id=None,
            status="ready",
            ai_questions=[],
            generated_diffs=[],
            error_message="alias check",
        )
    )


@pytest.mark.asyncio
async def test_get_operation_serializes_camel_case_fields():
    op_id = "op-alias-get"
    _save_ready_operation(op_id)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(f"/operation/{op_id}")

    assert response.status_code == 200
    payload = response.json()
    assert "generatedDiffs" in payload
    assert "errorMessage" in payload
    assert "generated_diffs" not in payload
    assert "error_message" not in payload


@pytest.mark.asyncio
async def test_apply_operation_serializes_nested_operation_camel_case_fields():
    op_id = "op-alias-apply"
    _save_ready_operation(op_id)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(f"/operation/{op_id}/apply")

    assert response.status_code == 200
    payload = response.json()
    assert "modifiedFiles" in payload
    assert "modified_files" not in payload
    assert "generatedDiffs" in payload["operation"]
    assert "errorMessage" in payload["operation"]
    assert "generated_diffs" not in payload["operation"]
    assert "error_message" not in payload["operation"]
