import { useState, useRef, useEffect, useCallback } from 'react'
import type { Operation, ParsedProject } from '../../types'
import { IDEChatPanel } from './IDEChatPanel'

type PanelTab = 'chat' | 'diff'

interface IDERightPanelProps {
  operation: Operation | null
  sessionId: string | null
  selectedNodeId: string | null
  project: ParsedProject | null
  onApply: () => void
  onRevert: () => void
}

export function IDERightPanel({
  operation,
  sessionId,
  selectedNodeId,
  project,
  onApply,
  onRevert,
}: IDERightPanelProps) {
  const [tab, setTab] = useState<PanelTab>('chat')

  // ── Resizable width ───────────────────────────────────────────────────────
  const [width, setWidth] = useState(320)
  const isDragging = useRef(false)
  const dragStartX = useRef(0)
  const dragStartWidth = useRef(320)

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
      const next = Math.max(240, Math.min(600, dragStartWidth.current + delta))
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

  const diffs = operation?.generatedDiffs ?? []
  const hasChanges = diffs.some((d) => d.changes.length > 0)

  const selectedNode = selectedNodeId
    ? (project?.functions.find((f) => f.id === selectedNodeId)
        ?? project?.schemas.find((s) => s.id === selectedNodeId)
        ?? null)
    : null

  const contextNodeName =
    selectedNode && 'params' in selectedNode ? selectedNode.name
    : selectedNode && 'fields' in selectedNode ? selectedNode.name
    : null

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

      {/* ── Tab bar ── */}
      <div className="px-3 py-2 border-b border-gray-700 flex items-center gap-1 shrink-0">
        <button
          onClick={() => setTab('chat')}
          className={`flex-1 text-xs px-2.5 py-1.5 rounded font-semibold transition-colors border-b-2 ${
            tab === 'chat'
              ? 'bg-gray-800 text-white border-blue-500'
              : 'text-gray-500 border-transparent hover:text-gray-300 hover:bg-gray-800/50'
          }`}
        >
          ✨ AI Chat
        </button>
        <button
          onClick={() => setTab('diff')}
          className={`flex-1 text-xs px-2.5 py-1.5 rounded font-semibold transition-colors relative border-b-2 ${
            tab === 'diff'
              ? 'bg-gray-800 text-white border-blue-500'
              : 'text-gray-500 border-transparent hover:text-gray-300 hover:bg-gray-800/50'
          }`}
        >
          Diff
          {operation?.status === 'ready' && (
            <span className="absolute top-0.5 right-0.5 w-1.5 h-1.5 bg-green-500 rounded-full" />
          )}
        </button>

        {/* Operation status badge — only on diff tab */}
        {operation && tab === 'diff' && (
          <span className={`ml-auto shrink-0 text-xs px-2 py-0.5 rounded-full ${
            operation.status === 'ready'   ? 'bg-green-900 text-green-300' :
            operation.status === 'applied' ? 'bg-blue-900 text-blue-300' :
            'bg-gray-700 text-gray-400'
          }`}>
            {operation.status}
          </span>
        )}
      </div>

      {/* ── Panel content ── */}
      <div className="flex-1 overflow-hidden flex flex-col">
        {tab === 'chat' ? (
          <IDEChatPanel
            sessionId={sessionId}
            contextNodeId={selectedNodeId}
            contextNodeName={contextNodeName}
          />
        ) : (
          /* ── Diff tab ── */
          <>
            <div className="flex-1 overflow-y-auto">
              {!operation ? (
                <div className="p-4 text-xs text-gray-600">
                  No active operation. Use the Graph view to run an AI operation, then switch here to review the diff.
                </div>
              ) : operation.status === 'awaiting_user' || operation.status === 'analyzing' || operation.status === 'generating' ? (
                <div className="p-4 text-xs text-gray-400 animate-pulse">
                  Waiting for AI… Switch to Graph view to answer questions.
                </div>
              ) : diffs.length === 0 ? (
                <div className="p-4 text-xs text-gray-500">
                  No code changes generated for this operation.
                </div>
              ) : !hasChanges ? (
                <div className="p-4 text-xs text-gray-500">
                  Generated file is identical to original — no diff to show.
                </div>
              ) : (
                <div className="p-3 space-y-4">
                  {diffs.map((diff) => (
                    <div key={diff.filePath}>
                      <div className="text-xs font-mono text-gray-400 mb-2 flex items-center justify-between">
                        <span>📄 {diff.filePath}</span>
                        <span className="text-gray-600">
                          +{diff.changes.filter(c => c.changeType === 'add').length}
                          {' '}-{diff.changes.filter(c => c.changeType === 'remove').length}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 gap-1">
                        <div>
                          <div className="text-xs text-red-400 font-semibold mb-1 px-1">Before</div>
                          <div className="bg-gray-950 rounded text-xs font-mono overflow-x-auto">
                            {diff.changes.map((c, i) => (
                              c.changeType !== 'add' && (
                                <div key={i} className={`px-2 py-0.5 ${
                                  c.changeType === 'remove' ? 'bg-red-950 text-red-300' : 'bg-yellow-950 text-yellow-300'
                                }`}>
                                  <span className="text-gray-600 mr-1 select-none text-right inline-block w-5">{c.lineNumber}</span>
                                  <span className="text-red-500 mr-1 select-none">-</span>
                                  {c.oldLine}
                                </div>
                              )
                            ))}
                          </div>
                        </div>

                        <div>
                          <div className="text-xs text-green-400 font-semibold mb-1 px-1">After</div>
                          <div className="bg-gray-950 rounded text-xs font-mono overflow-x-auto">
                            {diff.changes.map((c, i) => (
                              c.changeType !== 'remove' && (
                                <div key={i} className={`px-2 py-0.5 ${
                                  c.changeType === 'add' ? 'bg-green-950 text-green-300' : 'bg-yellow-950 text-yellow-300'
                                }`}>
                                  <span className="text-gray-600 mr-1 select-none text-right inline-block w-5">{c.lineNumber}</span>
                                  <span className="text-green-500 mr-1 select-none">+</span>
                                  {c.newLine}
                                </div>
                              )
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {operation?.status === 'ready' && (
              <div className="flex gap-2 p-3 border-t border-gray-700 shrink-0">
                <button onClick={onApply}
                  className="flex-1 bg-green-700 hover:bg-green-600 text-white text-xs font-semibold py-2 rounded transition-colors">
                  Apply Changes
                </button>
                <button onClick={onRevert}
                  className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-200 text-xs font-semibold py-2 rounded transition-colors">
                  Discard
                </button>
              </div>
            )}

            {operation?.status === 'applied' && (
              <div className="p-3 border-t border-gray-700 text-xs text-green-400 font-semibold shrink-0">
                ✓ Changes applied to disk
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
