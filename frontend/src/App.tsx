import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type ReactFlowInstance,
  type NodeTypes,
  type EdgeTypes,
  type NodeMouseHandler,
  type EdgeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { FunctionNodeComponent } from './components/nodes/FunctionNode'
import { SchemaNodeComponent } from './components/nodes/SchemaNode'
import { ExternalAPINodeComponent } from './components/nodes/ExternalAPINode'
import { CallEdgeComponent } from './components/edges/CallEdge'
import { DataFlowEdgeComponent } from './components/edges/DataFlowEdge'
import { LeftSidebar } from './components/panels/LeftSidebar'
import { RightPanel } from './components/panels/RightPanel'
import { ImportAPIModal } from './components/panels/ImportAPIModal'
import { ContextMenu } from './components/panels/ContextMenu'
import { CanvasToolbar } from './components/panels/CanvasToolbar'
import { TopNav } from './components/nav/TopNav'
import { IDEView } from './components/ide/IDEView'
import { useOperation } from './hooks/useOperation'
import { useProject } from './hooks/useProject'
import { useSession } from './hooks/useSession'
import { useAppStore } from './store'
import { projectToFlow } from './utils/projectToFlow'
import { addExternalAPI } from './services/api'
import type { FieldInfo, Operation } from './types'

// ── Register custom node & edge types ────────────────────────────────────────

const nodeTypes: NodeTypes = {
  functionNode: FunctionNodeComponent,
  schemaNode: SchemaNodeComponent,
  externalApiNode: ExternalAPINodeComponent,
}

const edgeTypes: EdgeTypes = {
  callEdge: CallEdgeComponent,
  dataFlowEdge: DataFlowEdgeComponent,
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function nodeBounds(node: Node) {
  const w = (node as Node & { measured?: { width: number; height: number } }).measured?.width ?? 200
  const h = (node as Node & { measured?: { width: number; height: number } }).measured?.height ?? 120
  return { x1: node.position.x, y1: node.position.y, x2: node.position.x + w, y2: node.position.y + h }
}

function overlaps(a: Node, b: Node) {
  const ab = nodeBounds(a); const bb = nodeBounds(b)
  return ab.x1 < bb.x2 && ab.x2 > bb.x1 && ab.y1 < bb.y2 && ab.y2 > bb.y1
}

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const rfInstance = useRef<ReactFlowInstance | null>(null)
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [activeEntryPointId, setActiveEntryPointId] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  // ── Operation UI state ────────────────────────────────────────────────────
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [deleteConfirmNodeId, setDeleteConfirmNodeId] = useState<string | null>(null)
  const [rollbackConfirmOp, setRollbackConfirmOp] = useState<Operation | null>(null)
  const [showImportAPIModal, setShowImportAPIModal] = useState(false)

  // Context menu state
  const [contextMenu, setContextMenu] = useState<{
    x: number
    y: number
    nodeId: string
    nodeType: 'function' | 'schema' | 'external'
    nodeName: string
  } | null>(null)

  // Phase 5-2: drag ExternalAPINode onto FunctionNode → replace confirmation
  const [replaceDropCandidate, setReplaceDropCandidate] = useState<{
    apiNodeId: string
    targetFunctionId: string
    apiName: string
    fnName: string
  } | null>(null)

  // Phase 6: click call edge → insert new intermediate function
  const [insertEdge, setInsertEdge] = useState<{
    sourceId: string
    targetId: string
    sourceLabel: string
    targetLabel: string
  } | null>(null)

  const { project, loadProject } = useProject()
  const { session, graphView, startSession, saveNodePosition } = useSession()
  const { activeOperation, startOperation, sendAnswer, apply, revert, rollback, rollbackById, clearOperation } = useOperation()
  const { activeView, setActiveView, operationHistory, operationError } = useAppStore()

  // Keep refs for stale-closure-safe keyboard handler
  const selectedNodeIdRef = useRef(selectedNodeId)
  selectedNodeIdRef.current = selectedNodeId
  const sessionRef = useRef(session)
  sessionRef.current = session

  // ── Derive nodes/edges from project + graphView ───────────────────────────
  useEffect(() => {
    if (!project) return

    const rootFunctionId =
      activeEntryPointId != null
        ? (project.entryPoints.find((ep) => ep.id === activeEntryPointId)?.functionId ?? null)
        : null

    const { nodes: allNodes, edges: allEdges } = projectToFlow(project, { rootFunctionId })

    setNodes(allNodes)
    setEdges(allEdges)
  }, [project, graphView, activeEntryPointId, setNodes, setEdges])

  // Phase 5-5: add a red incompatibility edge when replace analysis finds missing fields
  useEffect(() => {
    const INCOMPAT_ID = '__incompat__'
    if (
      activeOperation?.type === 'replace' &&
      activeOperation.status === 'awaiting_user' &&
      activeOperation.newNodeId &&
      activeOperation.aiQuestions.some((q) => q.question.includes('missing from'))
    ) {
      const syntheticEdge: Edge = {
        id: INCOMPAT_ID,
        source: activeOperation.targetNodeId,
        target: activeOperation.newNodeId,
        type: 'dataFlowEdge',
        data: { isCompatible: false, dataType: 'schema mismatch' },
        animated: true,
      }
      setEdges((prev) => {
        if (prev.some((e) => e.id === INCOMPAT_ID)) return prev
        return [...prev, syntheticEdge]
      })
    } else {
      setEdges((prev) => prev.filter((e) => e.id !== INCOMPAT_ID))
    }
  }, [activeOperation, setEdges])

  // Keyboard listener: Delete key → confirm delete
  useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== 'Delete' && e.key !== 'Backspace') return
      const tag = (e.target as HTMLElement).tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA') return
      const nodeId = selectedNodeIdRef.current
      if (nodeId && sessionRef.current) setDeleteConfirmNodeId(nodeId)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [])

  // ── Handlers ─────────────────────────────────────────────────────────────

  async function handleLoadProject(rootPath: string) {
    setIsLoading(true)
    setLoadError(null)
    try {
      const loaded = await loadProject(rootPath)
      if (loaded.entryPoints.length > 0) {
        const firstEp = loaded.entryPoints[0]
        setActiveEntryPointId(firstEp.id)
        await startSession(loaded.id, firstEp.id)
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to load project')
    } finally {
      setIsLoading(false)
    }
  }

  async function handleSelectEntryPoint(entryPointId: string) {
    setActiveEntryPointId(entryPointId)
    if (!project) return
    // Focus graph on the entry point's function node
    const ep = project.entryPoints.find((e) => e.id === entryPointId)
    if (ep) {
      setTimeout(() => {
        rfInstance.current?.fitView({ nodes: [{ id: ep.functionId }], duration: 600, padding: 0.5 })
      }, 50)
    }
    try {
      await startSession(project.id, entryPointId)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to create session')
    }
  }

  async function confirmDelete(nodeId: string) {
    setDeleteConfirmNodeId(null)
    setSelectedNodeId(null)
    if (!session) return
    try {
      await startOperation(session.id, 'delete', nodeId, null)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to start delete operation')
    }
  }

  async function handleImportAPIConfirm(params: {
    name: string
    endpoint: string
    method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
    outputSchema: FieldInfo[]
    description: string | null
  }) {
    setShowImportAPIModal(false)
    if (!session || !project) return
    try {
      await addExternalAPI(session.id, {
        name: params.name,
        endpoint: params.endpoint,
        method: params.method,
        inputSchema: [],
        outputSchema: params.outputSchema,
        description: params.description,
      })
      await loadProject(project.rootPath)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to import API')
    }
  }

  async function handleReplace(targetFunctionId: string, apiNodeId: string) {
    if (!session) return
    try {
      await startOperation(session.id, 'replace', targetFunctionId, apiNodeId)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to start replace operation')
    }
  }

  // Phase 5-2: drag confirmation → replace
  async function confirmReplaceFromDrop() {
    if (!replaceDropCandidate || !session) return
    const { targetFunctionId, apiNodeId } = replaceDropCandidate
    setReplaceDropCandidate(null)
    try {
      await startOperation(session.id, 'replace', targetFunctionId, apiNodeId)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to start replace operation')
    }
  }

  // Phase 6: edge click → insert confirmation → add_insert
  async function confirmInsert() {
    if (!insertEdge || !session) return
    const { sourceId, targetId } = insertEdge
    setInsertEdge(null)
    try {
      await startOperation(session.id, 'add_insert', sourceId, targetId)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to start insert operation')
    }
  }

  async function handleAddBranch(targetFunctionId: string) {
    if (!session) return
    try {
      await startOperation(session.id, 'add_branch', targetFunctionId, null)
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to start add-branch operation')
    }
  }

  // After apply: re-parse the project from disk so the graph reflects AI-written changes.
  // This removes deleted nodes, updates modified functions, etc.
  async function handleApply() {
    await apply()
    if (!project) return
    try {
      const newProject = await loadProject(project.rootPath)
      // Keep the same entry point if it still exists, otherwise fall back to first
      const epId =
        newProject.entryPoints.find((ep) => ep.id === activeEntryPointId)?.id ??
        newProject.entryPoints[0]?.id
      if (epId) {
        setActiveEntryPointId(epId)
        await startSession(newProject.id, epId)
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to reload project after apply')
    }
  }

  // Undo applied file changes, then reload project to restore graph state
  async function handleRollback() {
    await rollback()
    if (!project) return
    try {
      const newProject = await loadProject(project.rootPath)
      const epId =
        newProject.entryPoints.find((ep) => ep.id === activeEntryPointId)?.id ??
        newProject.entryPoints[0]?.id
      if (epId) {
        setActiveEntryPointId(epId)
        await startSession(newProject.id, epId)
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to reload project after rollback')
    }
  }

  // Roll back a specific history operation, then reload the project
  async function handleRollbackById() {
    if (!rollbackConfirmOp || !project) return
    setRollbackConfirmOp(null)
    try {
      await rollbackById(rollbackConfirmOp.id)
      const newProject = await loadProject(project.rootPath)
      const epId =
        newProject.entryPoints.find((ep) => ep.id === activeEntryPointId)?.id ??
        newProject.entryPoints[0]?.id
      if (epId) {
        setActiveEntryPointId(epId)
        await startSession(newProject.id, epId)
      }
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : 'Failed to rollback operation')
    }
  }

  // Switch to IDE view and select the given node (for "handle manually" flow)
  function handleGoToCode(nodeId: string) {
    setSelectedNodeId(nodeId)
    setActiveView('ide')
  }

  // ── React Flow event handlers ─────────────────────────────────────────────

  const onNodeClick: NodeMouseHandler = useCallback((_event, node) => {
    setSelectedNodeId(node.id)
    setContextMenu(null)
    // Auto-dismiss terminal operations so the inspector can show the new node
    const currentOp = useAppStore.getState().activeOperation
    if (currentOp && (currentOp.status === 'applied' || currentOp.status === 'reverted')) {
      clearOperation()
    }
  }, [clearOperation])

  const onNodeDoubleClick: NodeMouseHandler = useCallback((_event, node) => {
    setSelectedNodeId(node.id)
    setContextMenu(null)
    setActiveView('ide')
  }, [setActiveView])

  const onNodeContextMenu: NodeMouseHandler = useCallback(
    (event, node) => {
      event.preventDefault()
      if (!session) return
      const nodeType = node.id.startsWith('external::')
        ? 'external'
        : project?.schemas.some((s) => s.id === node.id)
        ? 'schema'
        : 'function'
      const nodeName =
        nodeType === 'function'
          ? (project?.functions.find((f) => f.id === node.id)?.name ?? node.id)
          : nodeType === 'schema'
          ? (project?.schemas.find((s) => s.id === node.id)?.name ?? node.id)
          : (project?.externalApis.find((a) => a.id === node.id)?.name ?? node.id)
      setSelectedNodeId(node.id)
      setContextMenu({ x: event.clientX, y: event.clientY, nodeId: node.id, nodeType, nodeName })
    },
    [session, project],
  )

  const onNodeDragStop = useCallback(
    (_event: React.MouseEvent, node: Node) => {
      saveNodePosition(node.id, node.position)

      // Phase 5-2: detect ExternalAPINode dropped onto a FunctionNode
      if (!node.id.startsWith('external::')) return
      const overlapped = nodes.find(
        (n) =>
          n.id !== node.id &&
          project?.functions.some((fn) => fn.id === n.id) &&
          overlaps(node, n),
      )
      if (overlapped && session && project) {
        const apiNode = project.externalApis.find((a) => a.id === node.id)
        const fn = project.functions.find((f) => f.id === overlapped.id)
        setReplaceDropCandidate({
          apiNodeId: node.id,
          targetFunctionId: overlapped.id,
          apiName: apiNode?.name ?? node.id,
          fnName: fn?.name ?? overlapped.id,
        })
      }
    },
    [saveNodePosition, nodes, session, project],
  )

  // Phase 6: click a call edge to trigger add_insert
  const onEdgeClick: EdgeMouseHandler = useCallback(
    (_event, edge) => {
      if (!session || !project) return
      if (!edge.id.startsWith('call::')) return
      const sourceFn = project.functions.find((fn) => fn.id === edge.source)
      const targetFn = project.functions.find((fn) => fn.id === edge.target)
      if (!sourceFn || !targetFn) return
      setInsertEdge({
        sourceId: edge.source,
        targetId: edge.target,
        sourceLabel: sourceFn.name,
        targetLabel: targetFn.name,
      })
    },
    [session, project],
  )

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null)
    setContextMenu(null)
  }, [])

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col h-screen w-screen bg-gray-950 text-white overflow-hidden">

      {/* ── Top navigation bar ───────────────────────────────────────────── */}
      <TopNav
        projectName={project?.name ?? null}
        activeView={activeView}
        onViewChange={setActiveView}
        operationHistory={operationHistory}
        onRollbackClick={setRollbackConfirmOp}
      />

      {/* ── Main content area (below nav) ────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Left sidebar — always visible */}
        <LeftSidebar
          entryPoints={project?.entryPoints ?? []}
          activeEntryPointId={activeEntryPointId}
          onSelectEntryPoint={handleSelectEntryPoint}
          onLoadProject={handleLoadProject}
          onImportAPI={() => setShowImportAPIModal(true)}
          isLoading={isLoading}
          loadError={loadError}
          hasSession={session != null}
        />

        {/* ── Graph view ────────────────────────────────────────────────── */}
        {activeView === 'graph' && (
          <>
            <div className="flex-1 relative overflow-hidden">
              {!project && !isLoading && (
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                  <p className="text-gray-500 text-sm">
                    Enter a project path and click Load to visualise the call graph.
                  </p>
                </div>
              )}

              {project && (
                <CanvasToolbar
                  selectedNodeId={selectedNodeId}
                  project={project}
                  hasSession={session != null}
                  onDelete={(nodeId) => setDeleteConfirmNodeId(nodeId)}
                  onAddBranch={handleAddBranch}
                  onImportAPI={() => setShowImportAPIModal(true)}
                  onFitView={() => rfInstance.current?.fitView({ duration: 400 })}
                />
              )}

              <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onInit={(instance) => { rfInstance.current = instance }}
                onNodeClick={onNodeClick}
                onNodeDoubleClick={onNodeDoubleClick}
                onNodeContextMenu={onNodeContextMenu}
                onNodeDragStop={onNodeDragStop}
                onEdgeClick={onEdgeClick}
                onPaneClick={onPaneClick}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                nodesConnectable={false}
                colorMode="dark"
                fitView
                proOptions={{ hideAttribution: true }}
              >
                <Background color="#374151" gap={24} />
                <Controls
                  style={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: 8 }}
                  showInteractive={false}
                />
                <MiniMap
                  style={{ backgroundColor: '#111827', border: '1px solid #374151' }}
                  nodeColor={(n) => {
                    if (n.type === 'schemaNode') return '#7c3aed'
                    if (n.type === 'externalApiNode') return '#9333ea'
                    return '#3b82f6'
                  }}
                  maskColor="rgba(0,0,0,0.6)"
                />
              </ReactFlow>

              {/* Edge legend */}
              {project && (
                <div className="absolute bottom-28 left-3 z-10 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg px-3 py-2 pointer-events-none select-none">
                  <p className="text-gray-500 text-[10px] font-semibold uppercase tracking-wider mb-1.5">边类型</p>
                  <div className="flex flex-col gap-1">
                    <div className="flex items-center gap-2">
                      <svg width="32" height="10"><line x1="0" y1="5" x2="32" y2="5" stroke="#3b82f6" strokeWidth="2" markerEnd="url(#arr-blue)"/><defs><marker id="arr-blue" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto"><path d="M0,0 L4,2 L0,4 Z" fill="#3b82f6"/></marker></defs></svg>
                      <span className="text-gray-400 text-[10px]">函数调用</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <svg width="32" height="10"><line x1="0" y1="5" x2="32" y2="5" stroke="#f97316" strokeWidth="2" strokeDasharray="5 3" markerEnd="url(#arr-orange)"/><defs><marker id="arr-orange" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto"><path d="M0,0 L4,2 L0,4 Z" fill="#f97316"/></marker></defs></svg>
                      <span className="text-gray-400 text-[10px]">返回该 Schema</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <svg width="32" height="10"><line x1="0" y1="5" x2="32" y2="5" stroke="#a855f7" strokeWidth="2" markerEnd="url(#arr-purple)"/><defs><marker id="arr-purple" markerWidth="4" markerHeight="4" refX="3" refY="2" orient="auto"><path d="M0,0 L4,2 L0,4 Z" fill="#a855f7"/></marker></defs></svg>
                      <span className="text-gray-400 text-[10px]">参数引用 Schema</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Delete confirmation modal */}
              {deleteConfirmNodeId && (() => {
                const fn = project?.functions.find((f) => f.id === deleteConfirmNodeId)
                return (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
                    <div className="bg-gray-800 border border-gray-600 rounded-lg p-6 w-96 shadow-2xl">
                      <h3 className="text-white font-semibold mb-2">Delete Function?</h3>
                      <p className="text-gray-300 text-sm mb-1">
                        AI will analyse the call chain and ask how to handle affected callers.
                      </p>
                      <p className="text-blue-300 text-sm font-mono mb-4">
                        {fn?.name ?? deleteConfirmNodeId}
                        {fn?.filePath && <span className="text-gray-500 text-xs ml-2">({fn.filePath})</span>}
                      </p>
                      <div className="flex gap-3">
                        <button onClick={() => confirmDelete(deleteConfirmNodeId)}
                          className="flex-1 bg-red-700 hover:bg-red-600 text-white text-sm font-medium rounded px-4 py-2 transition-colors">
                          Confirm Delete
                        </button>
                        <button onClick={() => setDeleteConfirmNodeId(null)}
                          className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm font-medium rounded px-4 py-2 transition-colors">
                          Cancel
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })()}

              {/* Rollback-to-checkpoint confirmation */}
              {rollbackConfirmOp && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
                  <div className="bg-gray-800 border border-gray-600 rounded-lg p-6 w-96 shadow-2xl">
                    <h3 className="text-white font-semibold mb-1">回撤至此操作？</h3>
                    <p className="text-yellow-400 text-xs mb-3">⚠️ 此操作不可逆，回撤后该操作写入的文件改动将被还原。</p>
                    <div className="bg-gray-900 rounded px-3 py-2 mb-4 text-xs font-mono">
                      <span className="text-gray-400">操作类型：</span>
                      <span className="text-blue-300 ml-1">{rollbackConfirmOp.type}</span>
                      <span className="text-gray-500 ml-3">ID: {rollbackConfirmOp.id.slice(0, 8)}…</span>
                    </div>
                    <div className="flex gap-3">
                      <button
                        onClick={handleRollbackById}
                        className="flex-1 bg-orange-700 hover:bg-orange-600 text-white text-sm font-medium rounded px-4 py-2 transition-colors"
                      >
                        确认回撤
                      </button>
                      <button
                        onClick={() => setRollbackConfirmOp(null)}
                        className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm font-medium rounded px-4 py-2 transition-colors"
                      >
                        取消
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Drag-replace confirmation */}
              {replaceDropCandidate && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
                  <div className="bg-gray-800 border border-gray-600 rounded-lg p-6 w-96 shadow-2xl">
                    <h3 className="text-white font-semibold mb-2">Replace with this API?</h3>
                    <p className="text-gray-400 text-xs mb-4">
                      <span className="text-purple-300">{replaceDropCandidate.apiName}</span>{' → '}
                      <span className="text-blue-300">{replaceDropCandidate.fnName}</span>
                    </p>
                    <div className="flex gap-3">
                      <button onClick={confirmReplaceFromDrop}
                        className="flex-1 bg-purple-700 hover:bg-purple-600 text-white text-sm font-medium rounded px-4 py-2 transition-colors">
                        Replace
                      </button>
                      <button onClick={() => setReplaceDropCandidate(null)}
                        className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm font-medium rounded px-4 py-2 transition-colors">
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* Edge-click insert confirmation */}
              {insertEdge && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
                  <div className="bg-gray-800 border border-gray-600 rounded-lg p-6 w-96 shadow-2xl">
                    <h3 className="text-white font-semibold mb-2">Insert New Function?</h3>
                    <p className="text-gray-400 text-xs mb-4 font-mono">
                      <span className="text-blue-300">{insertEdge.sourceLabel}</span>
                      {' → '}<span className="text-green-300">[new function]</span>{' → '}
                      <span className="text-blue-300">{insertEdge.targetLabel}</span>
                    </p>
                    <div className="flex gap-3">
                      <button onClick={confirmInsert}
                        className="flex-1 bg-green-700 hover:bg-green-600 text-white text-sm font-medium rounded px-4 py-2 transition-colors">
                        Insert
                      </button>
                      <button onClick={() => setInsertEdge(null)}
                        className="flex-1 bg-gray-700 hover:bg-gray-600 text-gray-200 text-sm font-medium rounded px-4 py-2 transition-colors">
                        Cancel
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Context menu */}
            {contextMenu && (
              <ContextMenu
                x={contextMenu.x}
                y={contextMenu.y}
                nodeId={contextMenu.nodeId}
                nodeType={contextMenu.nodeType}
                nodeName={contextMenu.nodeName}
                onDelete={() => setDeleteConfirmNodeId(contextMenu.nodeId)}
                onAddBranch={() => handleAddBranch(contextMenu.nodeId)}
                onClose={() => setContextMenu(null)}
              />
            )}

            {/* Right panel (AI assistant) */}
            <RightPanel
              operation={activeOperation}
              operationError={operationError}
              selectedNodeId={selectedNodeId}
              project={project ?? null}
              sessionId={session?.id ?? null}
              onAnswer={async (qId, answer) => { await sendAnswer(qId, answer) }}
              onApply={handleApply}
              onRevert={() => revert()}
              onReplace={handleReplace}
              onAddBranch={handleAddBranch}
              onDelete={(nodeId) => setDeleteConfirmNodeId(nodeId)}
              onGoToCode={handleGoToCode}
              onRollback={handleRollback}
              onOpenInIDE={handleGoToCode}
              onClearOperation={clearOperation}
            />
          </>
        )}

        {/* ── IDE view ──────────────────────────────────────────────────── */}
        {activeView === 'ide' && project && (
          <IDEView
            project={project}
            activeOperation={activeOperation}
            sessionId={session?.id ?? null}
            linkedNodeId={selectedNodeId}
            onNodeFocus={(nodeId) => setSelectedNodeId(nodeId)}
            onApply={handleApply}
            onRevert={() => revert()}
          />
        )}
        {activeView === 'ide' && !project && (
          <div className="flex-1 flex items-center justify-center text-gray-500 text-sm">
            Load a project first from the sidebar.
          </div>
        )}

      </div>

      {/* Import External API modal (global) */}
      {showImportAPIModal && (
        <ImportAPIModal
          onConfirm={handleImportAPIConfirm}
          onCancel={() => setShowImportAPIModal(false)}
        />
      )}
    </div>
  )
}
