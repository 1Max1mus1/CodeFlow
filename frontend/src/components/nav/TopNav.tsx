import type { AppView } from '../../store'
import type { Operation } from '../../types'

interface TopNavProps {
  projectName: string | null
  activeView: AppView
  onViewChange: (view: AppView) => void
  operationHistory: Operation[]
  onRollbackClick: (op: Operation) => void
}

const STATUS_COLOR: Record<string, string> = {
  applied: 'bg-green-700 text-green-200',
  reverted: 'bg-gray-600 text-gray-300',
  ready: 'bg-blue-800 text-blue-200',
}

const OP_ICON: Record<string, string> = {
  delete: '🗑',
  replace: '⇄',
  add_insert: '⊕',
  add_branch: '⤵',
  add_api: '🔗',
  generate_test: '🧪',
}

export function TopNav({ projectName, activeView, onViewChange, operationHistory, onRollbackClick }: TopNavProps) {
  return (
    <div className="h-10 bg-gray-900 border-b border-gray-700 flex items-center px-4 gap-4 shrink-0 z-30">
      {/* Logo + project name */}
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-blue-400 font-bold text-sm tracking-tight">Codeflow</span>
        {projectName && (
          <>
            <span className="text-gray-600">/</span>
            <span className="text-gray-300 text-xs truncate max-w-[160px]">{projectName}</span>
          </>
        )}
      </div>

      {/* Tab switcher — center */}
      <div className="flex-1 flex justify-center">
        <div className="flex items-center bg-gray-800 rounded-lg p-0.5 gap-0.5">
          <button
            onClick={() => onViewChange('graph')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
              activeView === 'graph'
                ? 'bg-blue-700 text-white shadow'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            📊 Graph
          </button>
          <button
            onClick={() => onViewChange('ide')}
            className={`px-3 py-1 rounded-md text-xs font-medium transition-all ${
              activeView === 'ide'
                ? 'bg-blue-700 text-white shadow'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            📝 IDE
          </button>
        </div>
      </div>

      {/* Operation history — right */}
      <div className="flex items-center gap-1.5 overflow-hidden max-w-[400px]">
        {operationHistory.length === 0 ? (
          <span className="text-xs text-gray-600">No operations yet</span>
        ) : (
          operationHistory.slice(0, 5).map((op) => {
            const canRollback = op.status === 'applied'
            return canRollback ? (
              <button
                key={op.id}
                onClick={() => onRollbackClick(op)}
                title={`${op.type} · ${op.status} — 点击回撤至此`}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs cursor-pointer transition-opacity hover:opacity-70 ${
                  STATUS_COLOR[op.status] ?? 'bg-gray-700 text-gray-400'
                }`}
              >
                <span>{OP_ICON[op.type] ?? '•'}</span>
                <span className="hidden sm:inline">{op.type}</span>
              </button>
            ) : (
              <span
                key={op.id}
                title={`${op.type} · ${op.status}`}
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${
                  STATUS_COLOR[op.status] ?? 'bg-gray-700 text-gray-400'
                }`}
              >
                <span>{OP_ICON[op.type] ?? '•'}</span>
                <span className="hidden sm:inline">{op.type}</span>
              </span>
            )
          })
        )}
        {operationHistory.length > 5 && (
          <span className="text-xs text-gray-500">+{operationHistory.length - 5}</span>
        )}
      </div>
    </div>
  )
}
