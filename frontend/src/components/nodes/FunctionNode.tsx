import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { FunctionNode } from '../../types'

export function FunctionNodeComponent({ data, selected }: NodeProps & { data: FunctionNode }) {
  return (
    <div className={`bg-blue-900 border-2 rounded-lg px-4 py-3 min-w-[220px] text-white shadow-lg transition-colors ${
      selected ? 'border-white shadow-white/20 shadow-lg' : 'border-blue-500'
    }`}>
      <Handle type="target" position={Position.Left} className="w-3 h-3 bg-blue-400" />

      <div className="flex items-center gap-2 mb-1">
        <span className="text-blue-400 text-xs font-bold uppercase tracking-wider">fn</span>
        {data.isAsync && (
          <span className="text-xs bg-blue-700 text-blue-200 px-1.5 py-0.5 rounded">async</span>
        )}
      </div>

      <div className="font-mono font-semibold text-sm text-white">{data.name}</div>

      <div className="text-xs text-blue-300 mt-1 truncate max-w-[200px]">{data.filePath}</div>

      {data.className && (
        <div className="text-xs text-blue-400 mt-0.5">class: {data.className}</div>
      )}

      <div className="flex items-center gap-2 mt-2 text-xs text-blue-300">
        <span>{data.params.length} param{data.params.length !== 1 ? 's' : ''}</span>
        {data.returnType && (
          <>
            <span>→</span>
            <span className="font-mono text-blue-200 truncate max-w-[100px]">{data.returnType}</span>
          </>
        )}
      </div>

      <Handle type="source" position={Position.Right} className="w-3 h-3 bg-blue-400" />
    </div>
  )
}
