import { useAppStore } from '../store'
import { parseProject } from '../services/api'

export function useProject() {
  const { project, setProject } = useAppStore()

  async function loadProject(rootPath: string) {
    const response = await parseProject(rootPath)
    setProject(response.project)
    return response.project
  }

  return { project, loadProject }
}
