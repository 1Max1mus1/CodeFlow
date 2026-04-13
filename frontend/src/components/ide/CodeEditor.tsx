import { useEffect, useRef } from 'react'
import MonacoEditor, { type OnMount } from '@monaco-editor/react'
import type { editor } from 'monaco-editor'
import type { ParsedProject } from '../../types'

interface CodeEditorProps {
  filePath: string | null
  content: string
  isLoading: boolean
  project: ParsedProject | null
  focusLine: number | null          // line to scroll to (from graph node selection)
  onSave: (content: string) => void
  onCursorChange: (line: number) => void  // tells parent what line the cursor is on
}

export function CodeEditor({
  filePath,
  content,
  isLoading,
  project,
  focusLine,
  onSave,
  onCursorChange,
}: CodeEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null)

  // Scroll to focusLine whenever it changes
  useEffect(() => {
    if (focusLine != null && editorRef.current) {
      editorRef.current.revealLineInCenter(focusLine)
      editorRef.current.setPosition({ lineNumber: focusLine, column: 1 })
      editorRef.current.focus()
    }
  }, [focusLine])

  const handleMount: OnMount = (editorInstance) => {
    editorRef.current = editorInstance

    // Ctrl/Cmd+S to save
    editorInstance.addCommand(
      // Monaco.KeyMod.CtrlCmd | Monaco.KeyCode.KeyS
      2048 | 49,
      () => {
        const value = editorInstance.getValue()
        onSave(value)
      },
    )

    // Track cursor position for graph linking
    editorInstance.onDidChangeCursorPosition((e) => {
      onCursorChange(e.position.lineNumber)
    })

    // Scroll to focusLine on mount
    if (focusLine != null) {
      setTimeout(() => {
        editorInstance.revealLineInCenter(focusLine)
        editorInstance.setPosition({ lineNumber: focusLine, column: 1 })
      }, 100)
    }
  }

  // Decorate function ranges
  useEffect(() => {
    if (!editorRef.current || !project || !filePath) return
    const monaco = (window as unknown as { monaco?: typeof import('monaco-editor') }).monaco
    if (!monaco) return

    const fnsInFile = project.functions.filter((f) => f.filePath === filePath)
    const decorations = fnsInFile.map((fn) => ({
      range: new monaco.Range(fn.startLine, 1, fn.startLine, 1),
      options: {
        isWholeLine: false,
        glyphMarginClassName: 'fn-glyph',
        glyphMarginHoverMessage: { value: `fn ${fn.name}` },
      },
    }))
    editorRef.current.createDecorationsCollection(decorations)
  }, [project, filePath, content])

  if (!filePath) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-950 text-gray-600 text-sm">
        Select a file from the tree, or click a node in the Graph view to open its source.
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden bg-gray-950">
      {/* File tab bar */}
      <div className="flex items-center bg-gray-900 border-b border-gray-700 px-3 py-1.5 shrink-0">
        <span className="text-xs text-blue-300 font-mono">{filePath}</span>
        <span className="ml-auto text-xs text-gray-600">Ctrl+S to save</span>
      </div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center text-gray-500 text-sm animate-pulse">
          Loading file…
        </div>
      ) : (
        <MonacoEditor
          height="100%"
          language="python"
          value={content}
          theme="vs-dark"
          onMount={handleMount}
          options={{
            fontSize: 13,
            lineHeight: 20,
            fontFamily: '"Fira Code", "Cascadia Code", Consolas, monospace',
            fontLigatures: true,
            minimap: { enabled: true },
            scrollBeyondLastLine: false,
            wordWrap: 'off',
            renderWhitespace: 'selection',
            glyphMargin: true,
            folding: true,
            lineNumbers: 'on',
            automaticLayout: true,
          }}
        />
      )}
    </div>
  )
}
