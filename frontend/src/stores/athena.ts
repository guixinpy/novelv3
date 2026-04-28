import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
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

export const useAthenaStore = defineStore('athena', () => {
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
  let chatScopeProjectId: string | null = null
  let chatScopeRequestId = 0

  function beginChatScope(projectId: string) {
    chatScopeProjectId = projectId
    chatScopeRequestId += 1
    return {
      projectId,
      requestId: chatScopeRequestId,
    }
  }

  function isCurrentChatScope(scope: { projectId: string; requestId: number }) {
    return chatScopeProjectId === scope.projectId && chatScopeRequestId === scope.requestId
  }

  async function loadOntology(projectId: string) {
    try {
      ontology.value = await api.getAthenaOntology(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadState(projectId: string) {
    try {
      const overview = await api.getAthenaState(projectId)
      projection.value = overview.projection
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadTimeline(projectId: string) {
    try {
      timeline.value = await api.getAthenaTimeline(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadEvolutionPlan(projectId: string) {
    try {
      evolutionPlan.value = await api.getAthenaEvolutionPlan(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadProposals(projectId: string, params?: { offset?: number; limit?: number; bundle_status?: string; item_status?: string }) {
    try {
      proposals.value = await api.getAthenaEvolutionProposals(projectId, params)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadProposalDetail(projectId: string, bundleId: string) {
    try {
      proposalDetails.value[bundleId] = await api.getAthenaProposalDetail(projectId, bundleId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function reviewProposalItem(projectId: string, bundleId: string, itemId: string, payload: ProposalReviewRequest) {
    proposalBusy.value[itemId] = true
    try {
      await api.reviewAthenaProposalItem(projectId, itemId, payload)
      await loadProposalDetail(projectId, bundleId)
      await loadProposals(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      proposalBusy.value[itemId] = false
    }
  }

  async function splitProposalItem(projectId: string, bundleId: string, itemId: string, reason: string) {
    proposalBusy.value[itemId] = true
    const payload: ProposalSplitRequest = {
      reviewer_ref: 'athena.user',
      reason,
      evidence_refs: [],
      item_ids: [itemId],
    }
    try {
      proposalDetails.value[bundleId] = await api.splitAthenaProposalBundle(projectId, bundleId, payload)
      await loadProposals(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      proposalBusy.value[itemId] = false
    }
  }

  async function rollbackProposalReview(projectId: string, bundleId: string, itemId: string, reviewId: string, reason: string) {
    proposalBusy.value[itemId] = true
    const payload: ProposalRollbackRequest = {
      reviewer_ref: 'athena.user',
      reason,
      evidence_refs: [],
    }
    try {
      await api.rollbackAthenaProposalReview(projectId, reviewId, payload)
      await loadProposalDetail(projectId, bundleId)
      await loadProposals(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      proposalBusy.value[itemId] = false
    }
  }

  async function batchApproveLowRiskItems(projectId: string, bundleId: string) {
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
    const scope = beginChatScope(projectId)
    try {
      const loadedMessages = await api.getAthenaMessages(projectId)
      if (isCurrentChatScope(scope)) {
        messages.value = loadedMessages
      }
    } catch (err) {
      if (isCurrentChatScope(scope)) {
        error.value = toErrorMessage(err)
      }
    }
  }

  async function loadSetup(projectId: string) {
    try {
      setup.value = await api.getAthenaSetup(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function runConsistencyCheck(projectId: string, chapterIndex: number, depth: string = 'l1') {
    try {
      await api.runAthenaConsistencyCheck(projectId, chapterIndex, depth)
      await loadConsistencyIssues(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadConsistencyIssues(projectId: string) {
    try {
      consistencyIssues.value = await api.getConsistencyIssues(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadOptimization(projectId: string) {
    try {
      optimization.value = await api.getAthenaOptimization(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function importSetup(projectId: string) {
    try {
      await api.importAthenaSetup(projectId)
      await loadOntology(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function analyzeChapter(projectId: string, chapterIndex: number) {
    try {
      await api.analyzeAthenaChapter(projectId, chapterIndex)
      await loadProposals(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadRetrievalDiagnostics(projectId: string) {
    try {
      retrievalDiagnostics.value = await api.getAthenaRetrievalDiagnostics(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function searchRetrieval(projectId: string, q: string, params?: { limit?: number; source_type?: string; chapter_index?: number }) {
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
    retrievalLoading.value = true
    try {
      retrievalLastIndexResult.value = await api.reindexAthenaRetrieval(projectId)
      await loadRetrievalDiagnostics(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      retrievalLoading.value = false
    }
  }

  async function sendChat(projectId: string, text: string) {
    const scope = beginChatScope(projectId)
    chatLoading.value = true
    try {
      const response = await api.sendAthenaChat(projectId, text)
      if (!isCurrentChatScope(scope)) return

      const loadedMessages = await api.getAthenaMessages(projectId)
      if (!isCurrentChatScope(scope)) return
      messages.value = loadedMessages

      const targets = new Set(response.refresh_targets || [])
      if (targets.has('proposals')) {
        const loadedProposals = await api.getAthenaEvolutionProposals(projectId, undefined)
        if (!isCurrentChatScope(scope)) return
        proposals.value = loadedProposals
      }
      if (targets.has('ontology')) {
        const loadedOntology = await api.getAthenaOntology(projectId)
        if (!isCurrentChatScope(scope)) return
        ontology.value = loadedOntology
      }
      if (targets.has('state') || targets.has('projection')) {
        const overview = await api.getAthenaState(projectId)
        if (!isCurrentChatScope(scope)) return
        projection.value = overview.projection
      }
    } catch (err) {
      if (isCurrentChatScope(scope)) {
        error.value = toErrorMessage(err)
      }
    } finally {
      if (isCurrentChatScope(scope)) {
        chatLoading.value = false
      }
    }
  }

  function reset() {
    chatScopeProjectId = null
    chatScopeRequestId += 1
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
    chatLoading.value = false
    error.value = null
  }

  return {
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
    reset,
  }
})
