import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Project } from '../api/types'

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchProjects = useCallback(async () => {
    try {
      const data = await api.getProjects()
      setProjects(data)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load projects')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const addProject = useCallback(async (name: string, path: string) => {
    const project = await api.addProject(name, path)
    setProjects((prev) => [...prev, project])
    return project
  }, [])

  const removeProject = useCallback(async (id: number) => {
    await api.deleteProject(id)
    setProjects((prev) => prev.filter((p) => p.id !== id))
  }, [])

  return { projects, loading, error, addProject, removeProject, refresh: fetchProjects }
}
