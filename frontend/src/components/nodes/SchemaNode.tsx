import { Handle, Position } from '@xyflow/react'
import type { NodeProps } from '@xyflow/react'
import type { SchemaNode } from '../../types'

export function SchemaNodeComponent({ data, selected }: NodeProps & { data: SchemaNode }) {
  return (
    <div className={`bg-purple-900 border-2 rounded-lg px-4 py-3 min-w-[200px] text-white shadow-lg transition-colors ${
      selected ? 'border-white' : 'border-purple-500'
    }`}>
      <Handle type="target" position={Position.Left} className="w-3 h-3 bg-purple-400" />

      <div className="flex items-center gap-2 mb-1">
        <span className="text-purple-400 text-xs font-bold uppercase tracking-wider">schema</span>
        <span className="text-xs bg-purple-700 text-purple-200 px-1.5 py-0.5 rounded">
          {data.schemaType}
        </span>
      </div>

      <div className="font-mono font-semibold text-sm text-white">{data.name}</div>

      <div className="text-xs text-purple-300 mt-1 truncate max-w-[180px]">{data.filePath}</div>

      <div className="text-xs text-purple-300 mt-2">
        {data.fields.length} field{data.fields.length !== 1 ? 's' : ''}
      </div>

      <Handle type="source" position={Position.Right} className="w-3 h-3 bg-purple-400" />
    </div>
  )
}
