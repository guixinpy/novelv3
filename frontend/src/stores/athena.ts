import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import { useRequestCacheStore } from './requestCache'
import { useWorldModelStore } from './worldModel'
import { createAthenaProposalActions } from './athenaModules/proposals'
import { createAthenaRetrievalActions } from './athenaModules/retrieval'
import { toErrorMessage } from './athenaModules/errors'
import type {
  AthenaEvolutionPlan,
  AthenaEvolutionPlanQuery,
  AthenaConsistencyIssue,
  AthenaConsistencyIssueListResponse,
  AthenaAnalyzeChapterResult,
  AthenaOntology,
  AthenaOptimization,
  AthenaRetrievalDiagnostics,
  AthenaRetrievalIndexResult,
  AthenaRetrievalSearchResponse,
  AthenaSetupImportPreview,
  AthenaTimeline,
  ChatHistoryMessage,
  LongformMaintenanceDiagnostics,
  LongformMaintenanceRepairResult,
  PaginatedProposalBundles,
  ProposalBundleDetail,
  WorldProjection,
} from '../api/types'

const ATHENA_CACHE_TTL_MS = 5 * 60 * 1000
const ATHENA_CHAT_HISTORY_PAGE_SIZE = 80
const CONSISTENCY_ISSUES_PAGE_SIZE = 100
const LONGFORM_MAINTENANCE_REPAIR_LIMIT = 500
const LONGFORM_MAINTENANCE_MAX_REPAIR_BATCHES = 10

export const useAthenaStore = defineStore('athena', () => {
  const requestCache = useRequestCacheStore()
  const worldModel = useWorldModelStore()
  const activeProjectId = ref<string | null>(null)
  const requestVersion = ref(0)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const ontology = ref<AthenaOntology | null>(null)
  const projection = ref<WorldProjection | null>(null)
  const timeline = ref<AthenaTimeline | null>(null)
  const evolutionPlan = ref<AthenaEvolutionPlan | null>(null)
  const evolutionPlanCacheResource = ref<string | null>(null)
  const proposals = ref<PaginatedProposalBundles | null>(null)
  const proposalDetails = ref<Record<string, ProposalBundleDetail>>({})
  const proposalBusy = ref<Record<string, boolean>>({})
  const consistencyIssues = ref<AthenaConsistencyIssue[]>([])
  const consistencyIssuesTotal = ref(0)
  const consistencyIssuesOffset = ref(0)
  const consistencyIssuesLimit = ref(CONSISTENCY_ISSUES_PAGE_SIZE)
  const consistencyIssuesHasMore = ref(false)
  const consistencyIssuesLoadingMore = ref(false)
  const lastConsistencyCheck = ref<{ chapterIndex: number; issueCount: number } | null>(null)
  const optimization = ref<AthenaOptimization | null>(null)
  const retrievalDiagnostics = ref<AthenaRetrievalDiagnostics | null>(null)
  const retrievalSearch = ref<AthenaRetrievalSearchResponse | null>(null)
  const retrievalLastIndexResult = ref<AthenaRetrievalIndexResult | null>(null)
  const retrievalLoading = ref(false)
  const longformMaintenanceDiagnostics = ref<LongformMaintenanceDiagnostics | null>(null)
  const longformMaintenanceRepairResult = ref<LongformMaintenanceRepairResult | null>(null)
  const longformMaintenanceRepairing = ref(false)
  const setupImportPreview = ref<AthenaSetupImportPreview | null>(null)

  const setup = ref<unknown>(null)
  const lastAnalyzeChapterResult = ref<AthenaAnalyzeChapterResult | null>(null)

  const messages = ref<ChatHistoryMessage[]>([])
  const chatLoading = ref(false)
  let activeChatProjectId: string | null = null
  let messageLoadRequestId = 0
  let sendRequestId = 0
  let sendProjectId: string | null = null
  let consistencyCheckRequestId = 0
  let analyzeChapterRequestId = 0
  let evolutionPlanRequestId = 0

  function cacheKey(projectId: string, resource: string) {
    return `athena:${projectId}:${resource}`
  }

  function isActiveProject(projectId: string) {
    return activeProjectId.value === projectId
  }

  function clearProjectState() {
    ontology.value = null
    projection.value = null
    timeline.value = null
    evolutionPlan.value = null
    evolutionPlanCacheResource.value = null
    proposals.value = null
    proposalDetails.value = {}
    proposalBusy.value = {}
    consistencyIssues.value = []
    consistencyIssuesTotal.value = 0
    consistencyIssuesOffset.value = 0
    consistencyIssuesLimit.value = CONSISTENCY_ISSUES_PAGE_SIZE
    consistencyIssuesHasMore.value = false
    consistencyIssuesLoadingMore.value = false
    lastConsistencyCheck.value = null
    optimization.value = null
    retrievalDiagnostics.value = null
    retrievalSearch.value = null
    retrievalLastIndexResult.value = null
    retrievalLoading.value = false
    longformMaintenanceDiagnostics.value = null
    longformMaintenanceRepairResult.value = null
    longformMaintenanceRepairing.value = false
    setupImportPreview.value = null
    setup.value = null
    lastAnalyzeChapterResult.value = null
    messages.value = []
    loading.value = false
    error.value = null
  }

  function reset(projectId: string | null = null) {
    requestVersion.value += 1
    if (projectId) requestCache.invalidate(cacheKey(projectId, ''))
    worldModel.resetProjectScopedState(projectId || '')
    activeProjectId.value = projectId
    activeChatProjectId = projectId
    messageLoadRequestId += 1
    consistencyCheckRequestId += 1
    analyzeChapterRequestId += 1
    evolutionPlanRequestId += 1
    if (!projectId) {
      sendProjectId = null
      sendRequestId += 1
      chatLoading.value = false
    }
    clearProjectState()
  }

  function ensureProject(projectId: string) {
    const changed = activeProjectId.value !== projectId
    if (changed) reset(projectId)
    return changed
  }

  async function loadCached<T>(
    projectId: string,
    resource: string,
    isLoaded: () => boolean,
    loader: () => Promise<T>,
    apply: (value: T) => void,
  ) {
    ensureProject(projectId)
    const key = cacheKey(projectId, resource)
    const version = requestVersion.value
    if (isLoaded() && requestCache.isFresh(key, ATHENA_CACHE_TTL_MS)) return
    try {
      const value = await requestCache.dedupe(key, loader)
      if (isActiveProject(projectId) && requestVersion.value === version) apply(value)
    } catch (err) {
      if (isActiveProject(projectId) && requestVersion.value === version) error.value = toErrorMessage(err)
    }
  }

  const {
    loadProposals,
    loadProposalDetail,
    reviewProposalItem,
    splitProposalItem,
    rollbackProposalReview,
    batchApproveLowRiskItems,
  } = createAthenaProposalActions({
    ensureProject,
    cacheKey,
    requestCache,
    error,
    proposals,
    proposalDetails,
    proposalBusy,
  })

  const {
    loadRetrievalDiagnostics,
    searchRetrieval,
    reindexRetrieval,
  } = createAthenaRetrievalActions({
    ensureProject,
    cacheKey,
    loadCached,
    requestCache,
    error,
    retrievalDiagnostics,
    retrievalSearch,
    retrievalLastIndexResult,
    retrievalLoading,
  })

  function beginMessageLoad(projectId: string) {
    activeChatProjectId = projectId
    messageLoadRequestId += 1
    return {
      projectId,
      requestId: messageLoadRequestId,
    }
  }

  function beginSend(projectId: string) {
    activeChatProjectId = projectId
    sendProjectId = projectId
    sendRequestId += 1
    messageLoadRequestId += 1
    return {
      projectId,
      requestId: sendRequestId,
    }
  }

  function isCurrentMessageLoad(scope: { projectId: string; requestId: number }) {
    return activeChatProjectId === scope.projectId && messageLoadRequestId === scope.requestId
  }

  function isCurrentSend(scope: { projectId: string; requestId: number }) {
    return sendProjectId === scope.projectId && sendRequestId === scope.requestId
  }

  function isActiveChatProject(projectId: string) {
    return activeChatProjectId === projectId
  }

  function invalidateMessageLoads() {
    messageLoadRequestId += 1
  }

  async function loadOntology(projectId: string) {
    await loadCached(
      projectId,
      'ontology',
      () => !!ontology.value,
      () => api.getAthenaOntology(projectId),
      (value) => {
        ontology.value = value
      },
    )
  }

  async function loadState(projectId: string) {
    await loadCached(
      projectId,
      'state',
      () => !!projection.value,
      () => api.getAthenaState(projectId),
      (overview) => {
        projection.value = overview.projection
      },
    )
  }

  async function loadTimeline(projectId: string) {
    await loadCached(
      projectId,
      'timeline',
      () => !!timeline.value,
      () => api.getAthenaTimeline(projectId, { latest: true, limit: 500 }),
      (value) => {
        timeline.value = value
      },
    )
  }

  function evolutionPlanResource(params?: AthenaEvolutionPlanQuery) {
    if (!params) return 'evolution-plan'
    const query = new URLSearchParams()
    if (params.mode !== undefined) query.set('mode', params.mode)
    if (params.chapter_offset !== undefined) query.set('chapter_offset', String(params.chapter_offset))
    if (params.chapter_limit !== undefined) query.set('chapter_limit', String(params.chapter_limit))
    if (params.plotline_offset !== undefined) query.set('plotline_offset', String(params.plotline_offset))
    if (params.plotline_limit !== undefined) query.set('plotline_limit', String(params.plotline_limit))
    if (params.milestone_offset !== undefined) query.set('milestone_offset', String(params.milestone_offset))
    if (params.milestone_limit !== undefined) query.set('milestone_limit', String(params.milestone_limit))
    if (params.foreshadowing_offset !== undefined) query.set('foreshadowing_offset', String(params.foreshadowing_offset))
    if (params.foreshadowing_limit !== undefined) query.set('foreshadowing_limit', String(params.foreshadowing_limit))
    const serialized = query.toString()
    return serialized ? `evolution-plan:${serialized}` : 'evolution-plan'
  }

  async function loadEvolutionPlan(projectId: string, params?: AthenaEvolutionPlanQuery) {
    ensureProject(projectId)
    const resource = evolutionPlanResource(params)
    const requestId = ++evolutionPlanRequestId
    await loadCached(
      projectId,
      resource,
      () => !!evolutionPlan.value && evolutionPlanCacheResource.value === resource,
      () => (params === undefined ? api.getAthenaEvolutionPlan(projectId) : api.getAthenaEvolutionPlan(projectId, params)),
      (value) => {
        if (requestId !== evolutionPlanRequestId) return
        evolutionPlan.value = value
        evolutionPlanCacheResource.value = resource
      },
    )
  }

  async function loadMessages(projectId: string) {
    ensureProject(projectId)
    const key = cacheKey(projectId, 'messages')
    if (requestCache.isFresh(key, ATHENA_CACHE_TTL_MS)) {
      activeChatProjectId = projectId
      return
    }
    const scope = beginMessageLoad(projectId)
    try {
      const loadedMessages = await requestCache.dedupe(key, () => api.getAthenaMessages(projectId, { limit: ATHENA_CHAT_HISTORY_PAGE_SIZE }))
      if (isCurrentMessageLoad(scope) && isActiveProject(projectId)) {
        messages.value = loadedMessages
      }
    } catch (err) {
      if (isCurrentMessageLoad(scope) && isActiveProject(projectId)) {
        error.value = toErrorMessage(err)
      }
    }
  }

  async function loadSetup(projectId: string) {
    await loadCached(
      projectId,
      'setup',
      () => !!setup.value,
      () => api.getAthenaSetup(projectId),
      (value) => {
        setup.value = value
      },
    )
  }

  async function runConsistencyCheck(projectId: string, chapterIndex: number, depth: string = 'l1') {
    ensureProject(projectId)
    const version = requestVersion.value
    const requestId = ++consistencyCheckRequestId
    loading.value = true
    try {
      const result = await api.runAthenaConsistencyCheck(projectId, chapterIndex, depth)
      if (!isActiveProject(projectId) || requestVersion.value !== version || consistencyCheckRequestId !== requestId) return
      requestCache.invalidate(cacheKey(projectId, 'consistency-issues'))
      await loadConsistencyIssues(projectId)
      const resultIssues = normalizeConsistencyIssues(result)
      const issueCount = consistencyIssues.value.length || resultIssues.length
      lastConsistencyCheck.value = { chapterIndex, issueCount }
    } catch (err) {
      if (isActiveProject(projectId) && requestVersion.value === version && consistencyCheckRequestId === requestId) {
        error.value = toErrorMessage(err)
      }
    } finally {
      if (isActiveProject(projectId) && requestVersion.value === version && consistencyCheckRequestId === requestId) {
        loading.value = false
      }
    }
  }

  async function loadConsistencyIssues(
    projectId: string,
    params: { offset?: number; limit?: number } = {},
  ) {
    ensureProject(projectId)
    const offsetValue = Number(params.offset ?? 0)
    const offset = Math.max(0, Math.floor(Number.isFinite(offsetValue) ? offsetValue : 0))
    const limitValue = Number(params.limit ?? CONSISTENCY_ISSUES_PAGE_SIZE)
    const limit = Math.max(1, Math.floor(Number.isFinite(limitValue) ? limitValue : CONSISTENCY_ISSUES_PAGE_SIZE))
    const key = cacheKey(projectId, `consistency-issues:${offset}:${limit}`)
    const version = requestVersion.value

    try {
      const value = await requestCache.dedupe(key, () => api.getConsistencyIssues(projectId, { offset, limit }))
      if (!isActiveProject(projectId) || requestVersion.value !== version) return
      applyConsistencyIssuesPage(value, offset, limit)
    } catch (err) {
      if (isActiveProject(projectId) && requestVersion.value === version) error.value = toErrorMessage(err)
    }
  }

  async function loadMoreConsistencyIssues(projectId: string) {
    if (!consistencyIssuesHasMore.value || consistencyIssuesLoadingMore.value) return
    consistencyIssuesLoadingMore.value = true
    try {
      await loadConsistencyIssues(projectId, {
        offset: consistencyIssues.value.length,
        limit: consistencyIssuesLimit.value || CONSISTENCY_ISSUES_PAGE_SIZE,
      })
    } finally {
      if (isActiveProject(projectId)) consistencyIssuesLoadingMore.value = false
    }
  }

  function normalizeConsistencyIssues(value: unknown): AthenaConsistencyIssue[] {
    if (Array.isArray(value)) return value as AthenaConsistencyIssue[]
    if (value && typeof value === 'object' && Array.isArray((value as { issues?: unknown }).issues)) {
      return (value as { issues: AthenaConsistencyIssue[] }).issues
    }
    return []
  }

  function applyConsistencyIssuesPage(value: unknown, fallbackOffset: number, fallbackLimit: number) {
    const issues = normalizeConsistencyIssues(value)
    const page = isConsistencyIssuePage(value)
      ? value
      : {
          issues,
          total: issues.length,
          offset: fallbackOffset,
          limit: fallbackLimit,
          has_more: false,
        }

    consistencyIssues.value = page.offset > 0
      ? [...consistencyIssues.value, ...issues]
      : issues
    consistencyIssuesTotal.value = page.total
    consistencyIssuesOffset.value = page.offset
    consistencyIssuesLimit.value = page.limit
    consistencyIssuesHasMore.value = page.has_more
  }

  function isConsistencyIssuePage(value: unknown): value is AthenaConsistencyIssueListResponse {
    return Boolean(
      value
      && typeof value === 'object'
      && Array.isArray((value as { issues?: unknown }).issues)
      && typeof (value as { total?: unknown }).total === 'number'
      && typeof (value as { offset?: unknown }).offset === 'number'
      && typeof (value as { limit?: unknown }).limit === 'number'
      && typeof (value as { has_more?: unknown }).has_more === 'boolean',
    )
  }

  async function loadOptimization(projectId: string) {
    await loadCached(
      projectId,
      'optimization',
      () => !!optimization.value,
      () => api.getAthenaOptimization(projectId),
      (value) => {
        optimization.value = value
      },
    )
  }

  async function loadLongformMaintenanceDiagnostics(projectId: string) {
    await loadCached(
      projectId,
      'longform-maintenance-diagnostics',
      () => !!longformMaintenanceDiagnostics.value,
      () => api.getAthenaLongformMaintenanceDiagnostics(projectId),
      (value) => {
        longformMaintenanceDiagnostics.value = value
      },
    )
  }

  async function repairLongformMaintenance(projectId: string) {
    ensureProject(projectId)
    const version = requestVersion.value
    longformMaintenanceRepairing.value = true
    try {
      for (let batch = 0; batch < LONGFORM_MAINTENANCE_MAX_REPAIR_BATCHES; batch += 1) {
        const result = await api.repairAthenaLongformMaintenance(projectId, {
          repair_limit: LONGFORM_MAINTENANCE_REPAIR_LIMIT,
        })
        if (!isActiveProject(projectId) || requestVersion.value !== version) return
        longformMaintenanceRepairResult.value = result
        longformMaintenanceDiagnostics.value = result.remaining
        if (!result.has_more || result.remaining_issue_count <= 0) break
      }
      requestCache.markFresh(cacheKey(projectId, 'longform-maintenance-diagnostics'))
    } catch (err) {
      if (isActiveProject(projectId) && requestVersion.value === version) {
        error.value = toErrorMessage(err)
      }
    } finally {
      if (isActiveProject(projectId) && requestVersion.value === version) {
        longformMaintenanceRepairing.value = false
      }
    }
  }

  async function importSetup(projectId: string) {
    ensureProject(projectId)
    try {
      requestVersion.value += 1
      await api.importAthenaSetup(projectId)
      requestCache.invalidate(cacheKey(projectId, 'ontology'))
      requestCache.invalidate(cacheKey(projectId, 'setup-import-preview'))
      setupImportPreview.value = null
      await loadOntology(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadSetupImportPreview(projectId: string) {
    await loadCached(
      projectId,
      'setup-import-preview',
      () => !!setupImportPreview.value,
      () => api.getAthenaSetupImportPreview(projectId),
      (value) => {
        setupImportPreview.value = value
      },
    )
  }

  async function analyzeChapter(projectId: string, chapterIndex: number) {
    ensureProject(projectId)
    const version = requestVersion.value
    const requestId = ++analyzeChapterRequestId
    try {
      const result = await api.analyzeAthenaChapter(projectId, chapterIndex)
      if (!isActiveProject(projectId) || requestVersion.value !== version || analyzeChapterRequestId !== requestId) return
      lastAnalyzeChapterResult.value = result
      requestCache.invalidate(cacheKey(projectId, 'proposals'))
      await loadProposals(projectId)
      if (!isActiveProject(projectId) || requestVersion.value !== version || analyzeChapterRequestId !== requestId) return
      await worldModel.loadSetupPanelData(projectId)
    } catch (err) {
      if (isActiveProject(projectId) && requestVersion.value === version && analyzeChapterRequestId === requestId) {
        error.value = toErrorMessage(err)
      }
    }
  }

  async function sendChat(projectId: string, text: string) {
    ensureProject(projectId)
    const scope = beginSend(projectId)
    chatLoading.value = true
    try {
      const response = await api.sendAthenaChat(projectId, text)
      if (!isCurrentSend(scope) || !isActiveChatProject(projectId)) return

      const loadedMessages = await api.getAthenaMessages(projectId, { limit: ATHENA_CHAT_HISTORY_PAGE_SIZE })
      if (!isCurrentSend(scope) || !isActiveChatProject(projectId)) return
      invalidateMessageLoads()
      messages.value = loadedMessages
      requestCache.markFresh(cacheKey(projectId, 'messages'))

      const targets = new Set(response.refresh_targets || [])
      if (targets.has('proposals')) {
        const loadedProposals = await api.getAthenaEvolutionProposals(projectId, undefined)
        if (!isCurrentSend(scope) || !isActiveChatProject(projectId)) return
        proposals.value = loadedProposals
        requestCache.markFresh(cacheKey(projectId, 'proposals'))
        await worldModel.loadSetupPanelData(projectId)
      }
      if (targets.has('ontology')) {
        const loadedOntology = await api.getAthenaOntology(projectId)
        if (!isCurrentSend(scope) || !isActiveChatProject(projectId)) return
        ontology.value = loadedOntology
        requestCache.markFresh(cacheKey(projectId, 'ontology'))
      }
      if (targets.has('state') || targets.has('projection')) {
        const overview = await api.getAthenaState(projectId)
        if (!isCurrentSend(scope) || !isActiveChatProject(projectId)) return
        projection.value = overview.projection
        requestCache.markFresh(cacheKey(projectId, 'state'))
      }
    } catch (err) {
      if (isCurrentSend(scope) && isActiveChatProject(projectId)) {
        error.value = toErrorMessage(err)
      }
    } finally {
      if (isCurrentSend(scope)) {
        chatLoading.value = false
      }
    }
  }

  return {
    activeProjectId,
    loading,
    error,
    ontology,
    projection,
    timeline,
    evolutionPlan,
    proposals,
    proposalDetails,
    proposalBusy,
    consistencyIssues,
    consistencyIssuesTotal,
    consistencyIssuesOffset,
    consistencyIssuesLimit,
    consistencyIssuesHasMore,
    consistencyIssuesLoadingMore,
    lastConsistencyCheck,
    optimization,
    retrievalDiagnostics,
    retrievalSearch,
    retrievalLastIndexResult,
    retrievalLoading,
    longformMaintenanceDiagnostics,
    longformMaintenanceRepairResult,
    longformMaintenanceRepairing,
    setupImportPreview,
    setup,
    lastAnalyzeChapterResult,
    messages,
    chatLoading,
    loadOntology,
    loadState,
    loadTimeline,
    loadEvolutionPlan,
    loadProposals,
    loadProposalDetail,
    reviewProposalItem,
    splitProposalItem,
    rollbackProposalReview,
    batchApproveLowRiskItems,
    loadSetup,
    runConsistencyCheck,
    loadConsistencyIssues,
    loadMoreConsistencyIssues,
    loadOptimization,
    loadLongformMaintenanceDiagnostics,
    repairLongformMaintenance,
    loadSetupImportPreview,
    importSetup,
    analyzeChapter,
    loadRetrievalDiagnostics,
    searchRetrieval,
    reindexRetrieval,
    loadMessages,
    sendChat,
    ensureProject,
    reset,
  }
})
