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
  AthenaConsistencyIssue,
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
  PaginatedProposalBundles,
  ProposalBundleDetail,
  WorldProjection,
} from '../api/types'

const ATHENA_CACHE_TTL_MS = 5 * 60 * 1000
const ATHENA_CHAT_HISTORY_PAGE_SIZE = 80

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
  const proposals = ref<PaginatedProposalBundles | null>(null)
  const proposalDetails = ref<Record<string, ProposalBundleDetail>>({})
  const proposalBusy = ref<Record<string, boolean>>({})
  const consistencyIssues = ref<AthenaConsistencyIssue[]>([])
  const lastConsistencyCheck = ref<{ chapterIndex: number; issueCount: number } | null>(null)
  const optimization = ref<AthenaOptimization | null>(null)
  const retrievalDiagnostics = ref<AthenaRetrievalDiagnostics | null>(null)
  const retrievalSearch = ref<AthenaRetrievalSearchResponse | null>(null)
  const retrievalLastIndexResult = ref<AthenaRetrievalIndexResult | null>(null)
  const retrievalLoading = ref(false)
  const longformMaintenanceDiagnostics = ref<LongformMaintenanceDiagnostics | null>(null)
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
    proposals.value = null
    proposalDetails.value = {}
    proposalBusy.value = {}
    consistencyIssues.value = []
    lastConsistencyCheck.value = null
    optimization.value = null
    retrievalDiagnostics.value = null
    retrievalSearch.value = null
    retrievalLastIndexResult.value = null
    retrievalLoading.value = false
    longformMaintenanceDiagnostics.value = null
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
      () => api.getAthenaTimeline(projectId),
      (value) => {
        timeline.value = value
      },
    )
  }

  async function loadEvolutionPlan(projectId: string) {
    await loadCached(
      projectId,
      'evolution-plan',
      () => !!evolutionPlan.value,
      () => api.getAthenaEvolutionPlan(projectId),
      (value) => {
        evolutionPlan.value = value
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

  async function loadConsistencyIssues(projectId: string) {
    await loadCached(
      projectId,
      'consistency-issues',
      () => true,
      () => api.getConsistencyIssues(projectId),
      (value) => {
        consistencyIssues.value = normalizeConsistencyIssues(value)
      },
    )
  }

  function normalizeConsistencyIssues(value: unknown): AthenaConsistencyIssue[] {
    if (Array.isArray(value)) return value as AthenaConsistencyIssue[]
    if (value && typeof value === 'object' && Array.isArray((value as { issues?: unknown }).issues)) {
      return (value as { issues: AthenaConsistencyIssue[] }).issues
    }
    return []
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
    lastConsistencyCheck,
    optimization,
    retrievalDiagnostics,
    retrievalSearch,
    retrievalLastIndexResult,
    retrievalLoading,
    longformMaintenanceDiagnostics,
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
    loadOptimization,
    loadLongformMaintenanceDiagnostics,
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
