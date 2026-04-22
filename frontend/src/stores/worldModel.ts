import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'
import type {
  ProjectProfileVersion,
  ProposalBundle,
  ProposalBundleDetail,
  ProposalReviewRequest,
  ProposalRollbackRequest,
  ProposalSplitRequest,
  WorldProjection,
} from '../api/types'

type RequestLane = 'overview' | 'bundles' | 'detail'

interface RequestSnapshot {
  projectId: string
  version: number
  requestId: number
}

interface BundleDetailLoadOptions {
  clearOnFailure?: boolean
  suppressError?: boolean
  requestSnapshot?: RequestSnapshot
}

interface PendingActionCounts {
  [itemId: string]: number
}

export const useWorldModelStore = defineStore('worldModel', () => {
  const projectProfile = ref<ProjectProfileVersion | null>(null)
  const projection = ref<WorldProjection | null>(null)
  const proposalBundles = ref<ProposalBundle[]>([])
  const selectedBundleId = ref<string | null>(null)
  const selectedBundleDetail = ref<ProposalBundleDetail | null>(null)
  const subjectKnowledge = ref<WorldProjection | null>(null)
  const selectedSubjectRef = ref<string | null>(null)
  const chapterSnapshot = ref<WorldProjection | null>(null)
  const selectedChapterIndex = ref<number | null>(null)
  const reviewerName = ref('editor')
  const bundlesTotal = ref(0)
  const bundlesOffset = ref(0)
  const bundlesLimit = ref(20)
  const bundleFilters = ref<{ bundle_status?: string; item_status?: string; profile_version?: number }>({})
  const loading = ref(false)
  const loaded = ref(false)
  const error = ref('')
  const activeSubmissionCount = ref(0)
  const pendingActionCounts = ref<PendingActionCounts>({})
  const currentProjectScope = ref('')
  const scopeVersion = ref(0)
  const nextRequestId = ref(0)
  const latestLaneRequest = ref<Record<RequestLane, number>>({
    overview: 0,
    bundles: 0,
    detail: 0,
  })

  const hasWorldData = computed(() =>
    projectProfile.value !== null || projection.value !== null || proposalBundles.value.length > 0,
  )
  const submitting = computed(() => activeSubmissionCount.value > 0)
  const activeActionItemId = computed(() => Object.keys(pendingActionCounts.value)[0] ?? null)

  function captureScope(projectId: string) {
    if (currentProjectScope.value !== projectId) {
      resetProjectScopedState(projectId)
    }
    return {
      projectId,
      version: scopeVersion.value,
    }
  }

  function isActiveScope(projectId: string, version: number) {
    return currentProjectScope.value === projectId && scopeVersion.value === version
  }

  function captureRequest(projectId: string, lanes: RequestLane[]): RequestSnapshot {
    const snapshot = captureScope(projectId)
    const requestId = nextRequestId.value + 1
    nextRequestId.value = requestId
    for (const lane of lanes) {
      latestLaneRequest.value[lane] = requestId
    }
    return {
      ...snapshot,
      requestId,
    }
  }

  function isLatestRequest(snapshot: RequestSnapshot, lane: RequestLane) {
    return isActiveScope(snapshot.projectId, snapshot.version)
      && latestLaneRequest.value[lane] === snapshot.requestId
  }

  function toErrorMessage(err: unknown) {
    return err instanceof Error ? err.message : String(err || '加载世界模型失败')
  }

  function areLanesLatest(snapshot: RequestSnapshot, lanes: RequestLane[]) {
    return lanes.every((lane) => isLatestRequest(snapshot, lane))
  }

  function assignErrorForSnapshot(snapshot: RequestSnapshot, lanes: RequestLane[], nextError: string) {
    if (areLanesLatest(snapshot, lanes)) {
      error.value = nextError
    }
  }

  function captureRefreshError(currentError: string, err: unknown) {
    return currentError || toErrorMessage(err)
  }

  function assignErrorForScope(projectId: string, version: number, nextError: string) {
    if (isActiveScope(projectId, version)) {
      error.value = nextError
    }
  }

  function beginAction(itemId?: string | null) {
    activeSubmissionCount.value += 1
    if (!itemId) return
    pendingActionCounts.value = {
      ...pendingActionCounts.value,
      [itemId]: (pendingActionCounts.value[itemId] ?? 0) + 1,
    }
  }

  function finishAction(itemId?: string | null) {
    activeSubmissionCount.value = Math.max(0, activeSubmissionCount.value - 1)
    if (!itemId) return

    const nextCount = (pendingActionCounts.value[itemId] ?? 0) - 1
    if (nextCount > 0) {
      pendingActionCounts.value = {
        ...pendingActionCounts.value,
        [itemId]: nextCount,
      }
      return
    }

    const { [itemId]: _removed, ...rest } = pendingActionCounts.value
    pendingActionCounts.value = rest
  }

  function isActionPending(itemId: string) {
    return (pendingActionCounts.value[itemId] ?? 0) > 0
  }

  function ensureProjectScope(projectId: string) {
    if (!currentProjectScope.value) {
      currentProjectScope.value = projectId
      return
    }
    if (currentProjectScope.value !== projectId) {
      resetProjectScopedState(projectId)
    }
  }

  async function loadSubjectKnowledge(projectId: string, subjectRef: string) {
    ensureProjectScope(projectId)
    selectedSubjectRef.value = subjectRef
    try {
      const overview = await api.getSubjectKnowledge(projectId, subjectRef)
      subjectKnowledge.value = overview.projection
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function loadChapterSnapshot(projectId: string, chapterIndex: number) {
    ensureProjectScope(projectId)
    selectedChapterIndex.value = chapterIndex
    try {
      const overview = await api.getChapterSnapshot(projectId, chapterIndex)
      chapterSnapshot.value = overview.projection
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  function setReviewerName(projectId: string, name: string) {
    reviewerName.value = name
    localStorage.setItem(`mozhou_reviewer_${projectId}`, name)
  }

  function resetProjectScopedState(nextProjectId = '') {
    scopeVersion.value += 1
    currentProjectScope.value = nextProjectId
    latestLaneRequest.value = {
      overview: 0,
      bundles: 0,
      detail: 0,
    }
    projectProfile.value = null
    projection.value = null
    proposalBundles.value = []
    selectedBundleId.value = null
    selectedBundleDetail.value = null
    loading.value = false
    loaded.value = false
    error.value = ''
    activeSubmissionCount.value = 0
    pendingActionCounts.value = {}
    subjectKnowledge.value = null
    selectedSubjectRef.value = null
    chapterSnapshot.value = null
    selectedChapterIndex.value = null
    bundlesTotal.value = 0
    bundlesOffset.value = 0
    bundleFilters.value = {}
  }

  async function loadSetupPanelData(projectId: string) {
    const snapshot = captureRequest(projectId, ['overview', 'bundles', 'detail'])
    loading.value = true
    error.value = ''

    try {
      const [overview, bundlesPage] = await Promise.all([
        api.getWorldModelOverview(projectId),
        api.listWorldProposalBundles(projectId, {
          offset: bundlesOffset.value,
          limit: bundlesLimit.value,
          ...bundleFilters.value,
        }),
      ])
      if (!isLatestRequest(snapshot, 'overview') || !isLatestRequest(snapshot, 'bundles')) return

      projectProfile.value = overview.project_profile
      projection.value = overview.projection
      proposalBundles.value = bundlesPage.items
      bundlesTotal.value = bundlesPage.total
      loaded.value = true

      const nextSelectedBundleId =
        (selectedBundleId.value && bundlesPage.items.some((bundle) => bundle.id === selectedBundleId.value))
          ? selectedBundleId.value
          : bundlesPage.items[0]?.id ?? null
      selectedBundleId.value = nextSelectedBundleId

      if (nextSelectedBundleId) {
        const detailError = await loadBundleDetail(projectId, nextSelectedBundleId, {
          requestSnapshot: snapshot,
          clearOnFailure: true,
          suppressError: true,
        })
        if (isLatestRequest(snapshot, 'detail')) {
          error.value = detailError
        }
      } else if (isLatestRequest(snapshot, 'detail')) {
        selectedBundleDetail.value = null
      }
    } catch (err) {
      if (!isLatestRequest(snapshot, 'overview') && !isLatestRequest(snapshot, 'bundles')) return
      error.value = toErrorMessage(err)
      loaded.value = true
    } finally {
      if (isLatestRequest(snapshot, 'overview')) {
        loading.value = false
      }
    }
  }

  async function loadBundleDetail(projectId: string, bundleId: string, options: BundleDetailLoadOptions = {}) {
    const snapshot = options.requestSnapshot ?? captureRequest(projectId, ['detail'])

    try {
      const detail = await api.getWorldProposalBundle(projectId, bundleId)
      if (!isLatestRequest(snapshot, 'detail')) return ''
      selectedBundleId.value = bundleId
      selectedBundleDetail.value = detail
      if (!options.suppressError) {
        error.value = ''
      }
      return ''
    } catch (err) {
      const nextError = toErrorMessage(err)
      if (!isLatestRequest(snapshot, 'detail')) return nextError
      selectedBundleId.value = bundleId
      if (options.clearOnFailure) {
        selectedBundleDetail.value = null
      }
      if (!options.suppressError) {
        error.value = nextError
      }
      return nextError
    }
  }

  async function selectBundle(projectId: string, bundleId: string) {
    ensureProjectScope(projectId)
    await loadBundleDetail(projectId, bundleId, { clearOnFailure: true })
  }

  async function refreshBundles(projectId: string, requestSnapshot?: RequestSnapshot) {
    const snapshot = requestSnapshot ?? captureRequest(projectId, ['bundles'])
    const page = await api.listWorldProposalBundles(projectId, {
      offset: 0,
      limit: bundlesOffset.value + bundlesLimit.value,
      ...bundleFilters.value,
    })
    if (!isLatestRequest(snapshot, 'bundles')) return
    proposalBundles.value = page.items
    bundlesTotal.value = page.total
    bundlesOffset.value = Math.max(0, page.items.length - bundlesLimit.value)
    if (selectedBundleId.value && !page.items.some((bundle) => bundle.id === selectedBundleId.value)) {
      selectedBundleId.value = page.items[0]?.id ?? null
    }
  }

  async function loadMoreBundles(projectId: string) {
    ensureProjectScope(projectId)
    const nextOffset = bundlesOffset.value + bundlesLimit.value
    try {
      const page = await api.listWorldProposalBundles(projectId, {
        offset: nextOffset,
        limit: bundlesLimit.value,
        ...bundleFilters.value,
      })
      proposalBundles.value = [...proposalBundles.value, ...page.items]
      bundlesOffset.value = nextOffset
      bundlesTotal.value = page.total
    } catch (err) {
      error.value = toErrorMessage(err)
    }
  }

  async function applyBundleFilters(projectId: string, filters: typeof bundleFilters.value) {
    bundleFilters.value = filters
    bundlesOffset.value = 0
    await loadSetupPanelData(projectId)
  }

  async function refreshOverview(projectId: string, requestSnapshot?: RequestSnapshot) {
    const snapshot = requestSnapshot ?? captureRequest(projectId, ['overview'])
    const overview = await api.getWorldModelOverview(projectId)
    if (!isLatestRequest(snapshot, 'overview')) return
    projectProfile.value = overview.project_profile
    projection.value = overview.projection
  }

  async function refreshAfterReviewAction(projectId: string) {
    const snapshot = captureRequest(projectId, ['overview', 'bundles', 'detail'])
    let refreshError = ''

    try {
      await refreshOverview(projectId, snapshot)
    } catch (err) {
      refreshError = captureRefreshError(refreshError, err)
    }

    try {
      await refreshBundles(projectId, snapshot)
    } catch (err) {
      refreshError = captureRefreshError(refreshError, err)
    }

    if (selectedBundleId.value) {
      const detailError = await loadBundleDetail(projectId, selectedBundleId.value, {
        requestSnapshot: snapshot,
        suppressError: true,
      })
      if (detailError) {
        refreshError = captureRefreshError(refreshError, detailError)
      }
    } else if (isLatestRequest(snapshot, 'detail')) {
      selectedBundleDetail.value = null
    }

    assignErrorForSnapshot(snapshot, ['overview', 'bundles', 'detail'], refreshError)
  }

  async function reviewProposalItem(projectId: string, itemId: string, payload: ProposalReviewRequest) {
    ensureProjectScope(projectId)
    const scope = captureScope(projectId)
    beginAction(itemId)
    try {
      await api.reviewWorldProposalItem(projectId, itemId, payload)
      await refreshAfterReviewAction(projectId)
    } catch (err) {
      assignErrorForScope(scope.projectId, scope.version, toErrorMessage(err))
    } finally {
      finishAction(itemId)
    }
  }

  async function splitProposalBundle(projectId: string, bundleId: string, payload: ProposalSplitRequest) {
    ensureProjectScope(projectId)
    const scope = captureScope(projectId)
    const actionItemId = payload.item_ids[0] ?? null
    beginAction(actionItemId)
    try {
      const snapshot = captureRequest(projectId, ['bundles', 'detail'])
      let detail: ProposalBundleDetail
      try {
        detail = await api.splitWorldProposalBundle(projectId, bundleId, payload)
      } catch (err) {
        assignErrorForScope(scope.projectId, scope.version, toErrorMessage(err))
        return
      }
      if (!isLatestRequest(snapshot, 'detail')) return
      selectedBundleId.value = detail.bundle.id
      selectedBundleDetail.value = detail

      let refreshError = ''
      try {
        await refreshBundles(projectId, snapshot)
      } catch (err) {
        refreshError = captureRefreshError(refreshError, err)
      }
      assignErrorForSnapshot(snapshot, ['bundles', 'detail'], refreshError)
    } finally {
      finishAction(actionItemId)
    }
  }

  async function rollbackProposalReview(
    projectId: string,
    reviewId: string,
    payload: ProposalRollbackRequest,
    itemId?: string,
  ) {
    ensureProjectScope(projectId)
    const scope = captureScope(projectId)
    beginAction(itemId)
    try {
      await api.rollbackWorldProposalReview(projectId, reviewId, payload)
      await refreshAfterReviewAction(projectId)
    } catch (err) {
      assignErrorForScope(scope.projectId, scope.version, toErrorMessage(err))
    } finally {
      finishAction(itemId)
    }
  }

  return {
    projectProfile,
    projection,
    proposalBundles,
    selectedBundleId,
    selectedBundleDetail,
    subjectKnowledge,
    selectedSubjectRef,
    chapterSnapshot,
    selectedChapterIndex,
    reviewerName,
    bundlesTotal,
    bundlesOffset,
    bundlesLimit,
    bundleFilters,
    loading,
    loaded,
    error,
    submitting,
    pendingActionCounts,
    activeActionItemId,
    hasWorldData,
    isActionPending,
    resetProjectScopedState,
    loadSetupPanelData,
    selectBundle,
    loadSubjectKnowledge,
    loadChapterSnapshot,
    loadMoreBundles,
    applyBundleFilters,
    setReviewerName,
    reviewProposalItem,
    splitProposalBundle,
    rollbackProposalReview,
  }
})
