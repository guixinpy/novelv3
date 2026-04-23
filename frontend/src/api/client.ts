import type {
  AthenaEvolutionPlan,
  AthenaOntology,
  AthenaTimeline,
  BackgroundTaskResponse,
  ChatHistoryMessage,
  ChatRequest,
  ChatResponse,
  PaginatedProposalBundles,
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
  generateSetup: (id: string) => request(`/projects/${id}/athena/ontology/generate`, { method: 'POST' }),
  getSetup: (id: string) => request(`/projects/${id}/setup`),
  getWorldModelOverview: (id: string) => request<WorldModelOverview>(`/projects/${id}/world-model`),
  listWorldProposalBundles: (id: string, params?: { offset?: number; limit?: number; bundle_status?: string; item_status?: string; profile_version?: number }) => {
    const query = new URLSearchParams()
    if (params?.offset !== undefined) query.set('offset', String(params.offset))
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    if (params?.bundle_status) query.set('bundle_status', params.bundle_status)
    if (params?.item_status) query.set('item_status', params.item_status)
    if (params?.profile_version !== undefined) query.set('profile_version', String(params.profile_version))
    const qs = query.toString()
    return request<PaginatedProposalBundles>(`/projects/${id}/world-model/proposal-bundles${qs ? `?${qs}` : ''}`)
  },
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
  getSubjectKnowledge: (id: string, subjectRef: string) =>
    request<WorldModelOverview>(`/projects/${id}/world-model/subject-knowledge?subject_ref=${encodeURIComponent(subjectRef)}`),
  getChapterSnapshot: (id: string, chapterIndex: number) =>
    request<WorldModelOverview>(`/projects/${id}/world-model/snapshot?chapter_index=${chapterIndex}`),
  getAthenaOntology: (id: string) =>
    request<AthenaOntology>(`/projects/${id}/athena/ontology`),
  getAthenaState: (id: string) =>
    request<WorldModelOverview>(`/projects/${id}/athena/state`),
  getAthenaTimeline: (id: string) =>
    request<AthenaTimeline>(`/projects/${id}/athena/state/timeline`),
  getAthenaEvolutionPlan: (id: string) =>
    request<AthenaEvolutionPlan>(`/projects/${id}/athena/evolution/plan`),
  getAthenaEvolutionProposals: (id: string, params?: { offset?: number; limit?: number; bundle_status?: string }) => {
    const query = new URLSearchParams()
    if (params?.offset !== undefined) query.set('offset', String(params.offset))
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    if (params?.bundle_status) query.set('bundle_status', params.bundle_status)
    const qs = query.toString()
    return request<PaginatedProposalBundles>(`/projects/${id}/athena/evolution/proposals${qs ? `?${qs}` : ''}`)
  },
  sendAthenaChat: (id: string, text: string) =>
    request<ChatResponse>(`/projects/${id}/athena/dialog/chat`, {
      method: 'POST',
      body: JSON.stringify({ project_id: id, input_type: 'text', text }),
    }),
  getAthenaMessages: (id: string) =>
    request<ChatHistoryMessage[]>(`/projects/${id}/athena/dialog/messages`),
  generateChapter: (id: string, index: number) => request(`/projects/${id}/chapters/${index}/generate`, { method: 'POST' }),
  getChapter: (id: string, index: number) => request(`/projects/${id}/chapters/${index}`),
  getConfig: () => request('/config'),
  updateConfig: (apiKey: string) => request('/config', { method: 'PUT', body: JSON.stringify({ api_key: apiKey }) }),
  generateStoryline: (id: string) => request(`/projects/${id}/athena/evolution/plan/generate?target=storyline`, { method: 'POST' }),
  getStoryline: (id: string) => request(`/projects/${id}/storyline`),
  generateOutline: (id: string) => request(`/projects/${id}/athena/evolution/plan/generate?target=outline`, { method: 'POST' }),
  getOutline: (id: string) => request(`/projects/${id}/outline`),
  getTopology: (id: string) => request(`/projects/${id}/athena/ontology/relations`),
  getDiagnosis: (id: string) => request(`/projects/${id}/state-diagnosis`),
  getMessages: (id: string, dialogType: string = 'hermes') => request<ChatHistoryMessage[]>(`/dialog/projects/${id}/messages?dialog_type=${dialogType}`),
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
