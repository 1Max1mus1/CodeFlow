from __future__ import annotations
from pydantic import BaseModel, ConfigDict, alias_generators
from typing import Literal


# ---------------------------------------------------------------------------
# Base model — all models inherit this.
# Serialises to camelCase JSON so the TypeScript frontend gets camelCase keys.
# Accepts both snake_case and camelCase on input (populate_by_name=True).
# ---------------------------------------------------------------------------

class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,
        populate_by_name=True,
    )


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class ParamInfo(CamelModel):
    name: str
    type: str | None
    default: str | None
    is_optional: bool


class FieldInfo(CamelModel):
    name: str
    type: str
    is_optional: bool
    default: str | None
    description: str | None


class NodePosition(CamelModel):
    x: float
    y: float


# ---------------------------------------------------------------------------
# Node models
# ---------------------------------------------------------------------------

class FunctionNode(CamelModel):
    id: str                  # "src/services/job.py::JobManager::create_job"
    name: str
    file_path: str
    class_name: str | None   # None for module-level functions
    is_async: bool
    params: list[ParamInfo]
    return_type: str | None
    source_code: str         # full function source — used by AI
    start_line: int
    end_line: int
    calls: list[str]         # FunctionNode IDs this function calls
    called_by: list[str]     # FunctionNode IDs that call this function
    uses_schemas: list[str]  # SchemaNode IDs used in this function


class SchemaNode(CamelModel):
    id: str                  # "src/schemas/job.py::JobResponse"
    name: str
    file_path: str
    schema_type: Literal["pydantic", "typeddict", "dataclass"]
    fields: list[FieldInfo]
    source_code: str
    start_line: int          # line number of the class definition (1-indexed)
    end_line: int
    used_by: list[str]       # FunctionNode IDs that use this schema


class ExternalAPINode(CamelModel):
    id: str                  # "external::mineru_api"
    name: str
    endpoint: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    input_schema: list[FieldInfo]
    output_schema: list[FieldInfo]
    description: str | None


# ---------------------------------------------------------------------------
# Edge models
# ---------------------------------------------------------------------------

class CallEdge(CamelModel):
    id: str                  # "call::{source_id}::{target_id}"
    source_id: str
    target_id: str
    call_line: int
    edge_type: Literal["call"]


class DataFlowEdge(CamelModel):
    id: str                  # "data::{source_id}::{target_id}"
    source_id: str
    target_id: str
    data_type: str | None
    is_compatible: bool      # False → edge renders red on canvas
    edge_type: Literal["dataflow"]


# ---------------------------------------------------------------------------
# Project & entry points
# ---------------------------------------------------------------------------

class EntryPoint(CamelModel):
    id: str                  # "entry::POST::/request/create"
    label: str               # "POST /request/create"
    function_id: str
    entry_type: Literal["fastapi_route", "main_function", "cli_command"]


class AppInstance(CamelModel):
    var_name: str            # "app" / "router"
    file_path: str           # "main.py"
    instance_type: Literal["fastapi", "apirouter"]


class ParsedProject(CamelModel):
    id: str
    name: str
    root_path: str
    language: Literal["python"]
    functions: list[FunctionNode]
    schemas: list[SchemaNode]
    external_apis: list[ExternalAPINode]
    call_edges: list[CallEdge]
    data_flow_edges: list[DataFlowEdge]
    entry_points: list[EntryPoint]
    app_instances: list[AppInstance] = []


class GraphView(CamelModel):
    entry_point_id: str
    visible_function_ids: list[str]
    visible_schema_ids: list[str]
    visible_external_api_ids: list[str]
    visible_call_edge_ids: list[str]
    visible_data_flow_edge_ids: list[str]


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

class GraphSession(CamelModel):
    id: str
    project_id: str
    active_entry_point_id: str
    visible_node_ids: list[str]
    node_positions: dict[str, NodePosition]
    pending_operation_id: str | None


# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

class AIQuestion(CamelModel):
    id: str
    question: str
    options: list[str] | None   # None = free-text; list = multiple choice
    user_answer: str | None


class DiffChange(CamelModel):
    line_number: int
    change_type: Literal["add", "remove", "modify"]
    old_line: str | None
    new_line: str | None


class FileDiff(CamelModel):
    file_path: str
    old_content: str
    new_content: str
    changes: list[DiffChange]


class Operation(CamelModel):
    id: str
    session_id: str
    project_id: str          # stored directly so diff generation doesn't need the session
    type: Literal["replace", "delete", "add_insert", "add_branch", "add_api", "generate_test"]
    target_node_id: str
    new_node_id: str | None
    status: Literal[
        "analyzing",
        "awaiting_user",
        "generating",
        "ready",
        "applied",
        "reverted",
    ]
    ai_questions: list[AIQuestion]
    generated_diffs: list[FileDiff] | None
    error_message: str | None


# ---------------------------------------------------------------------------
# API request / response models
# ---------------------------------------------------------------------------

class ParseProjectRequest(CamelModel):
    root_path: str


class ParseProjectResponse(CamelModel):
    project: ParsedProject


class CreateSessionRequest(CamelModel):
    project_id: str
    entry_point_id: str


class CreateSessionResponse(CamelModel):
    session: GraphSession
    graph_view: GraphView


class UpdateNodePositionRequest(CamelModel):
    session_id: str
    node_id: str
    position: NodePosition


class SubmitOperationRequest(CamelModel):
    session_id: str
    operation_type: Literal["replace", "delete", "add_insert", "add_branch", "add_api", "generate_test"]
    target_node_id: str
    new_node_id: str | None


class SubmitOperationResponse(CamelModel):
    operation: Operation


class AnswerQuestionRequest(CamelModel):
    operation_id: str
    question_id: str
    answer: str


class AnswerQuestionResponse(CamelModel):
    operation: Operation


class ApplyOperationResponse(CamelModel):
    operation: Operation
    modified_files: list[str]


class AddExternalAPIRequest(CamelModel):
    session_id: str
    name: str
    endpoint: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    input_schema: list[FieldInfo]
    output_schema: list[FieldInfo]
    description: str | None


class AddExternalAPIResponse(CamelModel):
    node: ExternalAPINode
