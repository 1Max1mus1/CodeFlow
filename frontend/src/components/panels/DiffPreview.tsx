import type { FileDiff } from '../../types'

interface DiffPreviewProps {
  diffs: FileDiff[]
  targetNodeId: string | null
  onApply: () => void
  onRevert: () => void
  onGoToCode: ((nodeId: string) => void) | null
}

export function DiffPreview({ diffs, targetNodeId, onApply, onRevert, onGoToCode }: DiffPreviewProps) {
  const hasChanges = diffs.length > 0 && diffs.some((d) => d.changes.length > 0)
  const isManual = diffs.length === 0

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isManual ? (
          <div className="text-xs text-gray-400 bg-gray-800 rounded p-3 space-y-3">
            <p>No AI changes generated — you chose to handle this manually.</p>
            {onGoToCode && targetNodeId && (
              <button
                onClick={() => onGoToCode(targetNodeId)}
                className="w-full bg-blue-800 hover:bg-blue-700 text-blue-200 text-xs font-semibold py-2 rounded transition-colors"
              >
                Open in IDE →
              </button>
            )}
            <p className="text-gray-600">
              Click <span className="text-blue-300">Apply</span> to mark complete after you make your changes, or <span className="text-gray-300">Cancel</span> to abort.
            </p>
          </div>
        ) : !hasChanges ? (
          <div className="text-xs text-gray-500 bg-gray-800 rounded p-3">
            The generated file is identical to the original — no diff to show. Click <span className="text-blue-300">Apply</span> to proceed.
          </div>
        ) : (
          diffs.map((diff) => (
            <div key={diff.filePath} className="space-y-1">
              <div className="text-xs font-mono text-gray-400 flex items-center gap-2">
                <span className="text-gray-600">📄</span>
                {diff.filePath}
                <span className="text-gray-600 ml-auto">
                  +{diff.changes.filter(c => c.changeType === 'add').length}
                  {' '}
                  -{diff.changes.filter(c => c.changeType === 'remove').length}
                </span>
              </div>
              <div className="bg-gray-900 rounded text-xs font-mono overflow-x-auto">
                {diff.changes.map((change, i) => (
                  <div
                    key={i}
                    className={`px-3 py-0.5 ${
                      change.changeType === 'add'
                        ? 'bg-green-950 text-green-300'
                        : change.changeType === 'remove'
                        ? 'bg-red-950 text-red-300'
                        : 'bg-yellow-950 text-yellow-300'
                    }`}
                  >
                    <span className="select-none text-gray-600 mr-2 inline-block w-8 text-right">{change.lineNumber}</span>
                    <span className="select-none mr-2">
                      {change.changeType === 'add' ? '+' : change.changeType === 'remove' ? '-' : '~'}
                    </span>
                    {change.changeType === 'remove' ? change.oldLine : change.newLine}
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      <div className="flex gap-2 p-4 border-t border-gray-700">
        <button
          onClick={onApply}
          className="flex-1 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded px-4 py-2 transition-colors"
        >
          Apply Changes
        </button>
        <button
          onClick={onRevert}
          className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm font-medium rounded px-4 py-2 transition-colors"
        >
          Cancel
        </button>
      </div>
    </div>
  )
}
