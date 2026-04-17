const API_BASE = '/api/v1'

async function request(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  listProjects: () => request('/projects'),
  createProject: (data: any) => request('/projects', { method: 'POST', body: JSON.stringify(data) }),
  getProject: (id: string) => request(`/projects/${id}`),
  deleteProject: (id: string) => request(`/projects/${id}`, { method: 'DELETE' }),
  generateSetup: (id: string) => request(`/projects/${id}/setup/generate`, { method: 'POST' }),
  getSetup: (id: string) => request(`/projects/${id}/setup`),
  generateChapter: (id: string, index: number) => request(`/projects/${id}/chapters/${index}/generate`, { method: 'POST' }),
  getChapter: (id: string, index: number) => request(`/projects/${id}/chapters/${index}`),
  getConfig: () => request('/config'),
  updateConfig: (apiKey: string) => request('/config', { method: 'PUT', body: JSON.stringify({ api_key: apiKey }) }),
  generateStoryline: (id: string) => request(`/projects/${id}/storyline/generate`, { method: 'POST' }),
  getStoryline: (id: string) => request(`/projects/${id}/storyline`),
  generateOutline: (id: string) => request(`/projects/${id}/outline/generate`, { method: 'POST' }),
  getOutline: (id: string) => request(`/projects/${id}/outline`),
  getTopology: (id: string) => request(`/projects/${id}/topology`),
  getDiagnosis: (id: string) => request(`/projects/${id}/state-diagnosis`),
  getMessages: (id: string) => request(`/dialog/projects/${id}/messages`),
  sendChat: (data: any) => request('/dialog/chat', { method: 'POST', body: JSON.stringify(data) }),
  resolveAction: (data: any) => request('/dialog/resolve-action', { method: 'POST', body: JSON.stringify(data) }),
  startWriting: (id: string) => request(`/projects/${id}/writing/start`, { method: 'POST' }),
  pauseWriting: (id: string) => request(`/projects/${id}/writing/pause`, { method: 'POST' }),
  resumeWriting: (id: string) => request(`/projects/${id}/writing/resume`, { method: 'POST' }),
}
