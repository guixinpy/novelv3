import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type {
  AthenaEvolutionPlan,
  AthenaOntology,
  AthenaOptimization,
  AthenaTimeline,
  ChatHistoryMessage,
  PaginatedProposalBundles,
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
  const consistencyIssues = ref<any[]>([])
  const optimization = ref<AthenaOptimization | null>(null)

  const setup = ref<unknown>(null)

  const messages = ref<ChatHistoryMessage[]>([])
  const chatLoading = ref(false)

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

  async function loadProposals(projectId: string, params?: { offset?: number; limit?: number; bundle_status?: string }) {
    try {
      proposals.value = await api.getAthenaEvolutionProposals(projectId, params)
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadMessages(projectId: string) {
    try {
      messages.value = await api.getAthenaMessages(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
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

  async function sendChat(projectId: string, text: string) {
    chatLoading.value = true
    try {
      await api.sendAthenaChat(projectId, text)
      await loadMessages(projectId)
    } catch (err) {
      error.value = toErrorMessage(err)
    } finally {
      chatLoading.value = false
    }
  }

  function reset() {
    ontology.value = null
    projection.value = null
    timeline.value = null
    evolutionPlan.value = null
    proposals.value = null
    consistencyIssues.value = []
    optimization.value = null
    setup.value = null
    messages.value = []
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
    consistencyIssues,
    optimization,
    setup,
    messages,
    chatLoading,
    loadOntology,
    loadState,
    loadTimeline,
    loadEvolutionPlan,
    loadProposals,
    loadSetup,
    runConsistencyCheck,
    loadConsistencyIssues,
    loadOptimization,
    loadMessages,
    sendChat,
    reset,
  }
})
