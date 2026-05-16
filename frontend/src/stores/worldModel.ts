import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api } from '../api/client'
import type {
  ProjectProfileVersion,
  ProposalBundle,
  ProposalBundleDetail,
  ProposalReviewQueue,
  ProposalReviewRequest,
  ProposalRollbackRequest,
  ProposalSplitRequest,
  WorldFactClaim,
  WorldModelDashboard,
  WorldModelOverviewQuery,
  WorldProjection,
} from '../api/types'

type RequestLane = 'dashboard' | 'overview' | 'facts' | 'bundles' | 'detail' | 'queue'
const FACT_CLAIMS_PAGE_SIZE = 200
const PROPOSAL_REVIEW_QUEUE_PAGE_SIZE = 200
const PROPOSAL_DETAIL_ITEM_PAGE_SIZE = 100
const PROPOSAL_DETAIL_ITEM_MAX_REFRESH_LIMIT = 500
const WORLD_MODEL_PROJECTION_WINDOW_QUERY: WorldModelOverviewQuery = {
  entity_offset: 0,
  entity_limit: 120,
  relation_offset: 0,
  relation_limit: 160,
  presence_offset: 0,
  presence_limit: 120,
  event_offset: 0,
  event_limit: 120,
  fact_subject_offset: 0,
  fact_subject_limit: 120,
}

interface RequestSnapshot {
  projectId: string
  version: number
  requestId: number
}

interface BundleDetailLoadOptions {
  clearOnFailure?: boolean
  suppressError?: boolean
  requestSnapshot?: RequestSnapshot
  itemLimit?: number
}

interface PendingActionCounts {
  [itemId: string]: number
}

type ProposalReviewQueueCluster = ProposalReviewQueue['clusters'][number]

export const useWorldModelStore = defineStore('worldModel', () => {
  const projectProfile = ref<ProjectProfileVersion | null>(null)
  const projection = ref<WorldProjection | null>(null)
  const factClaims = ref<WorldFactClaim[]>([])
  const factClaimsLoaded = ref(false)
  const factClaimsHasMore = ref(false)
  const dashboard = ref<WorldModelDashboard | null>(null)
  const proposalBundles = ref<ProposalBundle[]>([])
  const proposalBundlesLoaded = ref(false)
  const proposalReviewQueue = ref<ProposalReviewQueue | null>(null)
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
  const laneLoading = ref<Record<RequestLane, boolean>>({
    dashboard: false,
    overview: false,
    facts: false,
    bundles: false,
    detail: false,
    queue: false,
  })
  const loadingMoreBundles = ref(false)
  const loadingMoreFactClaims = ref(false)
  const loadingMoreProposalReviewQueue = ref(false)
  const loadingMoreBundleItems = ref(false)
  const loaded = ref(false)
  const error = ref('')
  const lastFactClaimsError = ref('')
  const activeSubmissionCount = ref(0)
  const pendingActionCounts = ref<PendingActionCounts>({})
  const currentProjectScope = ref('')
  const scopeVersion = ref(0)
  const nextRequestId = ref(0)
  let subjectKnowledgeRequestId = 0
  let chapterSnapshotRequestId = 0
  const latestLaneRequest = ref<Record<RequestLane, number>>({
    dashboard: 0,
    overview: 0,
    facts: 0,
    bundles: 0,
    detail: 0,
    queue: 0,
  })

  const hasWorldData = computed(() =>
    projectProfile.value !== null || projection.value !== null || factClaims.value.length > 0 || proposalBundles.value.length > 0,
  )
  const loading = computed(() => Object.values(laneLoading.value).some(Boolean))
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

  function setLaneLoading(lane: RequestLane, value: boolean) {
    laneLoading.value = {
      ...laneLoading.value,
      [lane]: value,
    }
  }

  function setLanesLoading(lanes: RequestLane[], value: boolean) {
    laneLoading.value = {
      ...laneLoading.value,
      ...Object.fromEntries(lanes.map((lane) => [lane, value])),
    } as Record<RequestLane, boolean>
  }

  function finishLatestLanes(snapshot: RequestSnapshot, lanes: RequestLane[]) {
    const next = { ...laneLoading.value }
    let changed = false
    for (const lane of lanes) {
      if (!isLatestRequest(snapshot, lane)) continue
      next[lane] = false
      changed = true
    }
    if (changed) laneLoading.value = next
  }

  function isLaneLoading(lane: RequestLane) {
    return laneLoading.value[lane]
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

  function normalizeFactClaimsPage(value: unknown, fallbackLimit: number) {
    if (Array.isArray(value)) {
      return {
        claims: value as WorldFactClaim[],
        hasMore: value.length === fallbackLimit,
      }
    }
    const payload = value as { claims?: unknown; has_more?: unknown } | null
    const claims = Array.isArray(payload?.claims) ? payload.claims as WorldFactClaim[] : []
    return {
      claims,
      hasMore: typeof payload?.has_more === 'boolean' ? payload.has_more : claims.length === fallbackLimit,
    }
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
    const scope = captureScope(projectId)
    const requestId = ++subjectKnowledgeRequestId
    selectedSubjectRef.value = subjectRef
    subjectKnowledge.value = null
    try {
      const overview = await api.getSubjectKnowledge(projectId, subjectRef)
      if (
        !isActiveScope(scope.projectId, scope.version)
        || subjectKnowledgeRequestId !== requestId
        || selectedSubjectRef.value !== subjectRef
      ) return
      subjectKnowledge.value = overview.projection
    } catch (err) {
      if (isActiveScope(scope.projectId, scope.version) && subjectKnowledgeRequestId === requestId) {
        error.value = toErrorMessage(err)
      }
    }
  }

  async function loadChapterSnapshot(projectId: string, chapterIndex: number) {
    const scope = captureScope(projectId)
    const requestId = ++chapterSnapshotRequestId
    selectedChapterIndex.value = chapterIndex
    chapterSnapshot.value = null
    try {
      const overview = await api.getChapterSnapshot(projectId, chapterIndex)
      if (
        !isActiveScope(scope.projectId, scope.version)
        || chapterSnapshotRequestId !== requestId
        || selectedChapterIndex.value !== chapterIndex
      ) return
      chapterSnapshot.value = overview.projection
    } catch (err) {
      if (isActiveScope(scope.projectId, scope.version) && chapterSnapshotRequestId === requestId) {
        error.value = toErrorMessage(err)
      }
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
      dashboard: 0,
      overview: 0,
      facts: 0,
      bundles: 0,
      detail: 0,
      queue: 0,
    }
    projectProfile.value = null
    projection.value = null
    factClaims.value = []
    factClaimsLoaded.value = false
    factClaimsHasMore.value = false
    dashboard.value = null
    proposalBundles.value = []
    proposalBundlesLoaded.value = false
    proposalReviewQueue.value = null
    selectedBundleId.value = null
    selectedBundleDetail.value = null
    setLanesLoading(['dashboard', 'overview', 'facts', 'bundles', 'detail', 'queue'], false)
    loadingMoreBundles.value = false
    loadingMoreFactClaims.value = false
    loadingMoreProposalReviewQueue.value = false
    loadingMoreBundleItems.value = false
    loaded.value = false
    error.value = ''
    lastFactClaimsError.value = ''
    activeSubmissionCount.value = 0
    pendingActionCounts.value = {}
    subjectKnowledgeRequestId += 1
    chapterSnapshotRequestId += 1
    subjectKnowledge.value = null
    selectedSubjectRef.value = null
    chapterSnapshot.value = null
    selectedChapterIndex.value = null
    bundlesTotal.value = 0
    bundlesOffset.value = 0
    bundleFilters.value = {}
  }

  function invalidateFactClaims() {
    factClaims.value = []
    factClaimsLoaded.value = false
    factClaimsHasMore.value = false
  }

  async function loadSetupPanelData(projectId: string) {
    const snapshot = captureRequest(projectId, ['overview', 'bundles', 'detail', 'queue'])
    setLanesLoading(['overview', 'bundles', 'detail', 'queue'], true)
    error.value = ''

    try {
      const [overview, bundlesPage, reviewQueue] = await Promise.all([
        api.getWorldModelOverview(projectId, WORLD_MODEL_PROJECTION_WINDOW_QUERY),
        api.listWorldProposalBundles(projectId, {
          offset: bundlesOffset.value,
          limit: bundlesLimit.value,
          ...bundleFilters.value,
        }),
        api.getWorldProposalReviewQueue(projectId, { offset: 0, limit: PROPOSAL_REVIEW_QUEUE_PAGE_SIZE }),
      ])
      if (!isLatestRequest(snapshot, 'overview') || !isLatestRequest(snapshot, 'bundles') || !isLatestRequest(snapshot, 'queue')) return

      projectProfile.value = overview.project_profile
      projection.value = overview.projection
      proposalBundles.value = bundlesPage.items
      bundlesTotal.value = bundlesPage.total
      proposalReviewQueue.value = normalizeProposalReviewQueue(reviewQueue)
      proposalBundlesLoaded.value = true
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
      proposalBundlesLoaded.value = false
    } finally {
      finishLatestLanes(snapshot, ['overview', 'bundles', 'detail', 'queue'])
    }
  }

  async function loadOverview(projectId: string) {
    ensureProjectScope(projectId)
    const snapshot = captureRequest(projectId, ['overview'])
    setLaneLoading('overview', true)
    error.value = ''

    try {
      const overview = await api.getWorldModelOverview(projectId, WORLD_MODEL_PROJECTION_WINDOW_QUERY)
      if (!isLatestRequest(snapshot, 'overview')) return
      projectProfile.value = overview.project_profile
      projection.value = overview.projection
      loaded.value = true
    } catch (err) {
      assignErrorForSnapshot(snapshot, ['overview'], toErrorMessage(err))
      loaded.value = true
    } finally {
      finishLatestLanes(snapshot, ['overview'])
    }
  }

  async function loadFactClaims(projectId: string) {
    const snapshot = captureRequest(projectId, ['facts'])
    setLaneLoading('facts', true)

    try {
      const response = await api.listWorldFactClaims(projectId, { offset: 0, limit: FACT_CLAIMS_PAGE_SIZE })
      if (!isLatestRequest(snapshot, 'facts')) return
      const page = normalizeFactClaimsPage(response, FACT_CLAIMS_PAGE_SIZE)
      factClaims.value = page.claims
      factClaimsHasMore.value = page.hasMore
      factClaimsLoaded.value = true
      if (lastFactClaimsError.value && error.value === lastFactClaimsError.value) {
        error.value = ''
      }
      lastFactClaimsError.value = ''
    } catch (err) {
      if (!isLatestRequest(snapshot, 'facts')) return
      factClaimsLoaded.value = false
      factClaimsHasMore.value = false
      const nextError = toErrorMessage(err)
      lastFactClaimsError.value = nextError
      error.value = nextError
    } finally {
      finishLatestLanes(snapshot, ['facts'])
    }
  }

  async function loadMoreFactClaims(projectId: string) {
    if (loadingMoreFactClaims.value || !factClaimsHasMore.value) return
    const scope = captureScope(projectId)
    loadingMoreFactClaims.value = true

    try {
      const response = await api.listWorldFactClaims(projectId, {
        offset: factClaims.value.length,
        limit: FACT_CLAIMS_PAGE_SIZE,
      })
      if (!isActiveScope(scope.projectId, scope.version)) return
      const page = normalizeFactClaimsPage(response, FACT_CLAIMS_PAGE_SIZE)
      factClaims.value = [...factClaims.value, ...page.claims]
      factClaimsHasMore.value = page.hasMore
      factClaimsLoaded.value = true
      if (lastFactClaimsError.value && error.value === lastFactClaimsError.value) {
        error.value = ''
      }
      lastFactClaimsError.value = ''
    } catch (err) {
      if (isActiveScope(scope.projectId, scope.version)) {
        const nextError = toErrorMessage(err)
        lastFactClaimsError.value = nextError
        error.value = nextError
      }
    } finally {
      if (isActiveScope(scope.projectId, scope.version)) {
        loadingMoreFactClaims.value = false
      }
    }
  }

  async function loadDashboard(projectId: string) {
    const snapshot = captureRequest(projectId, ['dashboard'])
    setLaneLoading('dashboard', true)
    error.value = ''

    try {
      const nextDashboard = await api.getWorldModelDashboard(projectId)
      if (!isLatestRequest(snapshot, 'dashboard')) return
      dashboard.value = nextDashboard
      projectProfile.value = nextDashboard.project_profile
    } catch (err) {
      assignErrorForSnapshot(snapshot, ['dashboard'], toErrorMessage(err))
    } finally {
      finishLatestLanes(snapshot, ['dashboard'])
    }
  }

  async function loadBundleDetail(projectId: string, bundleId: string, options: BundleDetailLoadOptions = {}) {
    const snapshot = options.requestSnapshot ?? captureRequest(projectId, ['detail'])
    const ownsDetailLane = !options.requestSnapshot
    if (ownsDetailLane) setLaneLoading('detail', true)
    const itemLimit = Math.min(
      PROPOSAL_DETAIL_ITEM_MAX_REFRESH_LIMIT,
      Math.max(PROPOSAL_DETAIL_ITEM_PAGE_SIZE, options.itemLimit ?? PROPOSAL_DETAIL_ITEM_PAGE_SIZE),
    )

    try {
      const detail = await api.getWorldProposalBundle(projectId, bundleId, {
        item_offset: 0,
        item_limit: itemLimit,
      })
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
    } finally {
      if (ownsDetailLane) finishLatestLanes(snapshot, ['detail'])
    }
  }

  async function selectBundle(projectId: string, bundleId: string) {
    ensureProjectScope(projectId)
    await loadBundleDetail(projectId, bundleId, { clearOnFailure: true })
  }

  function mergeBundleDetailItems(current: ProposalBundleDetail, page: ProposalBundleDetail): ProposalBundleDetail {
    const seenItemIds = new Set(current.items.map((item) => item.id))
    const items = [
      ...current.items,
      ...page.items.filter((item) => !seenItemIds.has(item.id)),
    ]
    const seenReviewIds = new Set(current.reviews.map((review) => review.id))
    const reviews = [
      ...current.reviews,
      ...page.reviews.filter((review) => !seenReviewIds.has(review.id)),
    ]
    const conflictKey = (conflict: { item_id: string; conflict_type: string; detail: string }) =>
      `${conflict.item_id}:${conflict.conflict_type}:${conflict.detail}`
    const seenConflictKeys = new Set(current.conflicts.map(conflictKey))
    const conflicts = [
      ...current.conflicts,
      ...page.conflicts.filter((conflict) => !seenConflictKeys.has(conflictKey(conflict))),
    ]
    return {
      ...page,
      items,
      items_total: page.items_total ?? current.items_total ?? items.length,
      items_offset: 0,
      items_limit: items.length,
      reviews,
      conflicts,
    }
  }

  async function loadMoreBundleDetailItems(projectId: string) {
    const current = selectedBundleDetail.value
    const bundleId = selectedBundleId.value ?? current?.bundle.id
    if (!current || !bundleId || loadingMoreBundleItems.value) return
    const total = current.items_total ?? current.items.length
    if (current.items.length >= total) return

    ensureProjectScope(projectId)
    const scope = {
      projectId,
      version: scopeVersion.value,
    }
    const nextOffset = current.items.length
    loadingMoreBundleItems.value = true
    try {
      const page = await api.getWorldProposalBundle(projectId, bundleId, {
        item_offset: nextOffset,
        item_limit: PROPOSAL_DETAIL_ITEM_PAGE_SIZE,
      })
      if (!isActiveScope(scope.projectId, scope.version) || selectedBundleId.value !== bundleId) return
      selectedBundleDetail.value = mergeBundleDetailItems(current, page)
      error.value = ''
    } catch (err) {
      if (isActiveScope(scope.projectId, scope.version) && selectedBundleId.value === bundleId) {
        error.value = toErrorMessage(err)
      }
    } finally {
      if (isActiveScope(scope.projectId, scope.version) && selectedBundleId.value === bundleId) {
        loadingMoreBundleItems.value = false
      }
    }
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
    proposalBundlesLoaded.value = true
    bundlesTotal.value = page.total
    bundlesOffset.value = Math.max(0, page.items.length - bundlesLimit.value)
    if (selectedBundleId.value && !page.items.some((bundle) => bundle.id === selectedBundleId.value)) {
      selectedBundleId.value = page.items[0]?.id ?? null
    }
  }

  async function refreshProposalReviewQueue(projectId: string, requestSnapshot?: RequestSnapshot) {
    const snapshot = requestSnapshot ?? captureRequest(projectId, ['queue'])
    const queue = await api.getWorldProposalReviewQueue(projectId, { offset: 0, limit: PROPOSAL_REVIEW_QUEUE_PAGE_SIZE })
    if (!isLatestRequest(snapshot, 'queue')) return
    proposalReviewQueue.value = normalizeProposalReviewQueue(queue)
  }

  function proposalReviewQueueReturnedItems(queue: ProposalReviewQueue) {
    return queue.returned_items
      ?? queue.clusters.reduce((total, cluster) => total + Math.max(0, cluster.candidate_count), 0)
  }

  function normalizeProposalReviewQueue(queue: ProposalReviewQueue): ProposalReviewQueue {
    const offset = queue.offset ?? 0
    const limit = queue.limit ?? PROPOSAL_REVIEW_QUEUE_PAGE_SIZE
    const returnedItems = proposalReviewQueueReturnedItems(queue)
    return {
      ...queue,
      offset,
      limit,
      returned_items: returnedItems,
      has_more: queue.has_more ?? offset + returnedItems < queue.total_items,
    }
  }

  function uniqueStrings(values: string[]) {
    return Array.from(new Set(values))
  }

  function mergeChapterRange(
    current: ProposalReviewQueueCluster['chapter_range'],
    next: ProposalReviewQueueCluster['chapter_range'],
  ) {
    const starts = [current.start, next.start].filter((value): value is number => value !== null)
    const ends = [current.end, next.end].filter((value): value is number => value !== null)
    return {
      start: starts.length ? Math.min(...starts) : null,
      end: ends.length ? Math.max(...ends) : null,
    }
  }

  function mergeProposalReviewQueueClusters(clusters: ProposalReviewQueueCluster[]) {
    const merged: ProposalReviewQueueCluster[] = []
    const indexByClusterId = new Map<string, number>()
    for (const cluster of clusters) {
      const existingIndex = indexByClusterId.get(cluster.cluster_id)
      if (existingIndex === undefined) {
        indexByClusterId.set(cluster.cluster_id, merged.length)
        merged.push({
          ...cluster,
          item_ids: uniqueStrings(cluster.item_ids),
          bundle_ids: uniqueStrings(cluster.bundle_ids),
          subject_refs: uniqueStrings(cluster.subject_refs),
        })
        continue
      }

      const existing = merged[existingIndex]
      const itemIds = uniqueStrings([...existing.item_ids, ...cluster.item_ids])
      merged[existingIndex] = {
        ...existing,
        candidate_count: itemIds.length || existing.candidate_count + cluster.candidate_count,
        item_ids: itemIds,
        bundle_ids: uniqueStrings([...existing.bundle_ids, ...cluster.bundle_ids]),
        subject_refs: uniqueStrings([...existing.subject_refs, ...cluster.subject_refs]),
        chapter_range: mergeChapterRange(existing.chapter_range, cluster.chapter_range),
      }
    }
    return merged
  }

  function mergeProposalReviewQueue(current: ProposalReviewQueue, page: ProposalReviewQueue): ProposalReviewQueue {
    const normalizedCurrent = normalizeProposalReviewQueue(current)
    const normalizedPage = normalizeProposalReviewQueue(page)
    return {
      ...normalizedPage,
      offset: normalizedCurrent.offset,
      limit: normalizedPage.limit ?? normalizedCurrent.limit,
      returned_items: proposalReviewQueueReturnedItems(normalizedCurrent) + proposalReviewQueueReturnedItems(normalizedPage),
      clusters: mergeProposalReviewQueueClusters([
        ...normalizedCurrent.clusters,
        ...normalizedPage.clusters,
      ]),
    }
  }

  async function loadMoreProposalReviewQueue(projectId: string) {
    const current = proposalReviewQueue.value
    if (loadingMoreProposalReviewQueue.value || !current) return
    const normalizedCurrent = normalizeProposalReviewQueue(current)
    if (!normalizedCurrent.has_more) return
    const nextOffset = (normalizedCurrent.offset ?? 0) + proposalReviewQueueReturnedItems(normalizedCurrent)
    if (nextOffset <= (normalizedCurrent.offset ?? 0)) return

    const scope = captureScope(projectId)
    loadingMoreProposalReviewQueue.value = true
    try {
      const page = await api.getWorldProposalReviewQueue(projectId, {
        offset: nextOffset,
        limit: normalizedCurrent.limit ?? PROPOSAL_REVIEW_QUEUE_PAGE_SIZE,
      })
      if (!isActiveScope(scope.projectId, scope.version)) return
      proposalReviewQueue.value = mergeProposalReviewQueue(normalizedCurrent, page)
      error.value = ''
    } catch (err) {
      if (isActiveScope(scope.projectId, scope.version)) {
        error.value = toErrorMessage(err)
      }
    } finally {
      if (isActiveScope(scope.projectId, scope.version)) {
        loadingMoreProposalReviewQueue.value = false
      }
    }
  }

  async function loadMoreBundles(projectId: string) {
    if (loadingMoreBundles.value) return
    const scope = captureScope(projectId)
    const nextOffset = bundlesOffset.value + bundlesLimit.value
    loadingMoreBundles.value = true
    try {
      const page = await api.listWorldProposalBundles(projectId, {
        offset: nextOffset,
        limit: bundlesLimit.value,
        ...bundleFilters.value,
      })
      if (!isActiveScope(scope.projectId, scope.version)) return
      proposalBundles.value = [...proposalBundles.value, ...page.items]
      proposalBundlesLoaded.value = true
      bundlesOffset.value = nextOffset
      bundlesTotal.value = page.total
    } catch (err) {
      if (isActiveScope(scope.projectId, scope.version)) {
        error.value = toErrorMessage(err)
      }
    } finally {
      if (isActiveScope(scope.projectId, scope.version)) {
        loadingMoreBundles.value = false
      }
    }
  }

  async function applyBundleFilters(projectId: string, filters: typeof bundleFilters.value) {
    bundleFilters.value = filters
    bundlesOffset.value = 0
    await loadSetupPanelData(projectId)
  }

  async function refreshOverview(projectId: string, requestSnapshot?: RequestSnapshot) {
    const snapshot = requestSnapshot ?? captureRequest(projectId, ['overview'])
    const overview = await api.getWorldModelOverview(projectId, WORLD_MODEL_PROJECTION_WINDOW_QUERY)
    if (!isLatestRequest(snapshot, 'overview')) return
    projectProfile.value = overview.project_profile
    projection.value = overview.projection
  }

  async function refreshDashboard(projectId: string, requestSnapshot?: RequestSnapshot) {
    const snapshot = requestSnapshot ?? captureRequest(projectId, ['dashboard'])
    const nextDashboard = await api.getWorldModelDashboard(projectId)
    if (!isLatestRequest(snapshot, 'dashboard')) return
    dashboard.value = nextDashboard
    projectProfile.value = nextDashboard.project_profile
  }

  async function refreshAfterReviewAction(projectId: string) {
    const snapshot = captureRequest(projectId, ['dashboard', 'overview', 'bundles', 'detail', 'queue'])
    setLanesLoading(['dashboard', 'overview', 'bundles', 'detail', 'queue'], true)
    invalidateFactClaims()
    let refreshError = ''

    try {
      await refreshDashboard(projectId, snapshot)
    } catch (err) {
      refreshError = captureRefreshError(refreshError, err)
    }

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

    try {
      await refreshProposalReviewQueue(projectId, snapshot)
    } catch (err) {
      refreshError = captureRefreshError(refreshError, err)
    }

    if (selectedBundleId.value) {
      const itemLimit = selectedBundleDetail.value
        ? selectedBundleDetail.value.items.length
        : PROPOSAL_DETAIL_ITEM_PAGE_SIZE
      const detailError = await loadBundleDetail(projectId, selectedBundleId.value, {
        requestSnapshot: snapshot,
        suppressError: true,
        itemLimit,
      })
      if (detailError) {
        refreshError = captureRefreshError(refreshError, detailError)
      }
    } else if (isLatestRequest(snapshot, 'detail')) {
      selectedBundleDetail.value = null
    }

    assignErrorForSnapshot(snapshot, ['dashboard', 'overview', 'bundles', 'detail', 'queue'], refreshError)
    finishLatestLanes(snapshot, ['dashboard', 'overview', 'bundles', 'detail', 'queue'])
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
      const snapshot = captureRequest(projectId, ['bundles', 'detail', 'queue'])
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
      try {
        await refreshProposalReviewQueue(projectId, snapshot)
      } catch (err) {
        refreshError = captureRefreshError(refreshError, err)
      }
      assignErrorForSnapshot(snapshot, ['bundles', 'detail', 'queue'], refreshError)
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
    factClaims,
    factClaimsLoaded,
    factClaimsHasMore,
    dashboard,
    proposalBundles,
    proposalBundlesLoaded,
    proposalReviewQueue,
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
    laneLoading,
    loadingMoreBundles,
    loadingMoreFactClaims,
    loadingMoreProposalReviewQueue,
    loadingMoreBundleItems,
    loading,
    loaded,
    error,
    submitting,
    pendingActionCounts,
    activeActionItemId,
    hasWorldData,
    isLaneLoading,
    isActionPending,
    resetProjectScopedState,
    loadDashboard,
    loadOverview,
    loadFactClaims,
    loadMoreFactClaims,
    loadSetupPanelData,
    loadMoreProposalReviewQueue,
    selectBundle,
    loadMoreBundleDetailItems,
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
