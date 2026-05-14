import type {
  AthenaEvolutionPlan,
  AthenaAnalyzeChapterResult,
  AthenaChapterContext,
  AthenaConsistencyIssue,
  AthenaConsistencyIssueListResponse,
  AthenaImportSetupResult,
  AthenaOntology,
  AthenaOptimization,
  AthenaRetrievalDiagnostics,
  AthenaRetrievalIndexResult,
  AthenaRetrievalSearchResponse,
  AthenaSetupImportPreview,
  AthenaTimeline,
  BackgroundTaskResponse,
  ChapterContent,
  ChapterListResponse,
  ChapterRevision,
  ChapterRevisionDraftPayload,
  ChapterRevisionListResponse,
  ChapterRevisionPayload,
  ChatHistoryMessage,
  ChatRequest,
  ChatResponse,
  LongformMaintenanceDiagnostics,
  LongformMaintenanceRepairResult,
  MessageQuery,
  ModelCallTraceDetail,
  ModelCallTraceListParams,
  PaginatedWorldFactClaims,
  PaginatedModelCallTraces,
  PaginatedProposalBundles,
  ProposalBundleDetail,
  ProposalReview,
  ProposalReviewQueue,
  ProposalReviewRequest,
  ProposalRollbackRequest,
  ProposalSplitRequest,
  ResolveActionRequest,
  ResolveActionResponse,
  VersionListResponse,
  WorldFactClaim,
  WorldModelDashboard,
  WorldModelOverview,
  WorkspaceBootstrap,
} from './types'

const API_BASE = '/api/v1'

function messageQuery(params?: MessageQuery) {
  const query = new URLSearchParams()
  if (params?.limit !== undefined) query.set('limit', String(params.limit))
  if (params?.after_id) query.set('after_id', params.after_id)
  return query
}

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
  getWorkspaceBootstrap: (id: string) => request<WorkspaceBootstrap>(`/projects/${id}/workspace-bootstrap`),
  deleteProject: (id: string) => request(`/projects/${id}`, { method: 'DELETE' }),
  generateSetup: (id: string) => request(`/projects/${id}/athena/ontology/generate`, { method: 'POST' }),
  getSetup: (id: string) => request(`/projects/${id}/setup`),
  getWorldModelOverview: (id: string) => request<WorldModelOverview>(`/projects/${id}/world-model`),
  getWorldModelDashboard: (id: string) => request<WorldModelDashboard>(`/projects/${id}/world-model/dashboard`),
  listWorldFactClaims: (id: string, params?: { claim_status?: string; claim_layer?: string; subject_ref?: string; offset?: number; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.claim_status) query.set('claim_status', params.claim_status)
    if (params?.claim_layer) query.set('claim_layer', params.claim_layer)
    if (params?.subject_ref) query.set('subject_ref', params.subject_ref)
    if (params?.offset !== undefined) query.set('offset', String(params.offset))
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    const qs = query.toString()
    return request<PaginatedWorldFactClaims | WorldFactClaim[]>(`/projects/${id}/world-model/facts${qs ? `?${qs}` : ''}`)
  },
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
  getWorldProposalReviewQueue: (id: string) =>
    request<ProposalReviewQueue>(`/projects/${id}/world-model/proposal-review-queue`),
  getWorldProposalBundle: (id: string, bundleId: string, params?: { item_offset?: number; item_limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.item_offset !== undefined) query.set('item_offset', String(params.item_offset))
    if (params?.item_limit !== undefined) query.set('item_limit', String(params.item_limit))
    const qs = query.toString()
    return request<ProposalBundleDetail>(`/projects/${id}/world-model/proposal-bundles/${bundleId}${qs ? `?${qs}` : ''}`)
  },
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
  getAthenaOptimization: (id: string) =>
    request<AthenaOptimization>(`/projects/${id}/athena/optimization`),
  getAthenaEvolutionProposals: (id: string, params?: { offset?: number; limit?: number; bundle_status?: string; item_status?: string }) => {
    const query = new URLSearchParams()
    if (params?.offset !== undefined) query.set('offset', String(params.offset))
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    if (params?.bundle_status) query.set('bundle_status', params.bundle_status)
    if (params?.item_status) query.set('item_status', params.item_status)
    const qs = query.toString()
    return request<PaginatedProposalBundles>(`/projects/${id}/athena/evolution/proposals${qs ? `?${qs}` : ''}`)
  },
  getAthenaProposalDetail: (id: string, bundleId: string, params?: { item_offset?: number; item_limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.item_offset !== undefined) query.set('item_offset', String(params.item_offset))
    if (params?.item_limit !== undefined) query.set('item_limit', String(params.item_limit))
    const qs = query.toString()
    return request<ProposalBundleDetail>(`/projects/${id}/athena/evolution/proposals/${bundleId}${qs ? `?${qs}` : ''}`)
  },
  reviewAthenaProposalItem: (id: string, itemId: string, data: ProposalReviewRequest) =>
    request<ProposalReview>(`/projects/${id}/athena/evolution/proposals/${itemId}/review`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  splitAthenaProposalBundle: (id: string, bundleId: string, data: ProposalSplitRequest) =>
    request<ProposalBundleDetail>(`/projects/${id}/athena/evolution/proposals/${bundleId}/split`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  rollbackAthenaProposalReview: (id: string, reviewId: string, data: ProposalRollbackRequest) =>
    request<ProposalReview>(`/projects/${id}/athena/evolution/reviews/${reviewId}/rollback`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getAthenaSetupImportPreview: (id: string) =>
    request<AthenaSetupImportPreview>(`/projects/${id}/athena/ontology/import-setup/preview`),
  importAthenaSetup: (id: string) =>
    request<AthenaImportSetupResult>(`/projects/${id}/athena/ontology/import-setup`, { method: 'POST' }),
  analyzeAthenaChapter: (id: string, chapterIndex: number) =>
    request<AthenaAnalyzeChapterResult>(`/projects/${id}/athena/evolution/chapters/${chapterIndex}/analyze`, { method: 'POST' }),
  getAthenaChapterContext: (id: string, chapterIndex: number) =>
    request<AthenaChapterContext>(`/projects/${id}/athena/context/chapter/${chapterIndex}`),
  getAthenaRetrievalDiagnostics: (id: string) =>
    request<AthenaRetrievalDiagnostics>(`/projects/${id}/athena/retrieval/diagnostics`),
  getAthenaLongformMaintenanceDiagnostics: (id: string) =>
    request<LongformMaintenanceDiagnostics>(`/projects/${id}/athena/longform/maintenance/diagnostics`),
  repairAthenaLongformMaintenance: (id: string, params?: { repair_limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.repair_limit !== undefined) query.set('repair_limit', String(params.repair_limit))
    const qs = query.toString()
    return request<LongformMaintenanceRepairResult>(
      `/projects/${id}/athena/longform/maintenance/repair${qs ? `?${qs}` : ''}`,
      { method: 'POST' },
    )
  },
  searchAthenaRetrieval: (id: string, params: { q: string; limit?: number; source_type?: string; chapter_index?: number }) => {
    const query = new URLSearchParams()
    query.set('q', params.q)
    if (params.limit !== undefined) query.set('limit', String(params.limit))
    if (params.source_type) query.set('source_type', params.source_type)
    if (params.chapter_index !== undefined) query.set('chapter_index', String(params.chapter_index))
    return request<AthenaRetrievalSearchResponse>(`/projects/${id}/athena/retrieval/search?${query.toString()}`)
  },
  reindexAthenaRetrieval: (id: string) =>
    request<AthenaRetrievalIndexResult>(`/projects/${id}/athena/retrieval/reindex`, { method: 'POST' }),
  indexAthenaRetrievalChapter: (id: string, chapterIndex: number) =>
    request<AthenaRetrievalIndexResult>(`/projects/${id}/athena/retrieval/chapters/${chapterIndex}/index`, { method: 'POST' }),
  sendAthenaChat: (id: string, text: string) =>
    request<ChatResponse>(`/projects/${id}/athena/dialog/chat`, {
      method: 'POST',
      body: JSON.stringify({ project_id: id, input_type: 'text', text }),
    }),
  getAthenaMessages: (id: string, params?: MessageQuery) => {
    const query = messageQuery(params)
    const qs = query.toString()
    return request<ChatHistoryMessage[]>(`/projects/${id}/athena/dialog/messages${qs ? `?${qs}` : ''}`)
  },
  getAthenaSetup: (id: string) =>
    request(`/projects/${id}/athena/ontology/setup`),
  getAthenaCharacterGraph: (id: string) =>
    request(`/projects/${id}/athena/ontology/character-graph`),
  runAthenaConsistencyCheck: (id: string, chapterIndex: number, depth: string = 'l1') =>
    request(`/projects/${id}/athena/evolution/consistency/chapters/${chapterIndex}/check?depth=${depth}`, { method: 'POST' }),
  getConsistencyIssues: (id: string, params?: { offset?: number; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.offset !== undefined) query.set('offset', String(params.offset))
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    const qs = query.toString()
    return request<AthenaConsistencyIssueListResponse | AthenaConsistencyIssue[]>(`/projects/${id}/consistency/issues${qs ? `?${qs}` : ''}`)
  },
  generateChapter: (id: string, index: number) => request<ChapterContent>(`/projects/${id}/chapters/${index}/generate`, { method: 'POST' }),
  getChapter: (id: string, index: number) => request<ChapterContent>(`/projects/${id}/chapters/${index}`),
  listModelCallTraces: (id: string, params?: ModelCallTraceListParams) => {
    const query = new URLSearchParams()
    if (params?.trace_type) query.set('trace_type', params.trace_type)
    if (params?.chapter_index !== undefined) query.set('chapter_index', String(params.chapter_index))
    if (params?.dialog_id) query.set('dialog_id', params.dialog_id)
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    if (params?.offset !== undefined) query.set('offset', String(params.offset))
    const qs = query.toString()
    return request<PaginatedModelCallTraces>(`/projects/${id}/model-call-traces${qs ? `?${qs}` : ''}`)
  },
  getModelCallTrace: (id: string, traceId: string) =>
    request<ModelCallTraceDetail>(`/projects/${id}/model-call-traces/${traceId}`),
  getActiveRevision: (id: string, index: number) =>
    request<ChapterRevision | null>(`/projects/${id}/revisions/chapters/${index}/active`),
  updateRevisionDraft: (id: string, index: number, data: ChapterRevisionDraftPayload) =>
    request<ChapterRevision | null>(`/projects/${id}/revisions/chapters/${index}/draft`, { method: 'PUT', body: JSON.stringify(data) }),
  submitRevision: (id: string, data: ChapterRevisionPayload) =>
    request<ChapterRevision>(`/projects/${id}/revisions`, { method: 'POST', body: JSON.stringify(data) }),
  submitRevisionDraft: (id: string, revisionId: string) =>
    request<ChapterRevision>(`/projects/${id}/revisions/${revisionId}/submit`, { method: 'POST' }),
  listRevisions: (id: string, params?: { offset?: number; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.offset !== undefined) query.set('offset', String(params.offset))
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    const qs = query.toString()
    return request<ChapterRevisionListResponse>(`/projects/${id}/revisions${qs ? `?${qs}` : ''}`)
  },
  getRevision: (id: string, revisionId: string) => request<ChapterRevision>(`/projects/${id}/revisions/${revisionId}`),
  regenerateRevision: (id: string, revisionId: string) =>
    request<ChapterContent>(`/projects/${id}/revisions/${revisionId}/regenerate`, { method: 'POST' }),
  getConfig: () => request('/config'),
  updateConfig: (apiKey: string) => request('/config', { method: 'PUT', body: JSON.stringify({ api_key: apiKey }) }),
  generateStoryline: (id: string) => request(`/projects/${id}/athena/evolution/plan/generate?target=storyline`, { method: 'POST' }),
  getStoryline: (id: string) => request(`/projects/${id}/storyline`),
  generateOutline: (id: string) => request(`/projects/${id}/athena/evolution/plan/generate?target=outline`, { method: 'POST' }),
  getOutline: (id: string) => request(`/projects/${id}/outline`),
  getTopology: (id: string) => request(`/projects/${id}/athena/ontology/relations`),
  getDiagnosis: (id: string) => request(`/projects/${id}/state-diagnosis`),
  getMessages: (id: string, dialogType: string = 'hermes', params?: MessageQuery) => {
    const query = messageQuery(params)
    query.set('dialog_type', dialogType)
    return request<ChatHistoryMessage[]>(`/dialog/projects/${id}/messages?${query.toString()}`)
  },
  sendChat: (data: ChatRequest) => request<ChatResponse>('/dialog/chat', { method: 'POST', body: JSON.stringify(data) }),
  resolveAction: (data: ResolveActionRequest) => request<ResolveActionResponse>('/dialog/resolve-action', { method: 'POST', body: JSON.stringify(data) }),
  startWriting: (id: string) => request(`/projects/${id}/writing/start`, { method: 'POST' }),
  pauseWriting: (id: string) => request(`/projects/${id}/writing/pause`, { method: 'POST' }),
  resumeWriting: (id: string) => request(`/projects/${id}/writing/resume`, { method: 'POST' }),
  listVersions: (id: string, nodeType?: string, params?: { offset?: number; limit?: number }) => {
    const query = new URLSearchParams()
    if (nodeType) query.set('node_type', nodeType)
    if (params?.offset !== undefined) query.set('offset', String(params.offset))
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    const qs = query.toString()
    return request<VersionListResponse | any[]>(`/projects/${id}/versions${qs ? `?${qs}` : ''}`)
  },
  getVersion: (id: string, versionId: string) => request(`/projects/${id}/versions/${versionId}`),
  createVersion: (id: string, data: any) => request(`/projects/${id}/versions`, { method: 'POST', body: JSON.stringify(data) }),
  rollbackVersion: (id: string, versionId: string) => request(`/projects/${id}/versions/${versionId}/rollback`, { method: 'POST' }),
  deleteVersion: (id: string, versionId: string) => request(`/projects/${id}/versions/${versionId}`, { method: 'DELETE' }),
  exportProject: (id: string, data: any) => fetch(`/api/v1/projects/${id}/export`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }),
  listChapters: (id: string, params?: { offset?: number; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.offset !== undefined) query.set('offset', String(params.offset))
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    const qs = query.toString()
    return request<ChapterListResponse>(`/projects/${id}/chapters${qs ? `?${qs}` : ''}`)
  },
  getPreferences: (id: string) => request(`/projects/${id}/preferences`),
  updatePreferences: (id: string, data: any) => request(`/projects/${id}/preferences`, { method: 'PUT', body: JSON.stringify(data) }),
  resetPreferences: (id: string) => request(`/projects/${id}/preferences/reset`, { method: 'POST' }),
  deepCheck: (id: string, chapterIndex: number) => request(`/projects/${id}/consistency/chapters/${chapterIndex}/check?depth=l2`, { method: 'POST' }),
  getBackgroundTask: (taskId: string) => request<BackgroundTaskResponse>(`/background-tasks/${taskId}`),
}
