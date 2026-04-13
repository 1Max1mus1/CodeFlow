import { create } from 'zustand'
import type {
  ParsedProject,
  GraphSession,
  GraphView,
  Operation,
} from '../types'

export type AppView = 'graph' | 'ide'

interface AppState {
  project: ParsedProject | null
  session: GraphSession | null
  graphView: GraphView | null
  activeOperation: Operation | null
  operationError: string | null
  operationHistory: Operation[]
  activeView: AppView
  selectedNodeId: string | null
}

interface AppActions {
  setProject: (project: ParsedProject) => void
  setSession: (session: GraphSession) => void
  setGraphView: (view: GraphView) => void
  setActiveOperation: (operation: Operation | null) => void
  setOperationError: (error: string | null) => void
  pushOperationHistory: (op: Operation) => void
  updateOperationHistory: (op: Operation) => void
  setActiveView: (view: AppView) => void
  setSelectedNodeId: (id: string | null) => void
}

export const useAppStore = create<AppState & AppActions>((set) => ({
  project: null,
  session: null,
  graphView: null,
  activeOperation: null,
  operationError: null,
  operationHistory: [],
  activeView: 'graph',
  selectedNodeId: null,
  setProject: (project) => set({ project }),
  setSession: (session) => set({ session }),
  setGraphView: (graphView) => set({ graphView }),
  setActiveOperation: (activeOperation) => set({ activeOperation }),
  setOperationError: (operationError) => set({ operationError }),
  pushOperationHistory: (op) =>
    set((state) => ({
      operationHistory: [op, ...state.operationHistory].slice(0, 20),
    })),
  updateOperationHistory: (op) =>
    set((state) => ({
      operationHistory: state.operationHistory.map((o) => (o.id === op.id ? op : o)),
    })),
  setActiveView: (activeView) => set({ activeView }),
  setSelectedNodeId: (selectedNodeId) => set({ selectedNodeId }),
}))
