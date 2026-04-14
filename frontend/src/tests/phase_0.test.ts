/**
 * Phase 0 frontend test — verifies all TypeScript types compile correctly
 * and mock data satisfies the type contracts.
 */
import { describe, it, expect } from 'vitest'
import type {
  FunctionNode,
  SchemaNode,
  ExternalAPINode,
  CallEdge,
  DataFlowEdge,
  EntryPoint,
  ParsedProject,
  GraphSession,
  Operation,
  OperationStatus,
} from '../types'

describe('Phase 0 — TypeScript type contracts', () => {
  it('FunctionNode satisfies its type', () => {
    const node: FunctionNode = {
      id: 'src/services/job.py::JobManager::create_job',
      name: 'create_job',
      filePath: 'src/services/job.py',
      className: 'JobManager',
      isAsync: false,
      params: [{ name: 'request', type: 'JobRequest', default: null, isOptional: false }],
      returnType: 'JobResponse',
      sourceCode: 'def create_job(): ...',
      startLine: 28,
      endLine: 98,
      calls: [],
      calledBy: [],
      usesSchemas: [],
    }
    expect(node.id).toBe('src/services/job.py::JobManager::create_job')
    expect(node.isAsync).toBe(false)
    expect(node.className).toBe('JobManager')
  })

  it('SchemaNode satisfies its type', () => {
    const schema: SchemaNode = {
      id: 'src/schemas/job.py::JobResponse',
      name: 'JobResponse',
      filePath: 'src/schemas/job.py',
      schemaType: 'pydantic',
      fields: [{ name: 'job_id', type: 'str', isOptional: false, default: null, description: null }],
      sourceCode: 'class JobResponse(BaseModel): ...',
      startLine: 1,
      endLine: 3,
      usedBy: [],
    }
    expect(schema.schemaType).toBe('pydantic')
    expect(schema.fields).toHaveLength(1)
  })

  it('ExternalAPINode satisfies its type', () => {
    const api: ExternalAPINode = {
      id: 'external::mineru_api',
      name: 'MinerU API',
      endpoint: 'https://api.mineru.com/v1/parse',
      method: 'POST',
      inputSchema: [],
      outputSchema: [],
      description: null,
    }
    expect(api.method).toBe('POST')
  })

  it('CallEdge satisfies its type', () => {
    const edge: CallEdge = {
      id: 'call::fn1::fn2',
      sourceId: 'fn1',
      targetId: 'fn2',
      callLine: 14,
      edgeType: 'call',
    }
    expect(edge.edgeType).toBe('call')
  })

  it('DataFlowEdge marks incompatible correctly', () => {
    const edge: DataFlowEdge = {
      id: 'data::fn1::schema1',
      sourceId: 'fn1',
      targetId: 'schema1',
      dataType: 'JobResponse',
      isCompatible: false,
      edgeType: 'dataflow',
    }
    expect(edge.isCompatible).toBe(false)
  })

  it('Operation status is one of the valid literals', () => {
    const validStatuses: OperationStatus[] = [
      'analyzing', 'awaiting_user', 'generating', 'ready', 'applied', 'reverted',
    ]
    const op: Operation = {
      id: 'op-001',
      sessionId: 'session-001',
      projectId: 'proj-001',
      type: 'delete',
      targetNodeId: 'fn-1',
      newNodeId: null,
      status: 'awaiting_user',
      aiQuestions: [{
        id: 'q-001',
        question: 'What to do?',
        options: ['Skip', 'Replace'],
        userAnswer: null,
      }],
      generatedDiffs: null,
      errorMessage: null,
    }
    expect(validStatuses).toContain(op.status)
    expect(op.aiQuestions[0].userAnswer).toBeNull()
  })

  it('ParsedProject contains all required arrays', () => {
    const project: ParsedProject = {
      id: 'project-001',
      name: 'task-api',
      rootPath: '/path/to/task-api',
      language: 'python',
      functions: [],
      schemas: [],
      externalApis: [],
      callEdges: [],
      dataFlowEdges: [],
      entryPoints: [],
      appInstances: [],
    }
    expect(project.language).toBe('python')
    expect(Array.isArray(project.functions)).toBe(true)
    expect(Array.isArray(project.entryPoints)).toBe(true)
  })

  it('GraphSession node_positions is a typed Record', () => {
    const session: GraphSession = {
      id: 'session-001',
      projectId: 'project-001',
      activeEntryPointId: 'entry::POST::/request/create',
      visibleNodeIds: ['fn-1'],
      nodePositions: { 'fn-1': { x: 100, y: 200 } },
      pendingOperationId: null,
    }
    expect(session.nodePositions['fn-1'].x).toBe(100)
  })

  it('EntryPoint entry_type is one of the valid literals', () => {
    const ep: EntryPoint = {
      id: 'entry::POST::/request/create',
      label: 'POST /request/create',
      functionId: 'src/routers/request.py::create_job',
      entryType: 'fastapi_route',
    }
    expect(ep.entryType).toBe('fastapi_route')
  })
})
