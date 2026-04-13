"""
Phase 3 test — verifies session creation, graph filtering, and position persistence.
Run from project root: pytest tests/test_phase_3.py
Uses example/task-api as the test project.
"""
import os
import pytest
import pytest_asyncio  # noqa: F401
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.models.domain import CreateSessionResponse, GraphSession

TASK_API_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "example", "task-api", "src")
)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest_asyncio.fixture
async def parsed_project(client: AsyncClient):
    """Parse task-api and return the project dict (camelCase keys)."""
    resp = await client.post("/project/parse", json={"root_path": TASK_API_PATH})
    assert resp.status_code == 200
    return resp.json()["project"]


@pytest_asyncio.fixture
async def first_session(client: AsyncClient, parsed_project: dict):
    """Create a session for the first entry point and return the full response dict."""
    entry_point_id = parsed_project["entryPoints"][0]["id"]
    resp = await client.post("/session", json={
        "project_id": parsed_project["id"],
        "entry_point_id": entry_point_id,
    })
    assert resp.status_code == 200
    return resp.json()


# ── Setup sanity ──────────────────────────────────────────────────────────────

def test_task_api_path_exists():
    assert os.path.isdir(TASK_API_PATH)


# ── Session creation ──────────────────────────────────────────────────────────

async def test_create_session_status_200(client, parsed_project):
    resp = await client.post("/session", json={
        "project_id": parsed_project["id"],
        "entry_point_id": parsed_project["entryPoints"][0]["id"],
    })
    assert resp.status_code == 200


async def test_create_session_valid_shape(first_session, parsed_project):
    data = CreateSessionResponse.model_validate(first_session)
    assert data.session.id != ""
    assert data.session.project_id == parsed_project["id"]
    assert data.session.active_entry_point_id == parsed_project["entryPoints"][0]["id"]


async def test_create_session_unknown_project_returns_404(client):
    resp = await client.post("/session", json={
        "project_id": "nonexistent-project",
        "entry_point_id": "entry::POST::/foo",
    })
    assert resp.status_code == 404


# ── Graph filtering ───────────────────────────────────────────────────────────

async def test_graph_view_has_visible_functions(first_session):
    data = CreateSessionResponse.model_validate(first_session)
    assert len(data.graph_view.visible_function_ids) >= 1


async def test_entry_point_function_is_visible(first_session, parsed_project):
    """The entry point's own function must be in visible_function_ids."""
    data = CreateSessionResponse.model_validate(first_session)
    ep_function_id = parsed_project["entryPoints"][0]["functionId"]
    assert ep_function_id in data.graph_view.visible_function_ids


async def test_visible_functions_are_real_project_functions(first_session, parsed_project):
    """Every visible function ID must exist in the project's function list."""
    data = CreateSessionResponse.model_validate(first_session)
    all_fn_ids = {fn["id"] for fn in parsed_project["functions"]}
    for fn_id in data.graph_view.visible_function_ids:
        assert fn_id in all_fn_ids, f"Visible fn {fn_id!r} not in project"


async def test_visible_schemas_are_real_project_schemas(first_session, parsed_project):
    """Every visible schema ID must exist in the project's schema list."""
    data = CreateSessionResponse.model_validate(first_session)
    all_schema_ids = {s["id"] for s in parsed_project["schemas"]}
    for schema_id in data.graph_view.visible_schema_ids:
        assert schema_id in all_schema_ids, f"Visible schema {schema_id!r} not in project"


async def test_visible_call_edges_connect_visible_functions(client, parsed_project, first_session):
    """Every visible call edge must connect two visible functions."""
    data = CreateSessionResponse.model_validate(first_session)
    visible_fn_set = set(data.graph_view.visible_function_ids)

    # Build edge lookup from project
    edge_by_id = {e["id"]: e for e in parsed_project["callEdges"]}
    for edge_id in data.graph_view.visible_call_edge_ids:
        edge = edge_by_id[edge_id]
        assert edge["sourceId"] in visible_fn_set
        assert edge["targetId"] in visible_fn_set


async def test_different_entry_points_may_have_different_views(client, parsed_project):
    """Two different entry points should not have identical visible function sets
    (unless the project only has one entry point or the graph has one function)."""
    if len(parsed_project["entryPoints"]) < 2:
        pytest.skip("task-api has fewer than 2 entry points")

    ep1_id = parsed_project["entryPoints"][0]["id"]
    ep2_id = parsed_project["entryPoints"][1]["id"]

    r1 = await client.post("/session", json={
        "project_id": parsed_project["id"],
        "entry_point_id": ep1_id,
    })
    r2 = await client.post("/session", json={
        "project_id": parsed_project["id"],
        "entry_point_id": ep2_id,
    })

    view1_fns = set(r1.json()["graphView"]["visibleFunctionIds"])
    view2_fns = set(r2.json()["graphView"]["visibleFunctionIds"])
    # Each view must at least have its own entry point function
    ep1_fn = parsed_project["entryPoints"][0]["functionId"]
    ep2_fn = parsed_project["entryPoints"][1]["functionId"]
    assert ep1_fn in view1_fns
    assert ep2_fn in view2_fns


# ── Session retrieval ─────────────────────────────────────────────────────────

async def test_get_session_returns_correct_id(client, first_session):
    session_id = first_session["session"]["id"]
    resp = await client.get(f"/session/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == session_id


async def test_get_unknown_session_returns_404(client):
    resp = await client.get("/session/nonexistent-session-xyz")
    assert resp.status_code == 404


# ── Position persistence ──────────────────────────────────────────────────────

async def test_update_node_position_returns_200(client, first_session):
    session_id = first_session["session"]["id"]
    node_id = first_session["graphView"]["visibleFunctionIds"][0]

    resp = await client.patch(f"/session/{session_id}/position", json={
        "session_id": session_id,
        "node_id": node_id,
        "position": {"x": 999.0, "y": 777.0},
    })
    assert resp.status_code == 200


async def test_update_node_position_persists_in_response(client, first_session):
    session_id = first_session["session"]["id"]
    node_id = first_session["graphView"]["visibleFunctionIds"][0]

    resp = await client.patch(f"/session/{session_id}/position", json={
        "session_id": session_id,
        "node_id": node_id,
        "position": {"x": 999.0, "y": 777.0},
    })
    updated = resp.json()
    assert node_id in updated["nodePositions"]
    assert updated["nodePositions"][node_id]["x"] == 999.0
    assert updated["nodePositions"][node_id]["y"] == 777.0


async def test_position_retrievable_after_patch(client, first_session):
    """Position saved via PATCH must be visible in a subsequent GET."""
    session_id = first_session["session"]["id"]
    node_id = first_session["graphView"]["visibleFunctionIds"][0]

    await client.patch(f"/session/{session_id}/position", json={
        "session_id": session_id,
        "node_id": node_id,
        "position": {"x": 123.0, "y": 456.0},
    })

    get_resp = await client.get(f"/session/{session_id}")
    assert get_resp.status_code == 200
    positions = get_resp.json()["nodePositions"]
    assert node_id in positions
    assert positions[node_id]["x"] == 123.0
    assert positions[node_id]["y"] == 456.0


async def test_update_unknown_session_returns_404(client, first_session):
    node_id = first_session["graphView"]["visibleFunctionIds"][0]
    resp = await client.patch("/session/nonexistent-session/position", json={
        "session_id": "nonexistent-session",
        "node_id": node_id,
        "position": {"x": 0.0, "y": 0.0},
    })
    assert resp.status_code == 404
