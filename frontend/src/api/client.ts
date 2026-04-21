import type {
  BackgroundTaskResponse,
  ChatHistoryMessage,
  ChatRequest,
  ChatResponse,
  ProposalBundle,
  ProposalBundleDetail,
  ProposalReview,
  ProposalReviewRequest,
  ProposalRollbackRequest,
  ProposalSplitRequest,
  ResolveActionRequest,
  ResolveActionResponse,
  WorldModelOverview,
} from './types'

const API_BASE = '/api/v1'

async function request<T = any>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json() as Promise<T>
}

export const api = {
  listProjects: () => request('/projects'),
  createProject: (data: any) => request('/projects', { method: 'POST', body: JSON.stringify(data) }),
  getProject: (id: string) => request(`/projects/${id}`),
  deleteProject: (id: string) => request(`/projects/${id}`, { method: 'DELETE' }),
  generateSetup: (id: string) => request(`/projects/${id}/setup/generate`, { method: 'POST' }),
  getSetup: (id: string) => request(`/projects/${id}/setup`),
  getWorldModelOverview: (id: string) => request<WorldModelOverview>(`/projects/${id}/world-model`),
  listWorldProposalBundles: (id: string) => request<ProposalBundle[]>(`/projects/${id}/world-model/proposal-bundles`),
  getWorldProposalBundle: (id: string, bundleId: string) => request<ProposalBundleDetail>(`/projects/${id}/world-model/proposal-bundles/${bundleId}`),
  reviewWorldProposalItem: (id: string, itemId: string, data: ProposalReviewRequest) =>
    request<ProposalReview>(`/projects/${id}/world-model/proposal-items/${itemId}/review`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  splitWorldProposalBundle: (id: string, bundleId: string, data: ProposalSplitRequest) =>
    request<ProposalBundleDetail>(`/projects/${id}/world-model/proposal-bundles/${bundleId}/split`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  rollbackWorldProposalReview: (id: string, reviewId: string, data: ProposalRollbackRequest) =>
    request<ProposalReview>(`/projects/${id}/world-model/reviews/${reviewId}/rollback`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
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
  getMessages: (id: string) => request<ChatHistoryMessage[]>(`/dialog/projects/${id}/messages`),
  sendChat: (data: ChatRequest) => request<ChatResponse>('/dialog/chat', { method: 'POST', body: JSON.stringify(data) }),
  resolveAction: (data: ResolveActionRequest) => request<ResolveActionResponse>('/dialog/resolve-action', { method: 'POST', body: JSON.stringify(data) }),
  startWriting: (id: string) => request(`/projects/${id}/writing/start`, { method: 'POST' }),
  pauseWriting: (id: string) => request(`/projects/${id}/writing/pause`, { method: 'POST' }),
  resumeWriting: (id: string) => request(`/projects/${id}/writing/resume`, { method: 'POST' }),
  listVersions: (id: string, nodeType?: string) => request(`/projects/${id}/versions${nodeType ? `?node_type=${nodeType}` : ''}`),
  getVersion: (id: string, versionId: string) => request(`/projects/${id}/versions/${versionId}`),
  createVersion: (id: string, data: any) => request(`/projects/${id}/versions`, { method: 'POST', body: JSON.stringify(data) }),
  rollbackVersion: (id: string, versionId: string) => request(`/projects/${id}/versions/${versionId}/rollback`, { method: 'POST' }),
  deleteVersion: (id: string, versionId: string) => request(`/projects/${id}/versions/${versionId}`, { method: 'DELETE' }),
  exportProject: (id: string, data: any) => fetch(`/api/v1/projects/${id}/export`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  listChapters: (id: string) => request(`/projects/${id}/chapters`),
  getPreferences: (id: string) => request(`/projects/${id}/preferences`),
  updatePreferences: (id: string, data: any) => request(`/projects/${id}/preferences`, { method: 'PUT', body: JSON.stringify(data) }),
  resetPreferences: (id: string) => request(`/projects/${id}/preferences/reset`, { method: 'POST' }),
  deepCheck: (id: string, chapterIndex: number) => request(`/projects/${id}/consistency/chapters/${chapterIndex}/check?depth=l2`, { method: 'POST' }),
  getBackgroundTask: (taskId: string) => request<BackgroundTaskResponse>(`/background-tasks/${taskId}`),
}
