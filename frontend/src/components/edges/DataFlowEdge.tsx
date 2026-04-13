import { getBezierPath } from '@xyflow/react'
import type { EdgeProps } from '@xyflow/react'

export function DataFlowEdgeComponent({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  data,
}: EdgeProps) {
  const [edgePath] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition })
  const isCompatible = (data as Record<string, unknown> | undefined)?.isCompatible
  const color = isCompatible === false ? '#ef4444' : '#f97316'

  return (
    <>
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={16}
        style={{ cursor: 'pointer' }}
        className="react-flow__edge-interaction"
      />
      <path
        d={edgePath}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeDasharray="6 3"
        markerEnd={markerEnd}
        className="react-flow__edge-path"
        style={{ cursor: 'pointer' }}
      />
    </>
  )
}
