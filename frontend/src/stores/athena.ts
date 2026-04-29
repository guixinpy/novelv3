import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import { useRequestCacheStore } from './requestCache'
import type {
  AthenaEvolutionPlan,
  AthenaOntology,
  AthenaOptimization,
  AthenaRetrievalDiagnostics,
  AthenaRetrievalIndexResult,
  AthenaRetrievalSearchResponse,
  AthenaTimeline,
  ChatHistoryMessage,
  PaginatedProposalBundles,
  ProposalBundleDetail,
  ProposalReviewRequest,
  ProposalRollbackRequest,
  ProposalSplitRequest,
  WorldProjection,
} from '../api/types'

function toErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err)
}

const ATHENA_CACHE_TTL_MS = 5 * 60 * 1000
const ATHENA_CHAT_HISTORY_PAGE_SIZE = 80

export const useAthenaStore = defineStore('athena', () => {
  const requestCache = useRequestCacheStore()
  const activeProjectId = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const ontology = ref<AthenaOntology | null>(null)
  const projection = ref<WorldProjection | null>(null)
  const timeline = ref<AthenaTimeline | null>(null)
  const evolutionPlan = ref<AthenaEvolutionPlan | null>(null)
  const proposals = ref<PaginatedProposalBundles | null>(null)
  const proposalDetails = ref<Record<string, ProposalBundleDetail>>({})
  const proposalBusy = ref<Record<string, boolean>>({})
  const consistencyIssues = ref<any[]>([])
  const optimization = ref<AthenaOptimization | null>(null)
  const retrievalDiagnostics = ref<AthenaRetrievalDiagnostics | null>(null)
  const retrievalSearch = ref<AthenaRetrievalSearchResponse | null>(null)
  const retrievalLastIndexResult = ref<AthenaRetrievalIndexResult | null>(null)
  const retrievalLoading = ref(false)

  const setup = ref<unknown>(null)

  const messages = ref<ChatHistoryMessage[]>([])
  const chatLoading = ref(false)
  let activeChatProjectId: string | null = null
  let messageLoadRequestId = 0
  let sendRequestId = 0
  let sendProjectId: string | null = null

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
    optimization.value = null
    retrievalDiagnostics.value = null
    retrievalSearch.value = null
    retrievalLastIndexResult.value = null
    retrievalLoading.value = false
    setup.value = null
    messages.value = []
    error.value = null
  }

  function reset(projectId: string | null = null) {
    if (projectId) requestCache.invalidate(cacheKey(projectId, ''))
    activeProjectId.value = projectId
    activeChatProjectId = projectId
    messageLoadRequestId += 1
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
    if (isLoaded() && requestCache.isFresh(key, ATHENA_CACHE_TTL_MS)) return
    try {
      const value = await requestCache.dedupe(key, loader)
      if (isActiveProject(projectId)) apply(value)
    } catch (err) {
      if (isActiveProject(projectId)) error.value = toErrorMessage(err)
    }
  }

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

  async function loadProposals(projectId: string, params?: { offset?: number; limit?: number; bundle_status?: string; item_status?: string }) {
    ensureProject(projectId)
    try {
      proposals.value = await api.getAthenaEvolutionProposals(projectId, params)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadProposalDetail(projectId: string, bundleId: string) {
    ensureProject(projectId)
    try {
      proposalDetails.value[bundleId] = await api.getAthenaProposalDetail(projectId, bundleId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function reviewProposalItem(projectId: string, bundleId: string, itemId: string, payload: ProposalReviewRequest) {
    ensureProject(projectId)
    proposalBusy.value[itemId] = true
    try {
      await api.reviewAthenaProposalItem(projectId, itemId, payload)
      requestCache.invalidate(cacheKey(projectId, 'proposals'))
      requestCache.invalidate(cacheKey(projectId, `proposal-detail:${bundleId}`))
      await loadProposalDetail(projectId, bundleId)
      await loadProposals(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      proposalBusy.value[itemId] = false
    }
  }

  async function splitProposalItem(projectId: string, bundleId: string, itemId: string, reason: string) {
    ensureProject(projectId)
    proposalBusy.value[itemId] = true
    const payload: ProposalSplitRequest = {
      reviewer_ref: 'athena.user',
      reason,
      evidence_refs: [],
      item_ids: [itemId],
    }
    try {
      proposalDetails.value[bundleId] = await api.splitAthenaProposalBundle(projectId, bundleId, payload)
      requestCache.invalidate(cacheKey(projectId, 'proposals'))
      await loadProposals(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      proposalBusy.value[itemId] = false
    }
  }

  async function rollbackProposalReview(projectId: string, bundleId: string, itemId: string, reviewId: string, reason: string) {
    ensureProject(projectId)
    proposalBusy.value[itemId] = true
    const payload: ProposalRollbackRequest = {
      reviewer_ref: 'athena.user',
      reason,
      evidence_refs: [],
    }
    try {
      await api.rollbackAthenaProposalReview(projectId, reviewId, payload)
      requestCache.invalidate(cacheKey(projectId, 'proposals'))
      requestCache.invalidate(cacheKey(projectId, `proposal-detail:${bundleId}`))
      await loadProposalDetail(projectId, bundleId)
      await loadProposals(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      proposalBusy.value[itemId] = false
    }
  }

  async function batchApproveLowRiskItems(projectId: string, bundleId: string) {
    ensureProject(projectId)
    if (!proposalDetails.value[bundleId]) {
      await loadProposalDetail(projectId, bundleId)
    }
    const detail = proposalDetails.value[bundleId]
    if (!detail) return
    const conflictedItemIds = new Set(detail.conflicts.map((conflict) => conflict.item_id))
    const items = detail.items.filter((item) =>
      ['pending', 'needs_edit'].includes(item.item_status) && !conflictedItemIds.has(item.id),
    )
    try {
      for (const item of items) {
        proposalBusy.value[item.id] = true
        await api.reviewAthenaProposalItem(projectId, item.id, {
          reviewer_ref: 'athena.batch',
          action: 'approve',
          reason: '批量通过低风险候选',
          evidence_refs: [],
          edited_fields: {},
        })
        proposalBusy.value[item.id] = false
      }
      requestCache.invalidate(cacheKey(projectId, 'proposals'))
      requestCache.invalidate(cacheKey(projectId, `proposal-detail:${bundleId}`))
      await loadProposalDetail(projectId, bundleId)
      await loadProposals(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      for (const item of items) {
        proposalBusy.value[item.id] = false
      }
    }
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
    try {
      await api.runAthenaConsistencyCheck(projectId, chapterIndex, depth)
      requestCache.invalidate(cacheKey(projectId, 'consistency-issues'))
      await loadConsistencyIssues(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadConsistencyIssues(projectId: string) {
    await loadCached(
      projectId,
      'consistency-issues',
      () => true,
      () => api.getConsistencyIssues(projectId),
      (value) => {
        consistencyIssues.value = value
      },
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

  async function importSetup(projectId: string) {
    ensureProject(projectId)
    try {
      await api.importAthenaSetup(projectId)
      requestCache.invalidate(cacheKey(projectId, 'ontology'))
      await loadOntology(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function analyzeChapter(projectId: string, chapterIndex: number) {
    ensureProject(projectId)
    try {
      await api.analyzeAthenaChapter(projectId, chapterIndex)
      requestCache.invalidate(cacheKey(projectId, 'proposals'))
      await loadProposals(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadRetrievalDiagnostics(projectId: string) {
    await loadCached(
      projectId,
      'retrieval-diagnostics',
      () => !!retrievalDiagnostics.value,
      () => api.getAthenaRetrievalDiagnostics(projectId),
      (value) => {
        retrievalDiagnostics.value = value
      },
    )
  }

  async function searchRetrieval(projectId: string, q: string, params?: { limit?: number; source_type?: string; chapter_index?: number }) {
    ensureProject(projectId)
    if (!q.trim()) {
      retrievalSearch.value = null
      return
    }
    retrievalLoading.value = true
    try {
      retrievalSearch.value = await api.searchAthenaRetrieval(projectId, { q: q.trim(), ...params })
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      retrievalLoading.value = false
    }
  }

  async function reindexRetrieval(projectId: string) {
    ensureProject(projectId)
    retrievalLoading.value = true
    try {
      retrievalLastIndexResult.value = await api.reindexAthenaRetrieval(projectId)
      requestCache.invalidate(cacheKey(projectId, 'retrieval-diagnostics'))
      await loadRetrievalDiagnostics(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      retrievalLoading.value = false
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
    optimization,
    retrievalDiagnostics,
    retrievalSearch,
    retrievalLastIndexResult,
    retrievalLoading,
    setup,
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
