// ---------------------------------------------------------------------------
// CodeFlow — TypeScript types
// Mirrors backend/src/models/domain.py exactly (camelCase throughout).
// No `any`. No untyped fields.
// ---------------------------------------------------------------------------

// ── Sub-types ───────────────────────────────────────────────────────────────

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

export interface NodePosition {
  x: number
  y: number
}

// ── Node types ───────────────────────────────────────────────────────────────

export interface FunctionNode {
  id: string           // "src/services/job.py::JobManager::create_job"
  name: string
  filePath: string
  className: string | null
  isAsync: boolean
  params: ParamInfo[]
  returnType: string | null
  sourceCode: string
  startLine: number
  endLine: number
  calls: string[]       // FunctionNode IDs
  calledBy: string[]    // FunctionNode IDs
  usesSchemas: string[] // SchemaNode IDs
}

export interface SchemaNode {
  id: string            // "src/schemas/job.py::JobResponse"
  name: string
  filePath: string
  schemaType: 'pydantic' | 'typeddict' | 'dataclass'
  fields: FieldInfo[]
  sourceCode: string
  startLine: number
  endLine: number
  usedBy: string[]      // FunctionNode IDs
}

export interface ExternalAPINode {
  id: string            // "external::mineru_api"
  name: string
  endpoint: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  inputSchema: FieldInfo[]
  outputSchema: FieldInfo[]
  description: string | null
}

export type AnyNode = FunctionNode | SchemaNode | ExternalAPINode

// ── Edge types ───────────────────────────────────────────────────────────────

export interface CallEdge {
  id: string            // "call::{source_id}::{target_id}"
  sourceId: string
  targetId: string
  callLine: number
  edgeType: 'call'
}

export interface DataFlowEdge {
  id: string            // "data::{source_id}::{target_id}"
  sourceId: string
  targetId: string
  dataType: string | null
  isCompatible: boolean // false → renders red
  edgeType: 'dataflow'
}

export type AnyEdge = CallEdge | DataFlowEdge

// ── Project ──────────────────────────────────────────────────────────────────

export interface EntryPoint {
  id: string            // "entry::POST::/request/create"
  label: string         // "POST /request/create"
  functionId: string
  entryType: 'fastapi_route' | 'main_function' | 'cli_command'
}

export interface AppInstance {
  varName: string
  filePath: string
  instanceType: 'fastapi' | 'apirouter'
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
  appInstances: AppInstance[]
}

export interface GraphView {
  entryPointId: string
  visibleFunctionIds: string[]
  visibleSchemaIds: string[]
  visibleExternalApiIds: string[]
  visibleCallEdgeIds: string[]
  visibleDataFlowEdgeIds: string[]
}

// ── Session ──────────────────────────────────────────────────────────────────

export interface GraphSession {
  id: string
  projectId: string
  activeEntryPointId: string
  visibleNodeIds: string[]
  nodePositions: Record<string, NodePosition>
  pendingOperationId: string | null
}

// ── Operations ───────────────────────────────────────────────────────────────

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

export type OperationType = 'replace' | 'delete' | 'add_insert' | 'add_branch' | 'add_api' | 'generate_test'

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
  projectId: string
  type: OperationType
  targetNodeId: string
  newNodeId: string | null
  status: OperationStatus
  aiQuestions: AIQuestion[]
  generatedDiffs: FileDiff[] | null
  errorMessage: string | null
}

// ── API request / response types ─────────────────────────────────────────────

export interface ParseProjectRequest {
  rootPath: string
}

export interface ParseProjectResponse {
  project: ParsedProject
}

export interface CreateSessionRequest {
  projectId: string
  entryPointId: string
}

export interface CreateSessionResponse {
  session: GraphSession
  graphView: GraphView
}

export interface UpdateNodePositionRequest {
  sessionId: string
  nodeId: string
  position: NodePosition
}

export interface SubmitOperationRequest {
  sessionId: string
  operationType: OperationType
  targetNodeId: string
  newNodeId: string | null
}

export interface SubmitOperationResponse {
  operation: Operation
}

export interface AnswerQuestionRequest {
  operationId: string
  questionId: string
  answer: string
}

export interface AnswerQuestionResponse {
  operation: Operation
}

export interface ApplyOperationResponse {
  operation: Operation
  modifiedFiles: string[]
}

export interface AddExternalAPIRequest {
  sessionId: string
  name: string
  endpoint: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  inputSchema: FieldInfo[]
  outputSchema: FieldInfo[]
  description: string | null
}

export interface AddExternalAPIResponse {
  node: ExternalAPINode
}
