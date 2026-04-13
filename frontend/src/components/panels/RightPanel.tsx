import { useState, useEffect, useRef, useCallback } from 'react'
import type { Operation, ParsedProject } from '../../types'
import { AIConversation } from './AIConversation'
import { DiffPreview } from './DiffPreview'

interface RightPanelProps {
  operation: Operation | null
  operationError: string | null
  selectedNodeId: string | null
  project: ParsedProject | null
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

export function RightPanel({
  operation,
  operationError,
  selectedNodeId,
  project,
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

  // ── Resizable width ───────────────────────────────────────────────────────
  const [width, setWidth] = useState(384) // default = w-96
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
      const delta = dragStartX.current - e.clientX // drag left → widen
      const next = Math.max(280, Math.min(700, dragStartWidth.current + delta))
      setWidth(next)
    }
    function onMouseUp() {
      isDragging.current = false
    }
    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
    return () => {
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [])

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

  const headerLabel = operation
    ? `${operation.type} · ${operation.status}`
    : selectedFn
    ? selectedFn.name
    : selectedSchema
    ? selectedSchema.name
    : selectedAPI
    ? selectedAPI.name
    : 'AI Assistant'

  return (
    <div
      style={{ width }}
      className="relative bg-gray-900 border-l border-gray-700 flex flex-col h-full shrink-0"
    >
      {/* ── Resize drag handle (left edge) ── */}
      <div
        onMouseDown={onDragHandleMouseDown}
        className="absolute left-0 top-0 bottom-0 w-1 cursor-ew-resize hover:bg-blue-500/40 transition-colors z-10 group"
        title="Drag to resize"
      >
        <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-gray-600 group-hover:bg-blue-400 rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>

      {/* ── Header ── */}
      <div className="pl-3 pr-3 py-3 border-b border-gray-700 flex items-center gap-2">
        <div className="flex-1 min-w-0">
          <h2 className="text-xs font-bold text-gray-400 uppercase tracking-wider">
            {operation ? 'AI Assistant' : 'Inspector'}
          </h2>
          <div className="mt-0.5 text-xs text-gray-300 truncate">{headerLabel}</div>
        </div>

        {operation && (
          <>
            <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full ${
              operation.status === 'ready'        ? 'bg-green-900 text-green-300' :
              operation.status === 'applied'      ? 'bg-blue-900 text-blue-300' :
              operation.status === 'awaiting_user'? 'bg-yellow-900 text-yellow-300' :
              operation.status === 'reverted'     ? 'bg-gray-700 text-gray-400' :
              'bg-gray-800 text-gray-400'
            }`}>
              {operation.status}
            </span>
            {/* X: dismiss operation and return to node inspector */}
            <button
              onClick={onClearOperation}
              title="Close operation panel"
              className="shrink-0 w-6 h-6 flex items-center justify-center text-gray-500 hover:text-white hover:bg-gray-700 rounded transition-colors text-sm"
            >
              ✕
            </button>
          </>
        )}
      </div>

      {/* ── Body ── */}
      <div className="flex-1 overflow-hidden flex flex-col">

        {/* ── Function node inspector (shown when no active operation) ── */}
        {selectedFn && !operation && (
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

        {/* ── Schema inspector ── */}
        {selectedSchema && !operation && (
          <div className="p-4 flex flex-col gap-3 overflow-y-auto">
            <div className="flex items-center gap-2">
              <span className="text-purple-400 text-xs font-bold uppercase">schema</span>
              <span className="text-xs bg-purple-900 text-purple-300 px-1.5 py-0.5 rounded">{selectedSchema.schemaType}</span>
            </div>
            <div className="text-xs text-gray-400 font-mono truncate">{selectedSchema.filePath}</div>
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

        {/* ── External API inspector ── */}
        {selectedAPI && !operation && (
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

        {/* ── Empty state ── */}
        {!operation && !selectedAPI && !isFunctionSelected && !isSchemaSelected && (
          <div className="p-4 text-sm text-gray-500">
            Click a node to inspect it, or right-click for operations.
          </div>
        )}

        {/* ── Operation error ── */}
        {operationError && (
          <div className="mx-3 mt-3 p-3 bg-red-950 border border-red-700 rounded text-xs text-red-300 leading-relaxed shrink-0">
            <div className="font-semibold mb-1">Error</div>
            <div className="text-red-400 break-all">{operationError}</div>
          </div>
        )}

        {/* ── Operation: awaiting answers ── */}
        {operation?.status === 'awaiting_user' && (
          <AIConversation questions={operation.aiQuestions} onAnswer={onAnswer} />
        )}

        {/* ── Operation: diff preview ── */}
        {operation?.status === 'ready' && operation.generatedDiffs && (
          <DiffPreview
            diffs={operation.generatedDiffs}
            targetNodeId={operation.targetNodeId}
            onApply={onApply}
            onRevert={onRevert}
            onGoToCode={onGoToCode}
          />
        )}

        {/* ── Operation: processing ── */}
        {(operation?.status === 'analyzing' || operation?.status === 'generating') && (
          <div className="p-4 flex flex-col gap-2">
            <div className="text-sm text-gray-400 animate-pulse">AI is thinking…</div>
            <div className="text-xs text-gray-600">This may take 10–30 seconds.</div>
          </div>
        )}

        {/* ── Operation: applied ── */}
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

        {/* ── Operation: reverted ── */}
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
      </div>
    </div>
  )
}
