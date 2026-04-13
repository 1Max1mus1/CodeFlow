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

  // Build a set of (sourceId, targetId) pairs already covered by dataFlowEdges
  // so we don't duplicate edges for return-type schema usage.
  const dataFlowPairs = new Set(
    project.dataFlowEdges.map((e) => `${e.sourceId}::${e.targetId}`)
  );

  // Build schema-usage edges from fn.usesSchemas (param-based, purple solid line)
  const schemaUsageEdges: Edge[] = [];
  const schemaIds = new Set(project.schemas.map((s) => s.id));
  for (const fn of project.functions) {
    for (const schemaId of fn.usesSchemas) {
      if (!schemaIds.has(schemaId)) continue;
      const pairKey = `${fn.id}::${schemaId}`;
      if (dataFlowPairs.has(pairKey)) continue; // already covered by return-type edge
      const edgeId = `uses::${fn.id}::${schemaId}`;
      const schema = project.schemas.find((s) => s.id === schemaId);
      schemaUsageEdges.push({
        id: edgeId,
        type: 'dataFlowEdge',
        source: fn.id,
        target: schemaId,
        markerEnd: { type: MarkerType.ArrowClosed, color: '#a855f7' },
        data: {
          edgeType: 'schemaUsage',
          isParamUsage: true,
          dataType: schema?.name ?? schemaId,
        },
      });
    }
  }

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
    ...schemaUsageEdges,
  ];

  return { nodes, edges };
}
