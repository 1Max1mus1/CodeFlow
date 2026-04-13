import uuid
from fastapi import APIRouter, HTTPException
from src.models.domain import (
    CreateSessionRequest,
    CreateSessionResponse,
    GraphSession,
    UpdateNodePositionRequest,
    AddExternalAPIRequest,
    AddExternalAPIResponse,
    ExternalAPINode,
)
from src.services.session import store
from src.services.graph.graph_filter import filter_graph
from src.services.ai.chat import chat_with_project

router = APIRouter()


@router.post("", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
    """Create a new editing session for an entry point."""
    project = store.get_project(request.project_id)
    if project is None:
        raise HTTPException(
            status_code=404,
            detail=f"Project {request.project_id!r} not found. Parse it first.",
        )

    graph_view = filter_graph(project, request.entry_point_id)

    visible_node_ids = (
        graph_view.visible_function_ids
        + graph_view.visible_schema_ids
        + graph_view.visible_external_api_ids
    )

    session = GraphSession(
        id=f"session-{uuid.uuid4().hex[:8]}",
        project_id=request.project_id,
        active_entry_point_id=request.entry_point_id,
        visible_node_ids=visible_node_ids,
        node_positions={},
        pending_operation_id=None,
    )
    store.save_session(session)

    return CreateSessionResponse(session=session, graph_view=graph_view)


@router.get("/{session_id}", response_model=GraphSession)
async def get_session(session_id: str) -> GraphSession:
    """Get current session state."""
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return session


@router.patch("/{session_id}/position", response_model=GraphSession)
async def update_node_position(
    session_id: str, request: UpdateNodePositionRequest
) -> GraphSession:
    """Persist a node's canvas position in the session."""
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    updated_positions = dict(session.node_positions)
    updated_positions[request.node_id] = request.position
    updated_session = session.model_copy(update={"node_positions": updated_positions})
    store.save_session(updated_session)
    return updated_session


@router.post("/{session_id}/external-api", response_model=AddExternalAPIResponse)
async def add_external_api(
    session_id: str, request: AddExternalAPIRequest
) -> AddExternalAPIResponse:
    """Add an external API node: persists it to the project for use in replace operations."""
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    project = store.get_project(session.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {session.project_id!r} not found")

    node_id = f"external::{request.name.lower().replace(' ', '_')}"
    node = ExternalAPINode(
        id=node_id,
        name=request.name,
        endpoint=request.endpoint,
        method=request.method,
        input_schema=request.input_schema,
        output_schema=request.output_schema,
        description=request.description,
    )

    # Persist node into the project so the analyzer can find it by new_node_id
    updated_project = project.model_copy(
        update={"external_apis": project.external_apis + [node]}
    )
    store.update_project(updated_project)

    # Add the node ID to the session's visible nodes
    updated_session = session.model_copy(
        update={"visible_node_ids": session.visible_node_ids + [node_id]}
    )
    store.save_session(updated_session)

    return AddExternalAPIResponse(node=node)


@router.post("/{session_id}/chat")
async def chat(session_id: str, body: dict) -> dict:
    """Send a chat message to the AI assistant with project context."""
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    project = store.get_project(session.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {session.project_id!r} not found")

    message: str = body.get("message", "")
    context_node_id: str | None = body.get("context_node_id", None)
    history: list[dict] = body.get("history", [])

    response = await chat_with_project(project, message, context_node_id, history)
    return {"response": response}
