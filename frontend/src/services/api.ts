/**
 * All fetch calls to the CodeFlow backend live here.
 * No fetch calls are allowed in components or hooks.
 */
import type {
  ParseProjectResponse,
  CreateSessionResponse,
  GraphSession,
  SubmitOperationResponse,
  Operation,
  AnswerQuestionResponse,
  ApplyOperationResponse,
  AddExternalAPIResponse,
  OperationType,
  NodePosition,
  FieldInfo,
} from '../types'

const BASE_URL = ''

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`${method} ${path} → ${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}

// ── Project ──────────────────────────────────────────────────────────────────

export function parseProject(rootPath: string): Promise<ParseProjectResponse> {
  return request('POST', '/project/parse', { root_path: rootPath })
}

export function readProjectFile(
  projectId: string,
  filePath: string,
): Promise<{ content: string; file_path: string }> {
  return request('GET', `/project/${projectId}/file?file_path=${encodeURIComponent(filePath)}`)
}

export function writeProjectFile(
  projectId: string,
  filePath: string,
  content: string,
): Promise<{ saved: boolean; file_path: string }> {
  return request('POST', `/project/${projectId}/file`, { file_path: filePath, content })
}

// ── Session ───────────────────────────────────────────────────────────────────

export function createSession(
  projectId: string,
  entryPointId: string,
): Promise<CreateSessionResponse> {
  return request('POST', '/session', {
    project_id: projectId,
    entry_point_id: entryPointId,
  })
}

export function getSession(sessionId: string): Promise<GraphSession> {
  return request('GET', `/session/${sessionId}`)
}

export function updateNodePosition(
  sessionId: string,
  nodeId: string,
  position: NodePosition,
): Promise<GraphSession> {
  return request('PATCH', `/session/${sessionId}/position`, {
    session_id: sessionId,
    node_id: nodeId,
    position,
  })
}

export function chatWithAI(
  sessionId: string,
  message: string,
  contextNodeId: string | null,
  history: Array<{ role: 'user' | 'assistant'; content: string }>,
): Promise<{ response: string }> {
  return request('POST', `/session/${sessionId}/chat`, {
    message,
    context_node_id: contextNodeId,
    history,
  })
}

export function addExternalAPI(
  sessionId: string,
  params: {
    name: string
    endpoint: string
    method: string
    inputSchema: FieldInfo[]
    outputSchema: FieldInfo[]
    description: string | null
  },
): Promise<AddExternalAPIResponse> {
  return request('POST', `/session/${sessionId}/external-api`, {
    session_id: sessionId,
    name: params.name,
    endpoint: params.endpoint,
    method: params.method,
    input_schema: params.inputSchema,
    output_schema: params.outputSchema,
    description: params.description,
  })
}

// ── Operations ────────────────────────────────────────────────────────────────

export function submitOperation(
  sessionId: string,
  operationType: OperationType,
  targetNodeId: string,
  newNodeId: string | null,
): Promise<SubmitOperationResponse> {
  return request('POST', '/operation', {
    session_id: sessionId,
    operation_type: operationType,
    target_node_id: targetNodeId,
    new_node_id: newNodeId,
  })
}

export function getOperation(operationId: string): Promise<Operation> {
  return request('GET', `/operation/${operationId}`)
}

export function answerQuestion(
  operationId: string,
  questionId: string,
  answer: string,
): Promise<AnswerQuestionResponse> {
  return request('POST', `/operation/${operationId}/answer`, {
    operation_id: operationId,
    question_id: questionId,
    answer,
  })
}

export function applyOperation(operationId: string): Promise<ApplyOperationResponse> {
  return request('POST', `/operation/${operationId}/apply`)
}

export function revertOperation(operationId: string): Promise<Operation> {
  return request('POST', `/operation/${operationId}/revert`)
}

export function rollbackOperation(operationId: string): Promise<ApplyOperationResponse> {
  return request('POST', `/operation/${operationId}/rollback`)
}
