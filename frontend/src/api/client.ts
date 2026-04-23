import type { AppConfig, ModelsResponse, Project, Review, ReviewsResponse, StatusResponse } from './types'

const BASE = ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  // Projects
  getProjects: () => request<Project[]>('/api/projects'),
  addProject: (name: string, path: string) =>
    request<Project>('/api/projects', { method: 'POST', body: JSON.stringify({ name, path }) }),
  deleteProject: (id: number) =>
    request<void>(`/api/projects/${id}`, { method: 'DELETE' }),

  // Reviews
  getReviews: (params?: { project_id?: number; severity?: string; search?: string; limit?: number; offset?: number }) => {
    const q = new URLSearchParams()
    if (params?.project_id != null) q.set('project_id', String(params.project_id))
    if (params?.severity) q.set('severity', params.severity)
    if (params?.search) q.set('search', params.search)
    if (params?.limit != null) q.set('limit', String(params.limit))
    if (params?.offset != null) q.set('offset', String(params.offset))
    return request<ReviewsResponse>(`/api/reviews?${q}`)
  },
  getReview: (id: string) => request<Review>(`/api/reviews/${id}`),
  deleteReview: (id: string) => request<void>(`/api/reviews/${id}`, { method: 'DELETE' }),
  exportReview: (id: string) => fetch(`/api/reviews/${id}/export`),
  triggerReview: (project_id: number, relative_path: string) =>
    request<{ queued: boolean; path: string }>('/api/reviews/trigger', {
      method: 'POST',
      body: JSON.stringify({ project_id, relative_path }),
    }),

  // Status & models
  getStatus: () => request<StatusResponse>('/api/status'),
  getModels: () => request<ModelsResponse>('/api/models'),
  clearQueue: () => request<{ removed: number }>('/api/queue', { method: 'DELETE' }),

  // Config
  getConfig: () => request<AppConfig>('/api/config'),
  updateConfig: (patch: Partial<AppConfig>) =>
    request<AppConfig>('/api/config', { method: 'POST', body: JSON.stringify(patch) }),
}
