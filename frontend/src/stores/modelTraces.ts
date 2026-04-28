import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type {
  ModelCallTraceDetail,
  ModelCallTraceListItem,
  ModelCallTraceListParams,
} from '../api/types'

type RequestLane = 'list' | 'detail'

export type ModelTraceFilters = Pick<ModelCallTraceListParams, 'trace_type' | 'chapter_index' | 'dialog_id'>

interface RequestSnapshot {
  projectId: string
  version: number
  requestId: number
}

const DEFAULT_LIMIT = 20

function toErrorMessage(err: unknown) {
  return err instanceof Error ? err.message : String(err || '加载模型调用记录失败')
}

function normalizeFilters(nextFilters: ModelTraceFilters) {
  const normalized: ModelTraceFilters = {}
  if (nextFilters.trace_type) normalized.trace_type = nextFilters.trace_type
  if (nextFilters.chapter_index !== undefined) normalized.chapter_index = nextFilters.chapter_index
  if (nextFilters.dialog_id) normalized.dialog_id = nextFilters.dialog_id
  return normalized
}

export const useModelTraceStore = defineStore('modelTraces', () => {
  const items = ref<ModelCallTraceListItem[]>([])
  const total = ref(0)
  const loadingList = ref(false)
  const loadingDetail = ref(false)
  const error = ref('')
  const selectedTrace = ref<ModelCallTraceDetail | null>(null)
  const selectedTraceId = ref<string | null>(null)
  const filters = ref<ModelTraceFilters>({})
  const limit = ref(DEFAULT_LIMIT)
  const offset = ref(0)

  const currentProjectScope = ref('')
  const scopeVersion = ref(0)
  const nextRequestId = ref(0)
  const latestLaneRequest = ref<Record<RequestLane, number>>({
    list: 0,
    detail: 0,
  })

  function resetProjectScopedState(nextProjectId = '') {
    scopeVersion.value += 1
    currentProjectScope.value = nextProjectId
    latestLaneRequest.value = {
      list: 0,
      detail: 0,
    }
    items.value = []
    total.value = 0
    loadingList.value = false
    loadingDetail.value = false
    error.value = ''
    selectedTrace.value = null
    selectedTraceId.value = null
    filters.value = {}
    limit.value = DEFAULT_LIMIT
    offset.value = 0
  }

  function captureScope(projectId: string) {
    if (!currentProjectScope.value) {
      currentProjectScope.value = projectId
    } else if (currentProjectScope.value !== projectId) {
      resetProjectScopedState(projectId)
    }
    return {
      projectId,
      version: scopeVersion.value,
    }
  }

  function captureRequest(projectId: string, lane: RequestLane): RequestSnapshot {
    const snapshot = captureScope(projectId)
    const requestId = nextRequestId.value + 1
    nextRequestId.value = requestId
    latestLaneRequest.value[lane] = requestId
    return {
      ...snapshot,
      requestId,
    }
  }

  function isLatestRequest(snapshot: RequestSnapshot, lane: RequestLane) {
    return currentProjectScope.value === snapshot.projectId
      && scopeVersion.value === snapshot.version
      && latestLaneRequest.value[lane] === snapshot.requestId
  }

  async function loadList(projectId: string, nextFilters?: ModelTraceFilters) {
    const snapshot = captureRequest(projectId, 'list')
    if (nextFilters) filters.value = normalizeFilters(nextFilters)
    loadingList.value = true
    error.value = ''

    try {
      const result = await api.listModelCallTraces(projectId, {
        ...filters.value,
        limit: limit.value,
        offset: offset.value,
      })
      if (!isLatestRequest(snapshot, 'list')) return
      items.value = result.items
      total.value = result.total
    } catch (err) {
      if (isLatestRequest(snapshot, 'list')) {
        error.value = toErrorMessage(err)
      }
    } finally {
      if (isLatestRequest(snapshot, 'list')) {
        loadingList.value = false
      }
    }
  }

  async function selectTrace(projectId: string, traceId: string) {
    const snapshot = captureRequest(projectId, 'detail')
    selectedTraceId.value = traceId
    selectedTrace.value = null
    loadingDetail.value = true
    error.value = ''

    try {
      const detail = await api.getModelCallTrace(projectId, traceId)
      if (!isLatestRequest(snapshot, 'detail')) return
      selectedTrace.value = detail
      selectedTraceId.value = traceId
    } catch (err) {
      if (isLatestRequest(snapshot, 'detail')) {
        selectedTrace.value = null
        error.value = toErrorMessage(err)
      }
    } finally {
      if (isLatestRequest(snapshot, 'detail')) {
        loadingDetail.value = false
      }
    }
  }

  function openTrace(projectId: string, traceId: string) {
    return selectTrace(projectId, traceId)
  }

  function closeTrace() {
    latestLaneRequest.value.detail = nextRequestId.value + 1
    nextRequestId.value = latestLaneRequest.value.detail
    selectedTraceId.value = null
    selectedTrace.value = null
    loadingDetail.value = false
    error.value = ''
  }

  function reset() {
    resetProjectScopedState()
  }

  return {
    items,
    total,
    loadingList,
    loadingDetail,
    error,
    selectedTrace,
    selectedTraceId,
    filters,
    limit,
    offset,
    loadList,
    selectTrace,
    openTrace,
    closeTrace,
    reset,
  }
})
