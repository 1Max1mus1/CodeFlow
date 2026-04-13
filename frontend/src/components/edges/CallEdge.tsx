import { getBezierPath } from '@xyflow/react'
import type { EdgeProps } from '@xyflow/react'

export function CallEdgeComponent({
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  markerEnd,
  selected,
}: EdgeProps) {
  const [edgePath] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition })

  return (
    <>
      {/* Wider transparent hit area for easier clicking */}
      <path
        d={edgePath}
        fill="none"
        stroke="transparent"
        strokeWidth={16}
        style={{ cursor: 'pointer' }}
        className="react-flow__edge-interaction"
      />
      {/* Visible edge */}
      <path
        d={edgePath}
        fill="none"
        stroke={selected ? '#93c5fd' : '#3b82f6'}
        strokeWidth={selected ? 3 : 2}
        markerEnd={markerEnd}
        className="react-flow__edge-path"
        style={{ cursor: 'pointer' }}
      />
    </>
  )
}
