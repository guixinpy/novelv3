import type { Ref } from 'vue'
import { api } from '../../api/client'
import type {
  AthenaRetrievalDiagnostics,
  AthenaRetrievalIndexResult,
  AthenaRetrievalSearchResponse,
} from '../../api/types'
import { toErrorMessage } from './errors'

interface RetrievalContext {
  ensureProject: (projectId: string) => void
  cacheKey: (projectId: string, resource: string) => string
  loadCached: <T>(
    projectId: string,
    resource: string,
    isLoaded: () => boolean,
    loader: () => Promise<T>,
    apply: (value: T) => void,
  ) => Promise<void>
  requestCache: {
    invalidate: (key: string) => void
  }
  error: Ref<string | null>
  retrievalDiagnostics: Ref<AthenaRetrievalDiagnostics | null>
  retrievalSearch: Ref<AthenaRetrievalSearchResponse | null>
  retrievalLastIndexResult: Ref<AthenaRetrievalIndexResult | null>
  retrievalLoading: Ref<boolean>
}

export function createAthenaRetrievalActions(ctx: RetrievalContext) {
  async function loadRetrievalDiagnostics(projectId: string) {
    await ctx.loadCached(
      projectId,
      'retrieval-diagnostics',
      () => !!ctx.retrievalDiagnostics.value,
      () => api.getAthenaRetrievalDiagnostics(projectId),
      (value) => {
        ctx.retrievalDiagnostics.value = value
      },
    )
  }

  async function searchRetrieval(
    projectId: string,
    q: string,
    params?: { limit?: number; source_type?: string; chapter_index?: number },
  ) {
    ctx.ensureProject(projectId)
    if (!q.trim()) {
      ctx.retrievalSearch.value = null
      return
    }
    ctx.retrievalLoading.value = true
    try {
      ctx.retrievalSearch.value = await api.searchAthenaRetrieval(projectId, { q: q.trim(), ...params })
    } catch (err) {
      ctx.error.value = toErrorMessage(err)
    } finally {
      ctx.retrievalLoading.value = false
    }
  }

  async function reindexRetrieval(projectId: string) {
    ctx.ensureProject(projectId)
    ctx.retrievalLoading.value = true
    try {
      ctx.retrievalLastIndexResult.value = await api.reindexAthenaRetrieval(projectId)
      ctx.requestCache.invalidate(ctx.cacheKey(projectId, 'retrieval-diagnostics'))
      await loadRetrievalDiagnostics(projectId)
    } catch (err) {
      ctx.error.value = toErrorMessage(err)
    } finally {
      ctx.retrievalLoading.value = false
    }
  }

  return {
    loadRetrievalDiagnostics,
    searchRetrieval,
    reindexRetrieval,
  }
}
