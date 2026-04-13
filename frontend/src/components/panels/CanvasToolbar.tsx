import type { ParsedProject } from '../../types'

interface CanvasToolbarProps {
  selectedNodeId: string | null
  project: ParsedProject | null
  hasSession: boolean
  onDelete: (nodeId: string) => void
  onAddBranch: (nodeId: string) => void
  onImportAPI: () => void
  onFitView: () => void
}

export function CanvasToolbar({
  selectedNodeId,
  project,
  hasSession,
  onDelete,
  onAddBranch,
  onImportAPI,
  onFitView,
}: CanvasToolbarProps) {
  const selectedFn = selectedNodeId
    ? project?.functions.find((f) => f.id === selectedNodeId) ?? null
    : null

  const isFunctionSelected = selectedFn != null
  const isExternalSelected = selectedNodeId?.startsWith('external::') ?? false

  return (
    <div className="absolute top-3 left-1/2 -translate-x-1/2 z-20 flex items-center gap-1 bg-gray-800/95 backdrop-blur border border-gray-600 rounded-xl px-3 py-2 shadow-2xl">
      {/* Always visible actions */}
      <button
        onClick={onFitView}
        title="Fit view"
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
      >
        <span>⊞</span>
        <span className="hidden sm:inline">Fit View</span>
      </button>

      <div className="w-px h-5 bg-gray-600 mx-1" />

      <button
        onClick={onImportAPI}
        disabled={!hasSession}
        title="Import external API"
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-purple-300 hover:bg-purple-900/50 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        <span>＋</span>
        <span>Import API</span>
      </button>

      {/* Context-sensitive actions — shown when a function is selected */}
      {isFunctionSelected && selectedFn && (
        <>
          <div className="w-px h-5 bg-gray-600 mx-1" />

          <div className="flex items-center gap-1 bg-gray-700/60 rounded-lg px-2 py-1">
            <span className="text-blue-400 text-xs font-mono font-semibold mr-1 max-w-[120px] truncate">
              {selectedFn.name}
            </span>

            <button
              onClick={() => onAddBranch(selectedFn.id)}
              title="Add branch function"
              className="flex items-center gap-1 px-2 py-1 rounded text-xs text-yellow-300 hover:bg-yellow-900/50 transition-colors"
            >
              <span>⤵</span>
              <span>Branch</span>
            </button>

            <button
              onClick={() => onDelete(selectedFn.id)}
              title="Delete function"
              className="flex items-center gap-1 px-2 py-1 rounded text-xs text-red-300 hover:bg-red-900/50 transition-colors"
            >
              <span>🗑</span>
              <span>Delete</span>
            </button>
          </div>
        </>
      )}

      {/* Hint when nothing selected */}
      {!isFunctionSelected && !isExternalSelected && (
        <>
          <div className="w-px h-5 bg-gray-600 mx-1" />
          <span className="text-xs text-gray-500 px-1">
            Click a node to inspect · right-click for ops · click an edge to insert
          </span>
        </>
      )}
    </div>
  )
}
