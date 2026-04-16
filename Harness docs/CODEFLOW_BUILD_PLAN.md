# CodeFlow — Build Plan

> Core philosophy: **Harness Engineering First.**
> Before any feature is implemented, all types, interfaces, and file skeletons exist.
> Every phase builds against already-defined contracts. AI coding never has to guess types.

---

## Harness Engineering Principle

```
Phase 0 (Harness)
  → All Pydantic models written
  → All TypeScript interfaces written
  → All API endpoints stubbed (return mock data)
  → React Flow renders hardcoded mock graph

Phase 1+
  → Replace stubs with real implementations, one phase at a time
  → Types never change (if they must, update PRD first)
```

The harness is the single source of truth. Implementation fills in the harness; it does not redesign it.

---

## Phase Overview

| Phase | Name | Goal |
|-------|------|------|
| 0 | Harness | All types defined, all files created, mock data renders |
| 1 | Parser | Real Python code → ParsedProject |
| 2 | Graph Render | ParsedProject → interactive React Flow graph |
| 3 | Session & Navigation | Entry point selection, node filtering, positions |
| 4 | Delete Operation | First write operation end-to-end |
| 5 | Replace Operation | Core value: swap nodes, AI schema mapping |
| 6 | Add Operations | Insert, branch, external API |

---

## Phase 0 — Harness

**Goal:** The entire project skeleton exists. No feature logic yet. Mock data flows end-to-end.

**Definition of Done:**
- Run `uvicorn` → all endpoints respond (with mock data, no errors)
- Run `npm run dev` → React app loads, mock graph renders in React Flow with 3 node types and 2 edge types
- No `any` types in TypeScript. No untyped fields in Python.
- `tests/test_phase_0.py` passes: hits every stub endpoint, asserts response shape matches Pydantic models

### Backend tasks

**0-B-1: Project scaffold**
```
backend/
  src/
    main.py
    application.py
    settings.py
    models/domain.py        ← paste ALL models from PRD Section 9.1
    routers/__init__.py
    routers/project.py
    routers/session.py
    routers/operation.py
    services/parser/__init__.py
    services/parser/file_scanner.py       ← empty stub
    services/parser/function_extractor.py ← empty stub
    services/parser/schema_extractor.py   ← empty stub
    services/parser/call_resolver.py      ← empty stub
    services/parser/entry_point_detector.py ← empty stub
    services/graph/__init__.py
    services/graph/graph_filter.py        ← empty stub
    services/ai/__init__.py
    services/ai/analyzer.py               ← empty stub
    services/ai/generator.py              ← empty stub
    services/ai/prompts.py                ← empty stub
    services/session/__init__.py
    services/session/store.py             ← in-memory dict store
  requirements.txt
```

**0-B-2: Stub all endpoints** (return hardcoded mock responses matching the exact types in `domain.py`)

`POST /project/parse` → returns `ParseProjectResponse` with 2 mock FunctionNodes, 1 SchemaNode, 1 EntryPoint

`POST /session` → returns `CreateSessionResponse` with mock session + mock graph view

`POST /operation` → returns `SubmitOperationResponse` with operation status `"analyzing"`

`GET /operation/{id}` → returns mock operation with 1 AIQuestion, status `"awaiting_user"`

`POST /operation/{id}/answer` → returns operation with status `"ready"`, 1 mock FileDiff

`POST /operation/{id}/apply` → returns operation with status `"applied"`

**0-B-3: In-memory store** (`services/session/store.py`)
```python
# Simple dict-based store. No database.
projects: dict[str, ParsedProject] = {}
sessions: dict[str, GraphSession] = {}
operations: dict[str, Operation] = {}
```

### Frontend tasks

**0-F-1: Project scaffold**
```
frontend/
  src/
    types/index.ts              ← paste ALL interfaces from PRD Section 9.2
    services/api.ts             ← typed fetch functions (all endpoints, stubs)
    store/index.ts              ← Zustand store with typed state
    components/nodes/FunctionNode.tsx
    components/nodes/SchemaNode.tsx
    components/nodes/ExternalAPINode.tsx
    components/edges/CallEdge.tsx
    components/edges/DataFlowEdge.tsx
    components/panels/LeftSidebar.tsx
    components/panels/RightPanel.tsx
    components/panels/AIConversation.tsx
    components/panels/DiffPreview.tsx
    hooks/useProject.ts
    hooks/useSession.ts
    hooks/useOperation.ts
    App.tsx
    main.tsx
```

**0-F-2: Zustand store shape**
```typescript
interface AppStore {
  project: ParsedProject | null
  session: GraphSession | null
  graphView: GraphView | null
  activeOperation: Operation | null
  setProject: (p: ParsedProject) => void
  setSession: (s: GraphSession) => void
  setGraphView: (g: GraphView) => void
  setActiveOperation: (o: Operation | null) => void
}
```

**0-F-3: React Flow mock render**
- Hardcode 3 nodes (1 FunctionNode, 1 SchemaNode, 1 ExternalAPINode) in mock data
- Hardcode 2 edges (1 CallEdge, 1 DataFlowEdge)
- All three node components render their type with correct colors (blue / purple / green)
- Both edge components render with correct colors (blue / orange)
- Canvas is pannable and zoomable

**0-F-4: `api.ts` typed stubs**
```typescript
// Every function is typed. No fetch calls anywhere else.
export async function parseProject(req: ParseProjectRequest): Promise<ParseProjectResponse>
export async function createSession(req: CreateSessionRequest): Promise<CreateSessionResponse>
export async function submitOperation(req: SubmitOperationRequest): Promise<SubmitOperationResponse>
export async function getOperation(operationId: string): Promise<Operation>
export async function answerQuestion(req: AnswerQuestionRequest): Promise<AnswerQuestionResponse>
export async function applyOperation(operationId: string): Promise<ApplyOperationResponse>
export async function revertOperation(operationId: string): Promise<Operation>
export async function addExternalAPI(req: AddExternalAPIRequest): Promise<AddExternalAPIResponse>
```

---

## Phase 1 — Parser

**Goal:** Real Python project on disk → `ParsedProject` returned from `POST /project/parse`.

**Definition of Done:**
- Point CodeFlow at the `example/task-api/src` folder
- Response contains all functions, all Pydantic schemas, all call edges, correct entry points
- `_process_pdf` node has `calls` list containing the `magic_pdf` function call IDs
- `POST /request/create` is detected as a `fastapi_route` entry point
- `tests/test_phase_1.py` passes: calls `POST /project/parse` with `example/task-api`, asserts node counts, asserts `_process_pdf` calls list, asserts entry point detection

### Tasks

**1-1: `file_scanner.py`**
- Walks `root_path` recursively
- Returns list of `.py` file paths (excludes `__pycache__`, `.venv`, `tests/`)

**1-2: `function_extractor.py`**
- Takes a single `.py` file path
- Uses `ast.parse()` to walk the AST
- Returns `list[FunctionNode]` (no `calls` or `called_by` yet — those are empty lists at this stage)
- Captures: `name`, `file_path`, `class_name`, `is_async`, `params`, `return_type`, `source_code`, `start_line`, `end_line`
- Handles: top-level functions, methods inside classes

**1-3: `schema_extractor.py`**
- Takes a single `.py` file path
- Detects: classes that inherit from `BaseModel` (Pydantic), `TypedDict`, or use `@dataclass`
- Returns `list[SchemaNode]` with all fields extracted

**1-4: `call_resolver.py`**
- Takes the full `list[FunctionNode]` from all files
- For each function, walks its AST for `ast.Call` nodes
- Resolves callee to a `FunctionNode.id` (cross-file, using import statements)
- Populates `calls` on each node, then derives `called_by` (inverse index)
- Returns updated `list[FunctionNode]` + `list[CallEdge]`

**1-5: `entry_point_detector.py`**
- Scans for FastAPI route decorators (`@router.get`, `@router.post`, `@app.get`, etc.)
- Scans for `if __name__ == "__main__"` blocks
- Returns `list[EntryPoint]`

**1-6: Wire up `POST /project/parse`**
- Calls each service in order: scan → extract functions → extract schemas → resolve calls → detect entry points
- Builds and stores `ParsedProject` in `session/store.py`
- Returns `ParseProjectResponse`

---

## Phase 2 — Graph Render

**Goal:** Frontend fetches real `ParsedProject` and renders it in React Flow.

**Definition of Done:**
- Load `example/task-api` → see all real function nodes on canvas
- Node shows: function name, file path, async badge (if async), param count
- SchemaNode shows: schema name, field count
- CallEdge is blue; DataFlowEdge is orange
- Canvas is pannable and zoomable
- `frontend/src/tests/phase_2.test.ts` passes: renders mock graph data, asserts correct node count, asserts FunctionNode shows async badge, asserts edge colors

### Tasks

**2-1: `FunctionNode.tsx` component**
```
┌─────────────────────────────┐
│ 🔵  create_job              │
│     src/services/job.py     │
│     JobManager              │
│     async  •  2 params      │
│     → JobResponse           │
└─────────────────────────────┘
```
- Input/output ports for React Flow handles
- Props: `FunctionNode` (from `types/index.ts`)

**2-2: `SchemaNode.tsx` component**
```
┌─────────────────────────────┐
│ 🟣  JobResponse             │
│     src/schemas/job.py      │
│     pydantic  •  6 fields   │
└─────────────────────────────┘
```

**2-3: `ExternalAPINode.tsx` component**
```
┌─────────────────────────────┐
│ 🟢  MinerU API              │
│     POST /v1/parse          │
│     3 inputs  •  4 outputs  │
└─────────────────────────────┘
```

**2-4: `CallEdge.tsx`** — blue animated arrow

**2-5: `DataFlowEdge.tsx`** — orange arrow, red when `isCompatible === false`

**2-6: Graph layout** — use React Flow's built-in auto-layout or `elkjs` to arrange nodes left-to-right by call depth

**2-7: `useProject` hook** — calls `parseProject()`, stores result in Zustand

---

## Phase 3 — Session & Navigation

**Goal:** Entry point selector + graph filtering + node positions saved.

**Definition of Done:**
- Left sidebar shows entry point list from real parsed data
- Click `POST /request/create` → canvas shows only nodes in that call chain
- Drag a node → position is saved in session
- Refresh / re-select entry point → positions are remembered
- `tests/test_phase_3.py` passes: creates session for `POST /request/create`, asserts `GraphView` only contains nodes reachable from that entry point, asserts position update persists

### Tasks

**3-1: `graph_filter.py`** (backend)
- Takes `ParsedProject` + `entry_point_id`
- BFS/DFS from entry point's function, following `calls` edges
- Returns `GraphView` (only IDs reachable from entry point)

**3-2: `LeftSidebar.tsx`** — entry point list, click to activate

**3-3: `useSession` hook** — creates session, stores `GraphSession` + `GraphView` in Zustand

**3-4: Canvas filter** — React Flow only renders nodes whose IDs are in `graphView.visibleFunctionIds` etc.

**3-5: Node drag handler** — on drag end, call `PATCH /session/{id}/position`

---

## Phase 4 — Delete Operation

**Goal:** Delete a node → AI detects break points → user answers questions → diff shown → apply writes code.

**Definition of Done:**
- Select a FunctionNode → delete key → confirmation modal
- Right panel shows AI question: "What should callers of `_upload_to_blob` do after deletion?"
- User picks an option
- Diff panel shows real code changes
- Click Apply → file on disk is modified correctly
- `tests/test_phase_4.py` passes: submits delete operation on `_upload_to_blob`, asserts operation reaches `"awaiting_user"` with ≥1 question, answers the question, asserts operation reaches `"ready"` with non-empty diffs, applies and asserts the target file is modified on disk

### Tasks

**4-1: Delete UI** — select node, delete key, confirmation modal

**4-2: `POST /operation`** — creates Operation with type `"delete"`, status `"analyzing"`

**4-3: `analyzer.py` — delete case**
- Receives `Operation` + `ParsedProject`
- Finds all nodes in `called_by` of target
- For each caller, generates an `AIQuestion`
- Updates operation to status `"awaiting_user"`

**4-4: `POST /operation/{id}/answer`**
- Stores answer on `AIQuestion`
- If all questions answered → triggers code generation → status `"generating"`
- When done → status `"ready"`

**4-5: `generator.py` — delete case**
- Uses Claude API with function source code + question answers as context
- Generates `list[FileDiff]` for each affected caller file

**4-6: `DiffPreview.tsx`** — renders FileDiff list with syntax highlighting, old/new side-by-side

**4-7: `POST /operation/{id}/apply`**
- Reads each `FileDiff`
- Writes `new_content` to `file_path` on disk
- Returns `ApplyOperationResponse`

**4-8: `prompts.py` — delete prompt**
```python
DELETE_ANALYSIS_PROMPT = """
You are analyzing a Python codebase refactoring operation.

The user wants to delete this function:
{function_source_code}

The following functions call it:
{caller_functions_source_code}

For each caller, generate ONE clarifying question asking the user how to handle
the removed call. Provide 3 concrete options.
"""
```

---

## Phase 5 — Replace Operation

**Goal:** Drag ExternalAPINode onto FunctionNode → AI maps schemas → diff shown → apply.

**Definition of Done:**
- Import MinerU API node via "Import API" form
- Drag MinerU node onto a magic_pdf function node
- AI shows: "Field `bbox` exists in old output but is missing from MinerU's output. It is used in 3 places. How should we handle it?"
- User picks option
- Diff shows real code changes to `_process_pdf`
- Apply writes correct file
- `tests/test_phase_5.py` passes: adds an ExternalAPINode with a schema that has 1 missing field, submits replace operation, asserts incompatible DataFlowEdge is detected, answers schema question, asserts diff modifies `_process_pdf`, applies and asserts file content changed

### Tasks

**5-1: "Import API" form** — modal with fields matching `AddExternalAPIRequest`

**5-2: Drag-to-replace gesture** — React Flow `onNodeDrop` or overlay detection; shows "Replace?" confirmation

**5-3: `analyzer.py` — replace case**
- Compare `target_node.return_type` schema fields with `new_node.output_schema` fields
- Detect: missing fields, renamed fields, type mismatches
- Generate one `AIQuestion` per incompatible field

**5-4: `generator.py` — replace case**
- Rewrites call sites of old function to use new API endpoint
- Generates adapter function if needed
- Returns `list[FileDiff]`

**5-5: DataFlowEdge incompatibility highlight**
- After replace analysis, mark edges with `isCompatible: false` where schema gaps exist
- These edges render red on canvas

**5-6: `prompts.py` — replace prompt**
```python
REPLACE_ANALYSIS_PROMPT = """
You are analyzing a Python codebase refactoring operation.

Old function being replaced:
{old_function_source_code}
Return type schema: {old_return_schema}

New external API replacing it:
Name: {new_api_name}
Endpoint: {new_api_endpoint}
Output schema: {new_api_output_schema}

Incompatible fields detected:
{incompatible_fields}

For each incompatible field, generate ONE clarifying question with concrete options.
"""
```

---

## Phase 6 — Add Operations

**Goal:** Insert node between two existing nodes; add a new branch from a node.

**Definition of Done:**
- Click an edge → "Insert node" option → new node appears between the two
- AI generates correct function stub with right param/return types
- Drag from a node to empty space → new branch node created
- Diff shows new function added to the correct file
- `tests/test_phase_6.py` passes: submits `add_insert` operation on a known edge, asserts diff contains a new function with correct param type matching source node's return type; submits `add_branch` operation, asserts diff adds new function to correct file

### Tasks

**6-1: Edge click → insert UI** — React Flow edge click handler, shows insert button on edge

**6-2: Branch drag UI** — custom connection line that creates node on drop to empty area

**6-3: `analyzer.py` — add_insert case**
- Infer new function's `param` type = source node's `return_type`
- Infer new function's `return_type` = target node's first param type
- Generate stub code question: "What should this function do?"

**6-4: `analyzer.py` — add_branch case**
- Source node's return type is known
- Ask user: "What should the new function receive and return?"

**6-5: `generator.py` — add cases**
- Generate new function stub in correct file (same file as source node)
- Return FileDiff adding the new function

---

## Cross-Phase Rules for AI Coding

These rules apply in every phase and must never be violated:

1. **Types first.** If a phase requires a new type, add it to `models/domain.py` and `types/index.ts` before writing any implementation.

2. **No business logic in routers.** Routers only: validate request → call service → return response.

3. **No direct file writes outside `operation.py` router's apply endpoint.** Only `POST /operation/{id}/apply` touches files on disk.

4. **All prompt strings are in `prompts.py`.** No f-string prompts inline in `analyzer.py` or `generator.py`.

5. **Poll, don't stream (MVP).** Operations are async but the frontend polls `GET /operation/{id}` every 1 second. No WebSockets in MVP.

6. **One question at a time.** `analyzer.py` must return questions as a list, but the frontend only shows the first unanswered question. Never render a form with multiple AI questions at once.

7. **Test with `example/task-api`.** Every phase's Definition of Done must be verified against the real `task-api` project, not synthetic test data.

8. **Each phase must ship a test script.** At the end of every phase, produce a test script at `tests/test_phase_N.py` (backend) and/or `frontend/src/tests/phase_N.test.ts` (frontend) that verifies the phase's Definition of Done. The script must:
   - Be runnable with a single command (`pytest tests/test_phase_N.py` or `npm test -- phase_N`)
   - Cover every item listed in the phase's Definition of Done
   - Use the real `example/task-api` project as test input, not hardcoded mock data
   - Pass completely before the next phase begins
   - Never be deleted or skipped in later phases (all prior test scripts must still pass)
