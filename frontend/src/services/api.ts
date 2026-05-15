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

export async function chatWithAIStream(
  sessionId: string,
  message: string,
  contextNodeId: string | null,
  history: Array<{ role: 'user' | 'assistant'; content: string }>,
  onToken: (token: string) => void,
): Promise<void> {
  const res = await fetch(`${BASE_URL}/session/${sessionId}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      context_node_id: contextNodeId,
      history,
    }),
  })

  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`POST /session/${sessionId}/chat/stream -> ${res.status}: ${detail}`)
  }
  if (!res.body) {
    throw new Error('Streaming response body is empty')
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const events = buffer.split('\n\n')
    buffer = events.pop() ?? ''
    for (const eventText of events) {
      handleSSEEvent(eventText, onToken)
    }
  }

  if (buffer.trim()) {
    handleSSEEvent(buffer, onToken)
  }
}

function handleSSEEvent(raw: string, onToken: (token: string) => void) {
  const eventLine = raw.split('\n').find((line) => line.startsWith('event:'))
  const dataLine = raw.split('\n').find((line) => line.startsWith('data:'))
  if (!eventLine || !dataLine) return

  const event = eventLine.slice('event:'.length).trim()
  const data = JSON.parse(dataLine.slice('data:'.length).trim()) as Record<string, unknown>
  if (event === 'token') {
    onToken(String(data.text ?? ''))
  } else if (event === 'error') {
    throw new Error(String(data.message ?? 'AI stream failed'))
  }
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
