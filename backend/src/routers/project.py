import asyncio
import os
from fastapi import APIRouter, HTTPException, Query
from src.models.domain import (
    ParseProjectRequest,
    ParseProjectResponse,
    ParsedProject,
    FunctionNode,
    SchemaNode,
    ExternalAPINode,
    CallEdge,
    DataFlowEdge,
    EntryPoint,
    ParamInfo,
    FieldInfo,
)
from src.services.parser import parse_project as _parse_project
from src.services.session import store

router = APIRouter()


# ---------------------------------------------------------------------------
# Phase 0 mock data — kept for GET /project/{id} fallback during development
# ---------------------------------------------------------------------------

def _build_mock_project(root_path: str) -> ParsedProject:
    fn_router = FunctionNode(
        id="src/routers/request.py::create_job",
        name="create_job",
        file_path="src/routers/request.py",
        class_name=None,
        is_async=True,
        params=[ParamInfo(name="request", type="JobRequest", default=None, is_optional=False)],
        return_type="JobResponse",
        source_code=(
            "@router.post('/create')\n"
            "async def create_job(request: JobRequest):\n"
            "    return JobManager.create_job(request=request)"
        ),
        start_line=11,
        end_line=16,
        calls=["src/services/job.py::JobManager::create_job"],
        called_by=[],
        uses_schemas=["src/schemas/job.py::JobRequest"],
    )

    fn_service = FunctionNode(
        id="src/services/job.py::JobManager::create_job",
        name="create_job",
        file_path="src/services/job.py",
        class_name="JobManager",
        is_async=False,
        params=[ParamInfo(name="request", type="JobRequest", default=None, is_optional=False)],
        return_type="Tuple[JobResponse, Response]",
        source_code=(
            "@staticmethod\n"
            "def create_job(request: JobRequest):\n"
            "    job_status = MGDOC_JobStatus(...)\n"
            "    asyncio.get_running_loop().create_task(_run_job(...))\n"
            "    return JobResponse(...), Response(...)"
        ),
        start_line=28,
        end_line=98,
        calls=[],
        called_by=["src/routers/request.py::create_job"],
        uses_schemas=["src/schemas/job.py::JobResponse"],
    )

    schema_response = SchemaNode(
        id="src/schemas/job.py::JobResponse",
        name="JobResponse",
        file_path="src/schemas/job.py",
        schema_type="pydantic",
        fields=[
            FieldInfo(name="job_id", type="str", is_optional=False, default=None, description=None),
            FieldInfo(name="job_status", type="str", is_optional=False, default=None, description=None),
            FieldInfo(name="file_path", type="str", is_optional=False, default=None, description=None),
        ],
        source_code="class JobResponse(BaseModel):\n    job_id: str\n    job_status: str\n    file_path: str",
        used_by=["src/services/job.py::JobManager::create_job"],
    )

    external_api = ExternalAPINode(
        id="external::mineru_api",
        name="MinerU API",
        endpoint="https://api.mineru.com/v1/parse",
        method="POST",
        input_schema=[
            FieldInfo(name="file_url", type="str", is_optional=False, default=None, description="URL of the PDF to parse"),
        ],
        output_schema=[
            FieldInfo(name="markdown", type="str", is_optional=False, default=None, description="Parsed markdown content"),
            FieldInfo(name="images", type="list[str]", is_optional=True, default=None, description="Extracted image URLs"),
        ],
        description="MinerU PDF parsing API — replacement for magic_pdf",
    )

    call_edge = CallEdge(
        id="call::src/routers/request.py::create_job::src/services/job.py::JobManager::create_job",
        source_id="src/routers/request.py::create_job",
        target_id="src/services/job.py::JobManager::create_job",
        call_line=14,
        edge_type="call",
    )

    data_flow_edge = DataFlowEdge(
        id="data::src/services/job.py::JobManager::create_job::src/schemas/job.py::JobResponse",
        source_id="src/services/job.py::JobManager::create_job",
        target_id="src/schemas/job.py::JobResponse",
        data_type="JobResponse",
        is_compatible=True,
        edge_type="dataflow",
    )

    entry_point = EntryPoint(
        id="entry::POST::/request/create",
        label="POST /request/create",
        function_id="src/routers/request.py::create_job",
        entry_type="fastapi_route",
    )

    return ParsedProject(
        id="project-001",
        name="task-api",
        root_path=root_path,
        language="python",
        functions=[fn_router, fn_service],
        schemas=[schema_response],
        external_apis=[external_api],
        call_edges=[call_edge],
        data_flow_edges=[data_flow_edge],
        entry_points=[entry_point],
    )


@router.post("/parse", response_model=ParseProjectResponse)
async def parse_project(request: ParseProjectRequest) -> ParseProjectResponse:
    """Parse a local Python project into a graph (Phase 1: real parser)."""
    project = await asyncio.to_thread(_parse_project, request.root_path)
    store.save_project(project)
    return ParseProjectResponse(project=project)


@router.get("/{project_id}", response_model=ParsedProject)
async def get_project(project_id: str) -> ParsedProject:
    """Get a previously parsed project by ID."""
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found")
    return project


@router.get("/{project_id}/file")
async def read_project_file(
    project_id: str,
    file_path: str = Query(..., description="Relative file path within the project"),
) -> dict:
    """Read the full content of a file within the project."""
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found")
    abs_path = os.path.normpath(os.path.join(project.root_path, file_path))
    # Security: ensure path stays within root
    if not abs_path.startswith(os.path.normpath(project.root_path)):
        raise HTTPException(status_code=400, detail="Path traversal not allowed")
    if not os.path.isfile(abs_path):
        raise HTTPException(status_code=404, detail=f"File {file_path!r} not found")
    with open(abs_path, encoding="utf-8") as f:
        content = f.read()
    return {"content": content, "file_path": file_path}


@router.post("/{project_id}/file")
async def write_project_file(
    project_id: str,
    body: dict,
) -> dict:
    """Write (save) a file within the project from the IDE editor."""
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found")
    file_path = body.get("file_path", "")
    content = body.get("content", "")
    abs_path = os.path.normpath(os.path.join(project.root_path, file_path))
    if not abs_path.startswith(os.path.normpath(project.root_path)):
        raise HTTPException(status_code=400, detail="Path traversal not allowed")
    with open(abs_path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"saved": True, "file_path": file_path}


@router.get("/{project_id}/entry-points", response_model=list[EntryPoint])
async def get_entry_points(project_id: str) -> list[EntryPoint]:
    """List auto-detected entry points for a project."""
    project = store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id!r} not found")
    return project.entry_points
