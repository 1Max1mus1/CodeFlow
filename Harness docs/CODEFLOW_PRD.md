# CodeFlow — Product Requirements Document v1.0

> This PRD is written for AI-assisted coding. Every type, contract, and interface is
> explicitly defined. No `dict`, no `Any`. All models are flat and unambiguous.
> The backend (Python/FastAPI) and frontend (TypeScript/React) use mirrored naming.

---

## 1. Product Summary

CodeFlow parses an existing Python codebase into a Dify-style interactive directed graph.
Each function becomes a node. Call relationships and data flow become edges.
The user can perform structural operations — replace, delete, add — directly on the graph.
AI handles all cascading code changes (schema mapping, call site updates, adapter generation).

**One-line pitch:** "Understand and refactor unfamiliar Python codebases visually, with AI doing the hard part."

---

## 2. Problem Statement

When a developer inherits an unfamiliar codebase and must replace or refactor a dependency:

- They cannot see which functions are affected without reading every file
- Schema/type mismatches appear as runtime bugs, not visible errors
- Cascading changes across call chains are invisible until something breaks

**Concrete scenario (the design anchor):**
A developer must replace `magic_pdf` with a MinerU API server in a FastAPI service they
have never seen before. They spend hours tracing the call chain manually, then introduce
schema bugs they cannot locate. CodeFlow eliminates both problems.

---

## 3. UI Layout

```
┌─────────────────┬──────────────────────────────────────┬──────────────────┐
│   Left Sidebar  │            Main Canvas               │   Right Panel    │
│                 │                                      │                  │
│  📁 File Tree   │   [FunctionNode] ──► [FunctionNode] │  AI Conversation │
│                 │         │                            │                  │
│  ⚡ Entry Points│   [SchemaNode]    [ExternalAPINode]  │  Diff Preview    │
│                 │                                      │                  │
│  POST /create   │   Directed graph (React Flow)        │                  │
│  GET  /status   │   Pan, zoom, drag nodes              │                  │
└─────────────────┴──────────────────────────────────────┴──────────────────┘
```

**Navigation flow:**
1. User opens project → system parses all Python files
2. Left sidebar shows auto-detected entry points
3. User clicks an entry point → main canvas renders that call chain only
4. All operations happen on the canvas; AI responses appear in right panel

---

## 4. Node Types

| Type | Visual Color | Represents |
|------|-------------|------------|
| `FunctionNode` | Blue | A Python function or method |
| `SchemaNode` | Purple | A Pydantic model, TypedDict, or dataclass |
| `ExternalAPINode` | Green | A manually imported external HTTP endpoint |

---

## 5. Edge Types

| Type | Visual Color | Represents | Turns Red When |
|------|-------------|------------|----------------|
| `CallEdge` | Blue | Function A calls Function B | — |
| `DataFlowEdge` | Orange | Data type flows from A to B | Schema incompatibility detected |

---

## 6. Operations

### 6.1 Replace
**Trigger:** User drags a new node on top of an existing node → confirmation prompt

**AI behavior:**
1. Compare `output_schema` of old node with `input_schema` of new node
2. Ask user how to handle each incompatible field (one question at a time)
3. Generate adapter code + updated call sites
4. Show diff panel → user applies

### 6.2 Delete
**Trigger:** User selects a node → presses Delete key → confirmation prompt

**AI behavior:**
1. Find all nodes in `called_by` list of deleted node
2. For each caller, ask user: skip the call / inline the logic / replace with null
3. Generate updated caller code
4. Show diff panel → user applies

### 6.3 Add — Insert Between Nodes
**Trigger:** User clicks an edge → "Insert node here" option appears

**AI behavior:**
1. New node is created between A and B (edge A→B becomes A→new→B)
2. AI generates function stub: infers input type from A's output, output type from B's input
3. Show diff panel → user applies

### 6.4 Add — New Branch
**Trigger:** User drags from a node's output port to empty canvas space

**AI behavior:**
1. New unconnected node is created
2. AI asks user: what should this function do?
3. AI generates function stub with correct input type (from source node's output)
4. Show diff panel → user applies

### 6.5 Add — External API Node
**Trigger:** User clicks "Import API" button → fills in endpoint details

**Behavior:**
1. Node appears on canvas, unconnected
2. User drags it to connect or onto an existing node (triggers Replace flow)

---

## 7. AI Workflow (Human-in-the-Loop)

Every operation follows this state machine:

```
"analyzing"      → AI reads affected nodes and their source code
"awaiting_user"  → AI asks one clarifying question, waits for answer
                   (repeats for each question)
"generating"     → AI generates code changes
"ready"          → Diff panel shown to user
"applied"        → User confirmed, code written to files
"reverted"       → User cancelled, no changes made
```

**Rules:**
- AI asks questions one at a time, never a form with multiple fields
- AI never writes code without user seeing the diff first
- Every operation can be reverted after applying

---

## 8. Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Frontend framework | React 18 + TypeScript | Best AI coding support |
| Graph library | React Flow (@xyflow/react) | Purpose-built for node graphs; used by Dify |
| Styling | Tailwind CSS + shadcn/ui | AI coding friendly; consistent components |
| State management | Zustand | Simple, TypeScript-native |
| Backend framework | Python 3.12 + FastAPI | Native Python AST parsing |
| Code parsing | Python `ast` + `astroid` | Built-in, cross-file import resolution |
| AI | Anthropic Claude API (claude-sonnet-4-6) | — |
| Storage | In-memory per session | No DB needed for MVP |

---

## 9. Data Models

### 9.1 Python Backend (Pydantic)

```python
from __future__ import annotations
from pydantic import BaseModel
from typing import Literal


# ─── Sub-models ──────────────────────────────────────────────────────────────

class ParamInfo(BaseModel):
    name: str
    type: str | None
    default: str | None
    is_optional: bool


class FieldInfo(BaseModel):
    name: str
    type: str
    is_optional: bool
    default: str | None
    description: str | None


# ─── Node Models ─────────────────────────────────────────────────────────────

class FunctionNode(BaseModel):
    id: str                    # format: "src/services/job.py::ClassName::method_name"
    name: str                  # "create_job"
    file_path: str             # "src/services/job.py"
    class_name: str | None     # "JobManager" or None if top-level function
    is_async: bool
    params: list[ParamInfo]
    return_type: str | None    # "JobResponse" or None
    source_code: str           # full function source, used by AI
    start_line: int
    end_line: int
    calls: list[str]           # list of FunctionNode IDs this function calls
    called_by: list[str]       # list of FunctionNode IDs that call this function
    uses_schemas: list[str]    # list of SchemaNode IDs used in this function


class SchemaNode(BaseModel):
    id: str                    # format: "src/schemas/job.py::JobResponse"
    name: str                  # "JobResponse"
    file_path: str
    schema_type: Literal["pydantic", "typeddict", "dataclass"]
    fields: list[FieldInfo]
    source_code: str
    used_by: list[str]         # list of FunctionNode IDs that use this schema


class ExternalAPINode(BaseModel):
    id: str                    # user-defined, e.g. "external::mineru_api"
    name: str                  # "MinerU API"
    endpoint: str              # "https://api.mineru.com/v1/parse"
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    input_schema: list[FieldInfo]
    output_schema: list[FieldInfo]
    description: str | None


# ─── Edge Models ─────────────────────────────────────────────────────────────

class CallEdge(BaseModel):
    id: str                    # format: "call::{source_id}::{target_id}"
    source_id: str             # FunctionNode ID
    target_id: str             # FunctionNode ID
    call_line: int             # line number of the call in source file
    edge_type: Literal["call"]


class DataFlowEdge(BaseModel):
    id: str                    # format: "data::{source_id}::{target_id}"
    source_id: str             # FunctionNode or SchemaNode ID
    target_id: str             # FunctionNode or SchemaNode ID
    data_type: str | None      # type name being passed, e.g. "JobResponse"
    is_compatible: bool        # False = edge renders red
    edge_type: Literal["dataflow"]


# ─── Project & Entry Points ───────────────────────────────────────────────────

class EntryPoint(BaseModel):
    id: str                    # format: "entry::POST::/request/create"
    label: str                 # "POST /request/create"
    function_id: str           # FunctionNode ID of the handler
    entry_type: Literal["fastapi_route", "main_function", "cli_command"]


class ParsedProject(BaseModel):
    id: str
    name: str                  # project folder name
    root_path: str
    language: Literal["python"]
    functions: list[FunctionNode]
    schemas: list[SchemaNode]
    external_apis: list[ExternalAPINode]
    call_edges: list[CallEdge]
    data_flow_edges: list[DataFlowEdge]
    entry_points: list[EntryPoint]


# ─── Graph View (filtered by entry point) ────────────────────────────────────

class GraphView(BaseModel):
    entry_point_id: str
    visible_function_ids: list[str]
    visible_schema_ids: list[str]
    visible_external_api_ids: list[str]
    visible_call_edge_ids: list[str]
    visible_data_flow_edge_ids: list[str]


# ─── Session ─────────────────────────────────────────────────────────────────

class NodePosition(BaseModel):
    x: float
    y: float


class GraphSession(BaseModel):
    id: str
    project_id: str
    active_entry_point_id: str
    visible_node_ids: list[str]
    node_positions: dict[str, NodePosition]   # node_id → position
    pending_operation_id: str | None


# ─── Operations ──────────────────────────────────────────────────────────────

class AIQuestion(BaseModel):
    id: str
    question: str
    options: list[str] | None      # multiple choice; None = free text
    user_answer: str | None        # None until user answers


class DiffChange(BaseModel):
    line_number: int
    change_type: Literal["add", "remove", "modify"]
    old_line: str | None
    new_line: str | None


class FileDiff(BaseModel):
    file_path: str
    old_content: str
    new_content: str
    changes: list[DiffChange]


class Operation(BaseModel):
    id: str
    session_id: str
    type: Literal["replace", "delete", "add_insert", "add_branch", "add_api"]
    target_node_id: str            # node being operated on
    new_node_id: str | None        # for replace: the replacement node ID
    status: Literal[
        "analyzing",
        "awaiting_user",
        "generating",
        "ready",
        "applied",
        "reverted"
    ]
    ai_questions: list[AIQuestion]
    generated_diffs: list[FileDiff] | None
    error_message: str | None


# ─── API Request/Response Models ──────────────────────────────────────────────

class ParseProjectRequest(BaseModel):
    root_path: str             # absolute path to project folder


class ParseProjectResponse(BaseModel):
    project: ParsedProject


class CreateSessionRequest(BaseModel):
    project_id: str
    entry_point_id: str


class CreateSessionResponse(BaseModel):
    session: GraphSession
    graph_view: GraphView


class UpdateNodePositionRequest(BaseModel):
    session_id: str
    node_id: str
    position: NodePosition


class SubmitOperationRequest(BaseModel):
    session_id: str
    operation_type: Literal["replace", "delete", "add_insert", "add_branch", "add_api"]
    target_node_id: str
    new_node_id: str | None


class SubmitOperationResponse(BaseModel):
    operation: Operation


class AnswerQuestionRequest(BaseModel):
    operation_id: str
    question_id: str
    answer: str


class AnswerQuestionResponse(BaseModel):
    operation: Operation          # updated with next question or status change


class ApplyOperationResponse(BaseModel):
    operation: Operation
    modified_files: list[str]     # paths of files that were changed


class AddExternalAPIRequest(BaseModel):
    session_id: str
    name: str
    endpoint: str
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    input_schema: list[FieldInfo]
    output_schema: list[FieldInfo]
    description: str | None


class AddExternalAPIResponse(BaseModel):
    node: ExternalAPINode
```

---

### 9.2 TypeScript Frontend (mirrors Python models exactly)

```typescript
// ─── Sub-types ────────────────────────────────────────────────────────────────

export interface ParamInfo {
  name: string
  type: string | null
  default: string | null
  isOptional: boolean
}

export interface FieldInfo {
  name: string
  type: string
  isOptional: boolean
  default: string | null
  description: string | null
}

// ─── Node Types ───────────────────────────────────────────────────────────────

export interface FunctionNode {
  id: string
  name: string
  filePath: string
  className: string | null
  isAsync: boolean
  params: ParamInfo[]
  returnType: string | null
  sourceCode: string
  startLine: number
  endLine: number
  calls: string[]
  calledBy: string[]
  usesSchemas: string[]
}

export interface SchemaNode {
  id: string
  name: string
  filePath: string
  schemaType: 'pydantic' | 'typeddict' | 'dataclass'
  fields: FieldInfo[]
  sourceCode: string
  usedBy: string[]
}

export interface ExternalAPINode {
  id: string
  name: string
  endpoint: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  inputSchema: FieldInfo[]
  outputSchema: FieldInfo[]
  description: string | null
}

export type AnyNode = FunctionNode | SchemaNode | ExternalAPINode

// ─── Edge Types ───────────────────────────────────────────────────────────────

export interface CallEdge {
  id: string
  sourceId: string
  targetId: string
  callLine: number
  edgeType: 'call'
}

export interface DataFlowEdge {
  id: string
  sourceId: string
  targetId: string
  dataType: string | null
  isCompatible: boolean
  edgeType: 'dataflow'
}

export type AnyEdge = CallEdge | DataFlowEdge

// ─── Project ──────────────────────────────────────────────────────────────────

export interface EntryPoint {
  id: string
  label: string
  functionId: string
  entryType: 'fastapi_route' | 'main_function' | 'cli_command'
}

export interface ParsedProject {
  id: string
  name: string
  rootPath: string
  language: 'python'
  functions: FunctionNode[]
  schemas: SchemaNode[]
  externalApis: ExternalAPINode[]
  callEdges: CallEdge[]
  dataFlowEdges: DataFlowEdge[]
  entryPoints: EntryPoint[]
}

export interface GraphView {
  entryPointId: string
  visibleFunctionIds: string[]
  visibleSchemaIds: string[]
  visibleExternalApiIds: string[]
  visibleCallEdgeIds: string[]
  visibleDataFlowEdgeIds: string[]
}

// ─── Session ──────────────────────────────────────────────────────────────────

export interface NodePosition {
  x: number
  y: number
}

export interface GraphSession {
  id: string
  projectId: string
  activeEntryPointId: string
  visibleNodeIds: string[]
  nodePositions: Record<string, NodePosition>
  pendingOperationId: string | null
}

// ─── Operations ───────────────────────────────────────────────────────────────

export interface AIQuestion {
  id: string
  question: string
  options: string[] | null
  userAnswer: string | null
}

export interface DiffChange {
  lineNumber: number
  changeType: 'add' | 'remove' | 'modify'
  oldLine: string | null
  newLine: string | null
}

export interface FileDiff {
  filePath: string
  oldContent: string
  newContent: string
  changes: DiffChange[]
}

export type OperationType = 'replace' | 'delete' | 'add_insert' | 'add_branch' | 'add_api'

export type OperationStatus =
  | 'analyzing'
  | 'awaiting_user'
  | 'generating'
  | 'ready'
  | 'applied'
  | 'reverted'

export interface Operation {
  id: string
  sessionId: string
  type: OperationType
  targetNodeId: string
  newNodeId: string | null
  status: OperationStatus
  aiQuestions: AIQuestion[]
  generatedDiffs: FileDiff[] | null
  errorMessage: string | null
}
```

---

## 10. API Contract

All endpoints return JSON. All error responses use HTTP status codes with `{ "detail": string }`.

### Project

| Method | Path | Request | Response | Description |
|--------|------|---------|----------|-------------|
| `POST` | `/project/parse` | `ParseProjectRequest` | `ParseProjectResponse` | Parse a local Python project |
| `GET` | `/project/{project_id}` | — | `ParsedProject` | Get parsed project |
| `GET` | `/project/{project_id}/entry-points` | — | `list[EntryPoint]` | List entry points |

### Session

| Method | Path | Request | Response | Description |
|--------|------|---------|----------|-------------|
| `POST` | `/session` | `CreateSessionRequest` | `CreateSessionResponse` | Create session + get filtered graph |
| `GET` | `/session/{session_id}` | — | `GraphSession` | Get session state |
| `PATCH` | `/session/{session_id}/position` | `UpdateNodePositionRequest` | `GraphSession` | Update node position |
| `POST` | `/session/{session_id}/external-api` | `AddExternalAPIRequest` | `AddExternalAPIResponse` | Add external API node |

### Operations

| Method | Path | Request | Response | Description |
|--------|------|---------|----------|-------------|
| `POST` | `/operation` | `SubmitOperationRequest` | `SubmitOperationResponse` | Submit a graph operation |
| `GET` | `/operation/{operation_id}` | — | `Operation` | Poll operation status |
| `POST` | `/operation/{operation_id}/answer` | `AnswerQuestionRequest` | `AnswerQuestionResponse` | Answer AI question |
| `POST` | `/operation/{operation_id}/apply` | — | `ApplyOperationResponse` | Write diffs to files |
| `POST` | `/operation/{operation_id}/revert` | — | `Operation` | Cancel operation |

---

## 11. Project Directory Structure

```
codeflow/
├── frontend/
│   ├── src/
│   │   ├── types/
│   │   │   └── index.ts              # All TypeScript interfaces (Section 9.2)
│   │   ├── components/
│   │   │   ├── nodes/
│   │   │   │   ├── FunctionNode.tsx  # Blue node component
│   │   │   │   ├── SchemaNode.tsx    # Purple node component
│   │   │   │   └── ExternalAPINode.tsx  # Green node component
│   │   │   ├── edges/
│   │   │   │   ├── CallEdge.tsx      # Blue edge component
│   │   │   │   └── DataFlowEdge.tsx  # Orange/red edge component
│   │   │   ├── panels/
│   │   │   │   ├── LeftSidebar.tsx   # File tree + entry points
│   │   │   │   ├── RightPanel.tsx    # AI chat + diff preview
│   │   │   │   ├── AIConversation.tsx
│   │   │   │   └── DiffPreview.tsx
│   │   │   └── ui/                   # shadcn/ui components
│   │   ├── hooks/
│   │   │   ├── useProject.ts         # project load/parse
│   │   │   ├── useSession.ts         # session management
│   │   │   └── useOperation.ts       # operation + polling
│   │   ├── services/
│   │   │   └── api.ts                # all fetch calls to backend
│   │   ├── store/
│   │   │   └── index.ts              # Zustand store
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── tsconfig.json
│
├── backend/
│   ├── src/
│   │   ├── main.py                   # uvicorn entry
│   │   ├── application.py            # FastAPI app + router registration
│   │   ├── settings.py               # config (API keys, etc.)
│   │   ├── models/
│   │   │   └── domain.py             # All Pydantic models (Section 9.1)
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── project.py            # /project endpoints
│   │   │   ├── session.py            # /session endpoints
│   │   │   └── operation.py          # /operation endpoints
│   │   └── services/
│   │       ├── parser/
│   │       │   ├── __init__.py
│   │       │   ├── file_scanner.py   # walk project, find .py files
│   │       │   ├── function_extractor.py  # ast → FunctionNode list
│   │       │   ├── schema_extractor.py    # ast → SchemaNode list
│   │       │   ├── call_resolver.py       # build CallEdge list
│   │       │   └── entry_point_detector.py  # find FastAPI routes / main()
│   │       ├── graph/
│   │       │   ├── __init__.py
│   │       │   └── graph_filter.py   # entry_point → GraphView
│   │       ├── ai/
│   │       │   ├── __init__.py
│   │       │   ├── analyzer.py       # analyze operation → AIQuestion list
│   │       │   ├── generator.py      # answers → FileDiff list
│   │       │   └── prompts.py        # all prompt templates
│   │       └── session/
│   │           ├── __init__.py
│   │           └── store.py          # in-memory session + project storage
│   └── requirements.txt
│
└── docs/
    ├── CODEFLOW_PRD.md               # this file
    └── CODEFLOW_BUILD_PLAN.md        # phase plan
```

---

## 12. Out of Scope (MVP)

| Feature | Reason deferred |
|---------|----------------|
| Multi-language support | Python parser is the core; other languages require separate parsers |
| Add — AI Generate (Add D) | Requires AI code generation from scratch; deferred to v2 |
| Team collaboration | No shared state/DB needed for single-user MVP |
| Version control integration | Out of scope; user manages their own git |
| Database persistence | Sessions are ephemeral; in-memory is sufficient for MVP |
| Authentication | Single-user local tool for MVP |
| Undo/redo history | Revert covers the immediate case; full history deferred |

---

## 13. Constraints & Rules for AI Coding

1. **Never use `dict` or `Any` in models.** Every field must have an explicit type.
2. **One model, one purpose.** Never reuse a domain model as a request or response schema.
3. **ID format is fixed:** `"file_path::ClassName::function_name"` for functions, `"file_path::ClassName"` for schemas, `"external::name"` for external APIs.
4. **Python snake_case, TypeScript camelCase.** The mapping is always direct (e.g., `file_path` ↔ `filePath`).
5. **All AI prompts live in `backend/src/services/ai/prompts.py`.** No prompt strings elsewhere.
6. **All API fetch calls live in `frontend/src/services/api.ts`.** No fetch calls in components.
7. **React components receive typed props only.** No prop type is ever `any` or untyped object.

8. **Each phase ships a test script.** At the end of every phase, produce `tests/test_phase_N.py` (backend) and/or `frontend/src/tests/phase_N.test.ts` (frontend). The script must be runnable with a single command, cover every Definition of Done item for that phase, use `example/task-api` as real test input, and pass fully before the next phase starts. All prior phase test scripts must continue to pass.
