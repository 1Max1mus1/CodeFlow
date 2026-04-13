/**
 * Dagre-based hierarchical layout for function call graphs.
 * Left-to-right direction: callers on the left, callees on the right.
 * Schema and ExternalAPI nodes are placed in their own lane to the right.
 */
import dagre from '@dagrejs/dagre'

const NODE_WIDTH = 240
const NODE_HEIGHT = 110
const SCHEMA_WIDTH = 220
const SCHEMA_HEIGHT = 100
const RANKSEP = 80   // horizontal gap between levels
const NODESEP = 40   // vertical gap between nodes in same level

export interface LayoutInput {
  functionIds: string[]
  callEdges: Array<{ sourceId: string; targetId: string }>
  schemaIds: string[]
  externalApiIds: string[]
  rootId?: string | null
}

export type PositionMap = Record<string, { x: number; y: number }>

export function computeGraphLayout(input: LayoutInput): PositionMap {
  const { functionIds, callEdges, schemaIds, externalApiIds } = input
  const positions: PositionMap = {}

  // ── Function nodes via dagre ──────────────────────────────────────────────
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({
    rankdir: 'LR',   // left → right
    ranksep: RANKSEP,
    nodesep: NODESEP,
    marginx: 40,
    marginy: 40,
  })

  for (const id of functionIds) {
    g.setNode(id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  }

  // Only include edges where both endpoints are functions
  const fnSet = new Set(functionIds)
  for (const edge of callEdges) {
    if (fnSet.has(edge.sourceId) && fnSet.has(edge.targetId)) {
      g.setEdge(edge.sourceId, edge.targetId)
    }
  }

  dagre.layout(g)

  let maxX = 0
  for (const id of functionIds) {
    const node = g.node(id)
    if (node) {
      // dagre gives center coords; ReactFlow uses top-left
      positions[id] = {
        x: node.x - NODE_WIDTH / 2,
        y: node.y - NODE_HEIGHT / 2,
      }
      maxX = Math.max(maxX, node.x + NODE_WIDTH / 2)
    }
  }

  // ── Schema nodes: stacked to the right of the function graph ──────────────
  const schemaStartX = maxX + RANKSEP * 2
  schemaIds.forEach((id, i) => {
    positions[id] = {
      x: schemaStartX,
      y: i * (SCHEMA_HEIGHT + NODESEP),
    }
  })

  // ── External API nodes: one more column to the right ─────────────────────
  const apiStartX = schemaStartX + (schemaIds.length > 0 ? SCHEMA_WIDTH + RANKSEP * 2 : 0)
  externalApiIds.forEach((id, i) => {
    positions[id] = {
      x: apiStartX,
      y: i * (SCHEMA_HEIGHT + NODESEP),
    }
  })

  return positions
}
