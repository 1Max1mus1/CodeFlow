/**
 * Phase 2 frontend test — verifies the layout utility and projectToFlow converter,
 * then checks that node/edge data is correct for mock graph data.
 *
 * Run from frontend/: npx vitest run src/tests/phase_2.test.ts
 */
import { describe, it, expect } from 'vitest'
import { computeGraphLayout } from '../utils/graphLayout'
import { projectToFlow } from '../utils/projectToFlow'
import type { ParsedProject, FunctionNode, SchemaNode, CallEdge, DataFlowEdge } from '../types'

// ── Fixtures ──────────────────────────────────────────────────────────────────

const FN_ROUTER: FunctionNode = {
  id: 'src/routers/request.py::create_job',
  name: 'create_job',
  filePath: 'src/routers/request.py',
  className: null,
  isAsync: true,
  params: [{ name: 'request', type: 'JobRequest', default: null, isOptional: false }],
  returnType: 'JobResponse',
  sourceCode: 'async def create_job(): ...',
  startLine: 11,
  endLine: 16,
  calls: ['src/services/job.py::JobManager::create_job'],
  calledBy: [],
  usesSchemas: [],
}

const FN_SERVICE: FunctionNode = {
  id: 'src/services/job.py::JobManager::create_job',
  name: 'create_job',
  filePath: 'src/services/job.py',
  className: 'JobManager',
  isAsync: false,
  params: [],
  returnType: 'JobResponse',
  sourceCode: 'def create_job(): ...',
  startLine: 28,
  endLine: 98,
  calls: [],
  calledBy: ['src/routers/request.py::create_job'],
  usesSchemas: [],
}

const SCHEMA: SchemaNode = {
  id: 'src/schemas/job.py::JobResponse',
  name: 'JobResponse',
  filePath: 'src/schemas/job.py',
  schemaType: 'pydantic',
  fields: [
    { name: 'job_id', type: 'str', isOptional: false, default: null, description: null },
    { name: 'job_status', type: 'str', isOptional: false, default: null, description: null },
  ],
  sourceCode: 'class JobResponse(BaseModel): ...',
  startLine: 1,
  endLine: 5,
  usedBy: ['src/services/job.py::JobManager::create_job'],
}

const CALL_EDGE: CallEdge = {
  id: 'call::src/routers/request.py::create_job::src/services/job.py::JobManager::create_job',
  sourceId: FN_ROUTER.id,
  targetId: FN_SERVICE.id,
  callLine: 14,
  edgeType: 'call',
}

const DATA_EDGE: DataFlowEdge = {
  id: 'data::src/services/job.py::JobManager::create_job::src/schemas/job.py::JobResponse',
  sourceId: FN_SERVICE.id,
  targetId: SCHEMA.id,
  dataType: 'JobResponse',
  isCompatible: true,
  edgeType: 'dataflow',
}

const MOCK_PROJECT: ParsedProject = {
  id: 'project-test',
  name: 'task-api',
  rootPath: '/mock/task-api',
  language: 'python',
  functions: [FN_ROUTER, FN_SERVICE],
  schemas: [SCHEMA],
  externalApis: [],
  callEdges: [CALL_EDGE],
  dataFlowEdges: [DATA_EDGE],
  entryPoints: [
    {
      id: 'entry::POST::/request/create',
      label: 'POST /request/create',
      functionId: FN_ROUTER.id,
      entryType: 'fastapi_route',
    },
  ],
}

// ── computeGraphLayout ────────────────────────────────────────────────────────

describe('computeGraphLayout', () => {
  it('assigns different x positions to nodes at different BFS levels', () => {
    const positions = computeGraphLayout({
      functionIds: [FN_ROUTER.id, FN_SERVICE.id],
      callEdges: [{ sourceId: FN_ROUTER.id, targetId: FN_SERVICE.id }],
      schemaIds: [],
      externalApiIds: [],
      rootId: FN_ROUTER.id,
    })

    expect(positions[FN_ROUTER.id]).toBeDefined()
    expect(positions[FN_SERVICE.id]).toBeDefined()
    // Router is root (level 0, col 0); service is level 1 → greater x
    expect(positions[FN_ROUTER.id].x).toBeLessThan(positions[FN_SERVICE.id].x)
  })

  it('places schema nodes to the right of all function nodes', () => {
    const positions = computeGraphLayout({
      functionIds: [FN_ROUTER.id, FN_SERVICE.id],
      callEdges: [{ sourceId: FN_ROUTER.id, targetId: FN_SERVICE.id }],
      schemaIds: [SCHEMA.id],
      externalApiIds: [],
      rootId: FN_ROUTER.id,
    })

    const maxFnX = Math.max(positions[FN_ROUTER.id].x, positions[FN_SERVICE.id].x)
    expect(positions[SCHEMA.id].x).toBeGreaterThan(maxFnX)
  })

  it('handles empty graph without throwing', () => {
    const positions = computeGraphLayout({
      functionIds: [],
      callEdges: [],
      schemaIds: [],
      externalApiIds: [],
    })
    expect(Object.keys(positions)).toHaveLength(0)
  })

  it('places unreachable nodes (no root provided) at same column', () => {
    const positions = computeGraphLayout({
      functionIds: [FN_ROUTER.id, FN_SERVICE.id],
      callEdges: [],
      schemaIds: [],
      externalApiIds: [],
      // No rootId — all functions unreachable → same level 999 → same column
    })
    expect(positions[FN_ROUTER.id].x).toBe(positions[FN_SERVICE.id].x)
    // But their y positions should differ (two nodes in same column)
    expect(positions[FN_ROUTER.id].y).not.toBe(positions[FN_SERVICE.id].y)
  })

  it('places external API nodes to the right of schema nodes', () => {
    const positions = computeGraphLayout({
      functionIds: [FN_ROUTER.id],
      callEdges: [],
      schemaIds: [SCHEMA.id],
      externalApiIds: ['external::some_api'],
      rootId: FN_ROUTER.id,
    })
    expect(positions['external::some_api'].x).toBeGreaterThan(positions[SCHEMA.id].x)
  })
})

// ── projectToFlow ─────────────────────────────────────────────────────────────

describe('projectToFlow', () => {
  it('returns correct total node count', () => {
    const { nodes } = projectToFlow(MOCK_PROJECT)
    // 2 functions + 1 schema + 0 external APIs
    expect(nodes).toHaveLength(3)
  })

  it('returns correct total edge count', () => {
    const { edges } = projectToFlow(MOCK_PROJECT)
    // 1 call edge + 1 data flow edge
    expect(edges).toHaveLength(2)
  })

  it('function nodes have type "functionNode"', () => {
    const { nodes } = projectToFlow(MOCK_PROJECT)
    const fnNodes = nodes.filter((n) => n.type === 'functionNode')
    expect(fnNodes).toHaveLength(2)
  })

  it('schema nodes have type "schemaNode"', () => {
    const { nodes } = projectToFlow(MOCK_PROJECT)
    const schemaNodes = nodes.filter((n) => n.type === 'schemaNode')
    expect(schemaNodes).toHaveLength(1)
  })

  it('call edges have type "callEdge"', () => {
    const { edges } = projectToFlow(MOCK_PROJECT)
    const callEdges = edges.filter((e) => e.type === 'callEdge')
    expect(callEdges).toHaveLength(1)
  })

  it('data flow edges have type "dataFlowEdge"', () => {
    const { edges } = projectToFlow(MOCK_PROJECT)
    const dfEdges = edges.filter((e) => e.type === 'dataFlowEdge')
    expect(dfEdges).toHaveLength(1)
  })

  it('compatible data flow edge marker is orange (#f97316)', () => {
    const { edges } = projectToFlow(MOCK_PROJECT)
    const dfEdge = edges.find((e) => e.type === 'dataFlowEdge')!
    const marker = dfEdge.markerEnd as { color: string }
    expect(marker.color).toBe('#f97316')
  })

  it('incompatible data flow edge marker is red (#ef4444)', () => {
    const incompatibleProject: ParsedProject = {
      ...MOCK_PROJECT,
      dataFlowEdges: [{ ...DATA_EDGE, isCompatible: false }],
    }
    const { edges } = projectToFlow(incompatibleProject)
    const dfEdge = edges.find((e) => e.type === 'dataFlowEdge')!
    const marker = dfEdge.markerEnd as { color: string }
    expect(marker.color).toBe('#ef4444')
  })

  it('node data field contains the original domain object', () => {
    const { nodes } = projectToFlow(MOCK_PROJECT)
    const routerNode = nodes.find((n) => n.id === FN_ROUTER.id)!
    // data should be the FunctionNode object (isAsync: true)
    expect((routerNode.data as unknown as FunctionNode).isAsync).toBe(true)
    expect((routerNode.data as unknown as FunctionNode).name).toBe('create_job')
  })

  it('node positions are assigned (not zero for all)', () => {
    const { nodes } = projectToFlow(MOCK_PROJECT, { rootFunctionId: FN_ROUTER.id })
    const positions = nodes.map((n) => n.position)
    // At least one node should not be at (0,0) — the layout should spread them
    const nonZero = positions.filter((p) => p.x !== 0 || p.y !== 0)
    expect(nonZero.length).toBeGreaterThan(0)
  })
})
