import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { ExternalAPINode } from '../../types'

export function ExternalAPINodeComponent({ data, selected }: NodeProps & { data: ExternalAPINode }) {
  return (
    <div className={`bg-green-900 border-2 rounded-lg px-4 py-3 min-w-[220px] text-white shadow-lg transition-colors ${
      selected ? 'border-white' : 'border-green-500'
    }`}>
      <Handle type="target" position={Position.Left} className="w-3 h-3 bg-green-400" />

      <div className="flex items-center gap-2 mb-1">
        <span className="text-green-400 text-xs font-bold uppercase tracking-wider">external api</span>
        <span className="text-xs bg-green-700 text-green-200 px-1.5 py-0.5 rounded">
          {data.method}
        </span>
      </div>

      <div className="font-semibold text-sm text-white">{data.name}</div>

      <div className="text-xs text-green-300 mt-1 truncate max-w-[200px]">{data.endpoint}</div>

      <div className="flex gap-3 mt-2 text-xs text-green-300">
        <span>{data.inputSchema.length} in</span>
        <span>{data.outputSchema.length} out</span>
      </div>

      <Handle type="source" position={Position.Right} className="w-3 h-3 bg-green-400" />
    </div>
  )
}
