import { useEffect, useRef } from 'react'

interface ContextMenuProps {
  x: number
  y: number
  nodeId: string
  nodeType: 'function' | 'schema' | 'external'
  nodeName: string
  onDelete: () => void
  onAddBranch: () => void
  onClose: () => void
}

export function ContextMenu({
  x,
  y,
  nodeType,
  nodeName,
  onDelete,
  onAddBranch,
  onClose,
}: ContextMenuProps) {
  const ref = useRef<HTMLDivElement>(null)

  // Close on click outside
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose()
      }
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleKey)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleKey)
    }
  }, [onClose])

  // Clamp position so menu stays on screen
  const menuWidth = 200
  const menuHeight = nodeType === 'function' ? 130 : 60
  const clampedX = Math.min(x, window.innerWidth - menuWidth - 8)
  const clampedY = Math.min(y, window.innerHeight - menuHeight - 8)

  return (
    <div
      ref={ref}
      className="fixed z-50 bg-gray-800 border border-gray-600 rounded-lg shadow-2xl py-1 text-sm"
      style={{ left: clampedX, top: clampedY, minWidth: menuWidth }}
    >
      {/* Header */}
      <div className="px-3 py-1.5 border-b border-gray-700 mb-1">
        <span className={`text-xs font-bold uppercase mr-1.5 ${
          nodeType === 'function' ? 'text-blue-400' :
          nodeType === 'schema' ? 'text-purple-400' : 'text-purple-300'
        }`}>
          {nodeType === 'function' ? 'fn' : nodeType === 'schema' ? 'schema' : 'api'}
        </span>
        <span className="text-gray-300 text-xs font-mono truncate">{nodeName}</span>
      </div>

      {nodeType === 'function' && (
        <>
          <button
            onClick={() => { onDelete(); onClose() }}
            className="w-full text-left px-3 py-2 text-red-300 hover:bg-red-900/40 transition-colors flex items-center gap-2"
          >
            <span>🗑</span>
            <span>Delete function</span>
          </button>
          <button
            onClick={() => { onAddBranch(); onClose() }}
            className="w-full text-left px-3 py-2 text-yellow-300 hover:bg-yellow-900/40 transition-colors flex items-center gap-2"
          >
            <span>⤵</span>
            <span>Add branch function</span>
          </button>
          <div className="px-3 py-1.5 mt-1 border-t border-gray-700">
            <span className="text-xs text-gray-600">Click a call edge to insert between nodes</span>
          </div>
        </>
      )}

      {nodeType !== 'function' && (
        <div className="px-3 py-2 text-gray-500 text-xs">
          No operations available for this node type.
        </div>
      )}
    </div>
  )
}
