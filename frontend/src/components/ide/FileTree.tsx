import type { ParsedProject } from '../../types'

interface FileTreeProps {
  project: ParsedProject
  selectedFile: string | null
  onSelectFile: (filePath: string) => void
}

export function FileTree({ project, selectedFile, onSelectFile }: FileTreeProps) {
  // Collect unique file paths from both functions AND schemas
  const filePaths = [
    ...new Set([
      ...project.functions.map((f) => f.filePath),
      ...project.schemas.map((s) => s.filePath),
    ]),
  ].sort()

  // Group by directory
  const byDir = new Map<string, string[]>()
  for (const fp of filePaths) {
    const parts = fp.replace(/\\/g, '/').split('/')
    const dir = parts.length > 1 ? parts.slice(0, -1).join('/') : ''
    if (!byDir.has(dir)) byDir.set(dir, [])
    byDir.get(dir)!.push(fp)
  }

  const dirs = [...byDir.keys()].sort()

  return (
    <div className="w-56 bg-gray-900 border-r border-gray-700 flex flex-col h-full overflow-hidden">
      <div className="px-3 py-2 border-b border-gray-700">
        <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider">Files</h2>
        <p className="text-xs text-gray-600 mt-0.5">{filePaths.length} source file{filePaths.length !== 1 ? 's' : ''}</p>
      </div>

      <div className="flex-1 overflow-y-auto py-1">
        {dirs.map((dir) => (
          <div key={dir}>
            {dir && (
              <div className="px-3 pt-2 pb-0.5 text-xs text-gray-500 font-medium select-none">
                📁 {dir}
              </div>
            )}
            {byDir.get(dir)!.map((fp) => {
              const filename = fp.replace(/\\/g, '/').split('/').pop()!
              const fnCount = project.functions.filter((f) => f.filePath === fp).length
              const isSelected = selectedFile === fp
              return (
                <button
                  key={fp}
                  onClick={() => onSelectFile(fp)}
                  className={`w-full text-left px-3 py-1.5 text-xs transition-colors flex items-center justify-between group ${
                    isSelected
                      ? 'bg-blue-900 text-blue-200'
                      : 'text-gray-300 hover:bg-gray-800'
                  }`}
                >
                  <span className="font-mono truncate flex items-center gap-1.5">
                    <span className="text-blue-500">🐍</span>
                    {filename}
                  </span>
                  <span className={`text-xs shrink-0 ${isSelected ? 'text-blue-400' : 'text-gray-600'}`}>
                    {fnCount}fn
                  </span>
                </button>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}
