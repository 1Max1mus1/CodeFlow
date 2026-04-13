"""
In-memory store for Phase 0 MVP.
No database — everything lives in process memory for the duration of the session.
"""
from src.models.domain import ParsedProject, GraphSession, Operation

_projects: dict[str, ParsedProject] = {}
_sessions: dict[str, GraphSession] = {}
_operations: dict[str, Operation] = {}


def get_project(project_id: str) -> ParsedProject | None:
    return _projects.get(project_id)


def save_project(project: ParsedProject) -> None:
    _projects[project.id] = project


def update_project(project: ParsedProject) -> None:
    """Replace the stored project with an updated version (same ID)."""
    _projects[project.id] = project


def get_session(session_id: str) -> GraphSession | None:
    return _sessions.get(session_id)


def save_session(session: GraphSession) -> None:
    _sessions[session.id] = session


def get_operation(operation_id: str) -> Operation | None:
    return _operations.get(operation_id)


def save_operation(operation: Operation) -> None:
    _operations[operation.id] = operation
