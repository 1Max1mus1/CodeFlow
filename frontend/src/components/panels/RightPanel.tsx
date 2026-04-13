import { useState, useEffect, useRef, useCallback } from 'react'
import type { Operation, ParsedProject } from '../../types'
import { AIConversation } from './AIConversation'
import { DiffPreview } from './DiffPreview'
import { IDEChatPanel } from '../ide/IDEChatPanel'

interface RightPanelProps {
  operation: Operation | null
  operationError: string | null
  selectedNodeId: string | null
  project: ParsedProject | null
  sessionId: string | null
  onAnswer: (questionId: string, answer: string) => Promise<void>
  onApply: () => void
  onRevert: () => void
  onReplace: (targetFunctionId: string, apiNodeId: string) => void
  onAddBranch: (targetFunctionId: string) => void
  onDelete: (nodeId: string) => void
  onGoToCode: (nodeId: string) => void
  onRollback: () => void
  onOpenInIDE: (nodeId: string) => void
  onClearOperation: () => void
}

type ActiveTab = 'inspector' | 'assistant'

export function RightPanel({
  operation,
  operationError,
  selectedNodeId,
  project,
  sessionId,
  onAnswer,
  onApply,
  onRevert,
  onReplace,
  onAddBranch,
  onDelete,
  onGoToCode,
  onRollback,
  onOpenInIDE,
  onClearOperation,
}: RightPanelProps) {
  const [replaceFunctionId, setReplaceFunctionId] = useState('')
  const [showCode, setShowCode] = useState(true)
  const [activeTab, setActiveTab] = useState<ActiveTab>('inspector')

  // ── Resizable width ───────────────────────────────────────────────────────
  const [width, setWidth] = useState(384)
  const isDragging = useRef(false)
  const dragStartX = useRef(0)
  const dragStartWidth = useRef(384)

  const onDragHandleMouseDown = useCallback((e: React.MouseEvent) => {
    isDragging.current = true
    dragStartX.current = e.clientX
    dragStartWidth.current = width
    e.preventDefault()
  }, [width])

  useEffect(() => {
    function onMouseMove(e: MouseEvent) {
      if (!isDragging.current) return
      const delta = dragStartX.current - e.clientX
      const next = Math.max(280, Math.min(700, dragStartWidth.current + delta))
      setWidth(next)
    }
    function onMouseUp() { isDragging.current = false }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [])

  // ── Auto-switch to AI tab when a new operation starts ────────────────────
  useEffect(() => {
    if (operation) setActiveTab('assistant')
  }, [operation?.id])

  // ── Auto-expand code when switching nodes ─────────────────────────────────
  useEffect(() => {
    setShowCode(true)
  }, [selectedNodeId])

  // ── Derived selection state ───────────────────────────────────────────────
  const isExternalAPISelected =
    selectedNodeId != null && selectedNodeId.startsWith('external::')

  const isFunctionSelected =
    selectedNodeId != null &&
    !isExternalAPISelected &&
    (project?.functions.some((fn) => fn.id === selectedNodeId) ?? false)

  const isSchemaSelected =
    selectedNodeId != null &&
    !isExternalAPISelected &&
    !isFunctionSelected &&
    (project?.schemas.some((s) => s.id === selectedNodeId) ?? false)

  const selectedAPI = isExternalAPISelected
    ? project?.externalApis.find((a) => a.id === selectedNodeId) ?? null
    : null

  const selectedFn = isFunctionSelected
    ? project?.functions.find((fn) => fn.id === selectedNodeId) ?? null
    : null

  const selectedSchema = isSchemaSelected
    ? project?.schemas.find((s) => s.id === selectedNodeId) ?? null
    : null

  function handleReplace() {
    if (!replaceFunctionId || !selectedNodeId) return
    onReplace(replaceFunctionId, selectedNodeId)
    setReplaceFunctionId('')
  }

  // Dot color for the AI tab indicator
  const opDotColor =
    operation?.status === 'ready'         ? 'bg-green-400' :
    operation?.status === 'awaiting_user' ? 'bg-yellow-400' :
    operation?.status === 'applied'       ? 'bg-blue-400' :
    operation?.status === 'analyzing' || operation?.status === 'generating'
                                          ? 'bg-gray-400 animate-pulse' :
    'bg-gray-500'

  return (
    <div
      style={{ width }}
      className="relative bg-gray-900 border-l border-gray-700 flex flex-col h-full shrink-0"
    >
      {/* ── Resize drag handle ── */}
      <div
        onMouseDown={onDragHandleMouseDown}
        className="absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize hover:bg-blue-500/40 transition-colors z-10 group"
        title="Drag to resize"
      >
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-gray-600 group-hover:bg-blue-400 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>

      {/* ── Tab bar ── */}
      <div className="pl-3 pr-3 pt-2 pb-0 border-b border-gray-700 flex flex-col gap-0">
        <div className="flex gap-1">
          {/* Inspector tab */}
          <button
            onClick={() => setActiveTab('inspector')}
            className={`flex-1 flex items-center justify-center gap-1.5 text-xs font-semibold py-2 rounded-t transition-colors border-b-2 ${
              activeTab === 'inspector'
                ? 'text-white border-blue-500 bg-gray-800'
                : 'text-gray-500 border-transparent hover:text-gray-300 hover:bg-gray-800/50'
            }`}
          >
            <span>🔍</span>
            Inspector
          </button>

          {/* AI Assistant tab */}
          <button
            onClick={() => setActiveTab('assistant')}
            className={`flex-1 flex items-center justify-center gap-1.5 text-xs font-semibold py-2 rounded-t transition-colors border-b-2 ${
              activeTab === 'assistant'
                ? 'text-white border-blue-500 bg-gray-800'
                : 'text-gray-500 border-transparent hover:text-gray-300 hover:bg-gray-800/50'
            }`}
          >
            <span>✨</span>
            AI Assistant
            {/* Status dot — only shown when not on this tab */}
            {operation && activeTab !== 'assistant' && (
              <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${opDotColor}`} />
            )}
          </button>
        </div>

        {/* Sub-header: operation status + X, shown only on AI tab when op is active */}
        {activeTab === 'assistant' && operation && (
          <div className="flex items-center justify-between py-1.5 px-1">
            <span className="text-xs text-gray-500 truncate">
              {operation.type} · {operation.targetNodeId.split('::').pop()}
            </span>
            <div className="flex items-center gap-1.5 shrink-0">
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                operation.status === 'ready'         ? 'bg-green-900 text-green-300' :
                operation.status === 'applied'       ? 'bg-blue-900 text-blue-300' :
                operation.status === 'awaiting_user' ? 'bg-yellow-900 text-yellow-300' :
                operation.status === 'reverted'      ? 'bg-gray-700 text-gray-400' :
                'bg-gray-800 text-gray-400'
              }`}>
                {operation.status}
              </span>
              <button
                onClick={onClearOperation}
                title="Dismiss operation"
                className="w-5 h-5 flex items-center justify-center text-gray-500 hover:text-white hover:bg-gray-700 rounded transition-colors text-xs"
              >
                ✕
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── Body ── */}
      <div className="flex-1 overflow-hidden flex flex-col">

        {/* ════════════════ INSPECTOR TAB ════════════════ */}
        {activeTab === 'inspector' && (
          <>
            {/* Function inspector */}
            {selectedFn && (
              <div className="flex flex-col flex-1 overflow-hidden">
                <div className="p-4 border-b border-gray-700 flex flex-col gap-2 shrink-0">
                  <div className="flex items-center gap-2">
                    <span className="text-blue-400 text-xs font-bold uppercase">fn</span>
                    {selectedFn.isAsync && (
                      <span className="text-xs bg-blue-900 text-blue-300 px-1.5 py-0.5 rounded">async</span>
                    )}
                    <span className="font-mono text-sm text-white font-semibold truncate">{selectedFn.name}</span>
                  </div>
                  <div className="text-xs text-gray-400 font-mono truncate">{selectedFn.filePath}</div>
                  {selectedFn.className && (
                    <div className="text-xs text-gray-500">class: {selectedFn.className}</div>
                  )}
                  <div className="flex gap-3 text-xs text-gray-400 flex-wrap">
                    <span>{selectedFn.params.length} param{selectedFn.params.length !== 1 ? 's' : ''}</span>
                    {selectedFn.returnType && (
                      <span>→ <span className="text-blue-300 font-mono">{selectedFn.returnType}</span></span>
                    )}
                    <span>L{selectedFn.startLine}–{selectedFn.endLine}</span>
                  </div>

                  <div className="flex gap-2 mt-1">
                    <button
                      onClick={() => onDelete(selectedFn.id)}
                      className="flex-1 bg-red-900 hover:bg-red-800 text-red-300 text-xs font-semibold py-1.5 rounded transition-colors"
                    >
                      Delete
                    </button>
                    <button
                      onClick={() => onAddBranch(selectedFn.id)}
                      className="flex-1 bg-yellow-900 hover:bg-yellow-800 text-yellow-300 text-xs font-semibold py-1.5 rounded transition-colors"
                    >
                      Add Branch
                    </button>
                  </div>

                  <div className="text-xs text-gray-500 bg-gray-800 rounded px-2 py-1.5">
                    Click any outgoing <span className="text-blue-300">call edge</span> to insert a function between two nodes.
                  </div>
                </div>

                {/* Source code preview */}
                <div className="flex-1 flex flex-col overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-2 border-b border-gray-700 shrink-0">
                    <button
                      onClick={() => setShowCode((v) => !v)}
                      className="text-xs text-gray-400 hover:text-gray-200 font-semibold uppercase tracking-wider transition-colors flex items-center gap-1"
                    >
                      <span>{showCode ? '▼' : '▶'}</span>
                      Source Code
                    </button>
                    <button
                      onClick={() => onOpenInIDE(selectedFn.id)}
                      title="Double-click node also opens IDE"
                      className="text-xs text-blue-400 hover:text-blue-200 font-semibold px-2 py-0.5 rounded hover:bg-blue-900/40 transition-colors"
                    >
                      Open in IDE →
                    </button>
                  </div>
                  {showCode && (
                    <pre className="flex-1 overflow-auto p-3 text-xs font-mono text-gray-300 bg-gray-950 leading-relaxed">
                      {selectedFn.sourceCode}
                    </pre>
                  )}
                </div>
              </div>
            )}

            {/* Schema inspector */}
            {selectedSchema && (
              <div className="p-4 flex flex-col gap-3 overflow-y-auto">
                <div className="flex items-center gap-2">
                  <span className="text-purple-400 text-xs font-bold uppercase">schema</span>
                  <span className="text-xs bg-purple-900 text-purple-300 px-1.5 py-0.5 rounded">{selectedSchema.schemaType}</span>
                </div>
                <div className="text-xs text-gray-400 font-mono truncate">{selectedSchema.filePath}</div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500">L{selectedSchema.startLine}–{selectedSchema.endLine}</span>
                  <button
                    onClick={() => onOpenInIDE(selectedSchema.id)}
                    className="text-xs text-purple-400 hover:text-purple-200 font-semibold px-2 py-0.5 rounded hover:bg-purple-900/40 transition-colors"
                  >
                    Open in IDE →
                  </button>
                </div>
                <div className="border-t border-gray-700 pt-2">
                  <div className="text-xs text-gray-500 mb-2 uppercase tracking-wider">Fields ({selectedSchema.fields.length})</div>
                  {selectedSchema.fields.map((f) => (
                    <div key={f.name} className="flex items-center gap-2 py-0.5 flex-wrap">
                      <span className="text-gray-300 font-mono text-xs">{f.name}</span>
                      <span className="text-purple-300 text-xs font-mono">{f.type}</span>
                      {f.isOptional && <span className="text-gray-600 text-xs">optional</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* External API inspector */}
            {selectedAPI && (
              <div className="p-4 border-b border-gray-700 flex flex-col gap-3">
                <div>
                  <p className="text-xs text-purple-300 font-semibold mb-1">{selectedAPI.name}</p>
                  <p className="text-xs text-gray-400 font-mono">{selectedAPI.method} {selectedAPI.endpoint}</p>
                  {selectedAPI.description && (
                    <p className="text-xs text-gray-500 mt-1">{selectedAPI.description}</p>
                  )}
                </div>
                <p className="text-xs text-gray-500">Drag onto a function to replace it, or select below:</p>
                <select
                  value={replaceFunctionId}
                  onChange={(e) => setReplaceFunctionId(e.target.value)}
                  className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-purple-500"
                >
                  <option value="">— select a function —</option>
                  {project?.functions.map((fn) => (
                    <option key={fn.id} value={fn.id}>{fn.name}</option>
                  ))}
                </select>
                <button
                  onClick={handleReplace}
                  disabled={!replaceFunctionId}
                  className="w-full bg-purple-700 hover:bg-purple-600 disabled:bg-gray-700 disabled:text-gray-500 text-white text-xs font-semibold py-1.5 rounded transition-colors"
                >
                  Replace with this API
                </button>
              </div>
            )}

            {/* Empty state */}
            {!selectedFn && !selectedSchema && !selectedAPI && (
              <div className="p-4 text-sm text-gray-500">
                Click a node to inspect it, or right-click for operations.
              </div>
            )}
          </>
        )}

        {/* ════════════════ AI ASSISTANT TAB ════════════════ */}
        {activeTab === 'assistant' && (
          <>
            {/* Operation error */}
            {operationError && (
              <div className="mx-3 mt-3 p-3 bg-red-950 border border-red-700 rounded text-xs text-red-300 leading-relaxed shrink-0">
                <div className="font-semibold mb-1">Error</div>
                <div className="text-red-400 break-all">{operationError}</div>
              </div>
            )}

            {/* Awaiting answers */}
            {operation?.status === 'awaiting_user' && (
              <AIConversation questions={operation.aiQuestions} onAnswer={onAnswer} />
            )}

            {/* Diff preview */}
            {operation?.status === 'ready' && operation.generatedDiffs && (
              <DiffPreview
                diffs={operation.generatedDiffs}
                targetNodeId={operation.targetNodeId}
                onApply={onApply}
                onRevert={onRevert}
                onGoToCode={onGoToCode}
              />
            )}

            {/* Processing */}
            {(operation?.status === 'analyzing' || operation?.status === 'generating') && (
              <div className="p-4 flex flex-col gap-2">
                <div className="text-sm text-gray-400 animate-pulse">AI is thinking…</div>
                <div className="text-xs text-gray-600">This may take 10–30 seconds.</div>
              </div>
            )}

            {/* Applied */}
            {operation?.status === 'applied' && (
              <div className="p-4 flex flex-col gap-3">
                <div className="text-sm text-green-400 font-semibold">Changes applied to disk.</div>
                {operation.generatedDiffs && operation.generatedDiffs.length > 0 && (
                  <button
                    onClick={onRollback}
                    className="w-full bg-orange-900 hover:bg-orange-800 text-orange-300 text-xs font-semibold py-2 rounded transition-colors"
                  >
                    Undo Changes (restore files)
                  </button>
                )}
                <button
                  onClick={onClearOperation}
                  className="text-xs text-gray-600 hover:text-gray-400 underline text-left"
                >
                  Dismiss ✕
                </button>
              </div>
            )}

            {/* Reverted */}
            {operation?.status === 'reverted' && (
              <div className="p-4 flex flex-col gap-2">
                <div className="text-sm text-gray-500">Operation reverted.</div>
                <button
                  onClick={onClearOperation}
                  className="text-xs text-gray-600 hover:text-gray-400 underline text-left"
                >
                  Dismiss ✕
                </button>
              </div>
            )}

            {/* Chat — shown when no active operation */}
            {!operation && !operationError && (
              <IDEChatPanel
                sessionId={sessionId}
                contextNodeId={selectedNodeId}
                contextNodeName={
                  selectedFn?.name ?? selectedSchema?.name ?? null
                }
              />
            )}
          </>
        )}
      </div>
    </div>
  )
}
