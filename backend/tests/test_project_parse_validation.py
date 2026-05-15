import os

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest.mark.asyncio
async def test_parse_rejects_missing_project_path(tmp_path):
    missing = tmp_path / "missing-project"
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/project/parse",
            json={"root_path": str(missing)},
        )

    assert response.status_code == 400
    assert "does not exist or is not a directory" in response.json()["detail"]


@pytest.mark.asyncio
async def test_parse_rejects_file_path(tmp_path):
    file_path = tmp_path / "single.py"
    file_path.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/project/parse",
            json={"root_path": str(file_path)},
        )

    assert response.status_code == 400
    assert "does not exist or is not a directory" in response.json()["detail"]


@pytest.mark.asyncio
async def test_parse_accepts_existing_directory(tmp_path):
    (tmp_path / "main.py").write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n\n"
        "@app.get('/health')\n"
        "def health():\n"
        "    return {'ok': True}\n",
        encoding="utf-8",
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/project/parse",
            json={"root_path": str(tmp_path)},
        )

    assert response.status_code == 200
    assert response.json()["project"]["rootPath"] == os.path.abspath(str(tmp_path))
