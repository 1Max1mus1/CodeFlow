import { useAppStore } from '../store'
import {
  submitOperation,
  answerQuestion,
  applyOperation,
  revertOperation,
  rollbackOperation,
} from '../services/api'
import type { OperationType } from '../types'

export function useOperation() {
  const { activeOperation, setActiveOperation, setOperationError, pushOperationHistory, updateOperationHistory } = useAppStore()

  async function startOperation(
    sessionId: string,
    type: OperationType,
    targetNodeId: string,
    newNodeId: string | null,
  ) {
    setOperationError(null)
    const response = await submitOperation(sessionId, type, targetNodeId, newNodeId)
    setActiveOperation(response.operation)
    return response.operation
  }

  async function sendAnswer(questionId: string, answer: string) {
    // Read fresh from store every call to avoid stale closures when submitting
    // multiple answers sequentially from the form (each await causes a re-render).
    const currentOp = useAppStore.getState().activeOperation
    if (!currentOp) return

    setOperationError(null)
    const prevOp = currentOp
    // Optimistic: immediately show "generating" so the form hides and the
    // user sees feedback while the Moonshot API is in-flight (10–30s).
    setActiveOperation({ ...currentOp, status: 'generating' })

    try {
      const response = await answerQuestion(currentOp.id, questionId, answer)
      setActiveOperation(response.operation)
      return response.operation
    } catch (err) {
      setActiveOperation(prevOp)
      const raw = err instanceof Error ? err.message : 'Unknown error'
      if (raw.includes('404')) {
        setActiveOperation(null)
        setOperationError(
          'Operation not found — the backend may have restarted. Please reload your project and try again.',
        )
      } else {
        setOperationError(raw)
      }
    }
  }

  async function apply() {
    if (!activeOperation) return
    const response = await applyOperation(activeOperation.id)
    setActiveOperation(response.operation)
    pushOperationHistory(response.operation)
    return response
  }

  async function revert() {
    if (!activeOperation) return
    const updated = await revertOperation(activeOperation.id)
    setActiveOperation(updated)
    pushOperationHistory(updated)
  }

  async function rollback() {
    if (!activeOperation) return
    const response = await rollbackOperation(activeOperation.id)
    setActiveOperation(response.operation)
    pushOperationHistory(response.operation)
    return response
  }

  async function rollbackById(operationId: string) {
    const response = await rollbackOperation(operationId)
    updateOperationHistory(response.operation)
    return response
  }

  function clearOperation() {
    setActiveOperation(null)
    setOperationError(null)
  }

  return { activeOperation, startOperation, sendAnswer, apply, revert, rollback, rollbackById, clearOperation }
}
