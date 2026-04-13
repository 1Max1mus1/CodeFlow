/**
 * Converts a ParsedProject into React Flow nodes and edges.
 * Uses computeGraphLayout to assign positions.
 */

import { MarkerType } from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import type { ParsedProject } from '../types';
import { computeGraphLayout } from './graphLayout';

interface ProjectToFlowOptions {
  /** If provided, root of the BFS layout (entry point function ID). */
  rootFunctionId?: string | null;
}

export function projectToFlow(
  project: ParsedProject,
  options: ProjectToFlowOptions = {},
): { nodes: Node[]; edges: Edge[] } {
  const positions = computeGraphLayout({
    functionIds: project.functions.map((f) => f.id),
    callEdges: project.callEdges.map((e) => ({
      sourceId: e.sourceId,
      targetId: e.targetId,
    })),
    schemaIds: project.schemas.map((s) => s.id),
    externalApiIds: project.externalApis.map((a) => a.id),
    rootId: options.rootFunctionId ?? null,
  });

  const nodes: Node[] = [
    ...project.functions.map((fn) => ({
      id: fn.id,
      type: 'functionNode',
      position: positions[fn.id] ?? { x: 0, y: 0 },
      data: fn as unknown as Record<string, unknown>,
    })),
    ...project.schemas.map((schema) => ({
      id: schema.id,
      type: 'schemaNode',
      position: positions[schema.id] ?? { x: 0, y: 0 },
      data: schema as unknown as Record<string, unknown>,
    })),
    ...project.externalApis.map((api) => ({
      id: api.id,
      type: 'externalApiNode',
      position: positions[api.id] ?? { x: 0, y: 0 },
      data: api as unknown as Record<string, unknown>,
    })),
  ];

  const edges: Edge[] = [
    ...project.callEdges.map((edge) => ({
      id: edge.id,
      type: 'callEdge',
      source: edge.sourceId,
      target: edge.targetId,
      markerEnd: { type: MarkerType.ArrowClosed, color: '#3b82f6' },
      data: { edgeType: 'call', callLine: edge.callLine },
    })),
    ...project.dataFlowEdges.map((edge) => ({
      id: edge.id,
      type: 'dataFlowEdge',
      source: edge.sourceId,
      target: edge.targetId,
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: edge.isCompatible ? '#f97316' : '#ef4444',
      },
      data: {
        edgeType: 'dataflow',
        isCompatible: edge.isCompatible,
        dataType: edge.dataType,
      },
    })),
  ];

  return { nodes, edges };
}
