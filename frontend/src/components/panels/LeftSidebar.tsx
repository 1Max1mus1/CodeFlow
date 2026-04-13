import { useState } from 'react'
import type { EntryPoint } from '../../types'

interface LeftSidebarProps {
  entryPoints: EntryPoint[]
  activeEntryPointId: string | null
  onSelectEntryPoint: (id: string) => void
  onLoadProject: (rootPath: string) => void
  onImportAPI: () => void
  isLoading: boolean
  loadError: string | null
  hasSession: boolean
}

export function LeftSidebar({
  entryPoints,
  activeEntryPointId,
  onSelectEntryPoint,
  onLoadProject,
  onImportAPI,
  isLoading,
  loadError,
  hasSession,
}: LeftSidebarProps) {
  const [inputPath, setInputPath] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = inputPath.trim()
    if (trimmed) onLoadProject(trimmed)
  }

  return (
    <div className="w-64 bg-gray-900 border-r border-gray-700 flex flex-col h-full">
      {/* Project loader */}
      <div className="px-4 py-3 border-b border-gray-700">
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">
          Project
        </h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-2">
          <input
            type="text"
            value={inputPath}
            onChange={(e) => setInputPath(e.target.value)}
            placeholder="/path/to/project/src"
            className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-xs text-gray-200 placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <button
            type="submit"
            disabled={isLoading || inputPath.trim() === ''}
            className="w-full bg-blue-700 hover:bg-blue-600 disabled:bg-gray-700 disabled:text-gray-500 text-white text-xs font-semibold py-1.5 rounded transition-colors"
          >
            {isLoading ? 'Loading…' : 'Load'}
          </button>
        </form>
        {loadError && (
          <p className="mt-2 text-xs text-red-400 break-words">{loadError}</p>
        )}
      </div>

      {/* Entry points */}
      <div className="px-4 pt-3 pb-1 border-b border-gray-700">
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Entry Points</h2>
      </div>
      <div className="flex-1 overflow-y-auto py-2">
        {entryPoints.map((ep) => (
          <button
            key={ep.id}
            onClick={() => onSelectEntryPoint(ep.id)}
            className={`w-full text-left px-4 py-2 text-sm font-mono transition-colors ${
              activeEntryPointId === ep.id
                ? 'bg-blue-900 text-blue-200'
                : 'text-gray-300 hover:bg-gray-800'
            }`}
          >
            {ep.label}
          </button>
        ))}
        {entryPoints.length === 0 && (
          <p className="px-4 py-2 text-xs text-gray-500">No entry points detected.</p>
        )}
      </div>

      {/* Import API button */}
      <div className="px-4 py-3 border-t border-gray-700">
        <button
          onClick={onImportAPI}
          disabled={!hasSession}
          className="w-full bg-purple-800 hover:bg-purple-700 disabled:bg-gray-700 disabled:text-gray-500 text-white text-xs font-semibold py-1.5 rounded transition-colors"
        >
          + Import External API
        </button>
      </div>
    </div>
  )
}
