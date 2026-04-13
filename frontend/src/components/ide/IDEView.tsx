import { useState, useEffect, useCallback } from 'react'
import type { Operation, ParsedProject } from '../../types'
import { readProjectFile, writeProjectFile } from '../../services/api'
import { FileTree } from './FileTree'
import { CodeEditor } from './CodeEditor'
import { IDERightPanel } from './IDERightPanel'

interface IDEViewProps {
  project: ParsedProject
  activeOperation: Operation | null
  sessionId: string | null
  /** Function node selected in graph view — we open its file automatically */
  linkedNodeId: string | null
  /** Tell parent which node the IDE is now focused on (code → graph linking) */
  onNodeFocus: (nodeId: string | null) => void
  onApply: () => void
  onRevert: () => void
}

export function IDEView({
  project,
  activeOperation,
  sessionId,
  linkedNodeId,
  onNodeFocus,
  onApply,
  onRevert,
}: IDEViewProps) {
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [focusLine, setFocusLine] = useState<number | null>(null)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle')

  // ── Open the file of the linked graph node ─────────────────────────────────
  useEffect(() => {
    if (!linkedNodeId) return
    const fn = project.functions.find((f) => f.id === linkedNodeId)
    if (!fn) return
    if (fn.filePath !== selectedFile) {
      loadFile(fn.filePath)
    }
    setFocusLine(fn.startLine)
  }, [linkedNodeId]) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadFile(filePath: string) {
    setIsLoading(true)
    setSelectedFile(filePath)
    setFocusLine(null)
    try {
      const result = await readProjectFile(project.id, filePath)
      setFileContent(result.content)
    } catch {
      setFileContent(`// Error loading ${filePath}`)
    } finally {
      setIsLoading(false)
    }
  }

  async function handleSave(content: string) {
    if (!selectedFile) return
    setSaveStatus('saving')
    try {
      await writeProjectFile(project.id, selectedFile, content)
      setFileContent(content)
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 2000)
    } catch {
      setSaveStatus('idle')
    }
  }

  // ── IDE → graph: cursor position → node id ────────────────────────────────
  const handleCursorChange = useCallback(
    (line: number) => {
      if (!selectedFile) return
      // Find function whose range contains this line
      const fn = project.functions.find(
        (f) => f.filePath === selectedFile && line >= f.startLine && line <= f.endLine,
      )
      onNodeFocus(fn?.id ?? null)
    },
    [project, selectedFile, onNodeFocus],
  )

  return (
    <div className="flex flex-1 overflow-hidden h-full">
      {/* Left: file tree */}
      <FileTree
        project={project}
        selectedFile={selectedFile}
        onSelectFile={(fp) => {
          loadFile(fp)
          setFocusLine(null)
        }}
      />

      {/* Center: Monaco editor */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {saveStatus === 'saved' && (
          <div className="absolute top-2 right-4 z-10 bg-green-800 text-green-200 text-xs px-3 py-1 rounded shadow">
            ✓ Saved
          </div>
        )}
        {saveStatus === 'saving' && (
          <div className="absolute top-2 right-4 z-10 bg-gray-700 text-gray-300 text-xs px-3 py-1 rounded shadow animate-pulse">
            Saving…
          </div>
        )}
        <CodeEditor
          filePath={selectedFile}
          content={fileContent}
          isLoading={isLoading}
          project={project}
          focusLine={focusLine}
          onSave={handleSave}
          onCursorChange={handleCursorChange}
        />
      </div>

      {/* Right: tabbed panel (AI Chat + Diff) */}
      <IDERightPanel
        operation={activeOperation}
        sessionId={sessionId}
        selectedNodeId={linkedNodeId}
        project={project}
        onApply={onApply}
        onRevert={onRevert}
      />
    </div>
  )
}
