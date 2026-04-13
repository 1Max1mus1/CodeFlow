import { useAppStore } from '../store'
import { createSession, updateNodePosition } from '../services/api'
import type { NodePosition } from '../types'

export function useSession() {
  const { session, graphView, setSession, setGraphView } = useAppStore()

  async function startSession(projectId: string, entryPointId: string) {
    const response = await createSession(projectId, entryPointId)
    setSession(response.session)
    setGraphView(response.graphView)
    return response
  }

  async function saveNodePosition(nodeId: string, position: NodePosition) {
    if (!session) return
    const updated = await updateNodePosition(session.id, nodeId, position)
    setSession(updated)
  }

  return { session, graphView, startSession, saveNodePosition }
}
