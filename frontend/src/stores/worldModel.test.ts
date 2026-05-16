import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWorldModelStore } from './worldModel'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getWorldModelOverview: vi.fn(),
    getWorldModelDashboard: vi.fn(),
    listWorldFactClaims: vi.fn(),
    getSubjectKnowledge: vi.fn(),
    getChapterSnapshot: vi.fn(),
    listWorldProposalBundles: vi.fn(),
    getWorldProposalReviewQueue: vi.fn(),
    getWorldProposalBundle: vi.fn(),
    reviewWorldProposalItem: vi.fn(),
    splitWorldProposalBundle: vi.fn(),
    rollbackWorldProposalReview: vi.fn(),
  },
}))

function createDeferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

const overviewWindowQuery = {
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

function createOverview(rank: string, version = 1) {
  return {
    project_profile: {
      id: `profile-${version}`,
      project_id: 'project-1',
      genre_profile_id: 'genre-1',
      version,
      contract_version: 'world.contract.v1',
      profile_payload: {},
      created_at: '2026-04-20T00:00:00Z',
    },
    projection: {
      view_type: 'current_truth',
      entities: {
        'char.hero': {
          entity_type: 'character',
          attributes: { status: 'alive' },
        },
      },
      relations: {},
      presence: {},
      occurred_events: {},
      event_links: {},
      facts: {
        'char.hero': {
          rank,
        },
      },
    },
  }
}

function createDashboard(rank = 'captain', pendingItemCount = 0) {
  return {
    project_profile: createOverview(rank).project_profile,
    metrics: {
      entity_count: 1,
      fact_count: 1,
      presence_count: 0,
      event_count: 0,
      pending_bundle_count: pendingItemCount > 0 ? 1 : 0,
      pending_item_count: pendingItemCount,
    },
    next_action: {
      action: pendingItemCount > 0 ? 'review_proposals' : 'inspect_projection',
      label: pendingItemCount > 0 ? '处理待审世界模型提案' : '检查真相投影',
    },
  }
}

function createFactClaim() {
  return {
    id: 'fact-1',
    project_id: 'project-1',
    project_profile_version_id: 'profile-1',
    profile_version: 1,
    contract_version: 'world.contract.v1',
    claim_id: 'claim.hero.rank',
    chapter_index: 1,
    intra_chapter_seq: 1,
    subject_ref: 'char.hero',
    predicate: 'rank',
    object_ref_or_value: 'captain',
    claim_layer: 'truth',
    claim_status: 'confirmed',
    perspective_ref: null,
    disclosed_to_refs: ['char.hero'],
    valid_from_anchor_id: 'anchor.1',
    valid_to_anchor_id: null,
    source_event_ref: 'event.hero.rank',
    evidence_refs: ['chapter.01'],
    authority_type: 'authoritative_structured',
    confidence: 0.9,
    notes: '',
    created_at: '2026-04-20T00:00:00Z',
  }
}

function createBundle(status = 'pending', version = 1) {
  return {
    id: 'bundle-1',
    project_id: 'project-1',
    project_profile_version_id: `profile-${version}`,
    profile_version: version,
    parent_bundle_id: null,
    bundle_status: status,
    title: '候选设定',
    summary: '',
    created_by: 'writer.alpha',
    created_at: '2026-04-20T00:00:00Z',
    updated_at: '2026-04-20T00:00:00Z',
  }
}

function createProposalReviewQueue() {
  return {
    project_id: 'project-1',
    profile_version: 1,
    total_items: 3,
    clusters: [
      {
        cluster_id: 'high:status:item-1',
        risk_level: 'high',
        review_mode: 'individual',
        candidate_count: 1,
        item_ids: ['item-1'],
        bundle_ids: ['bundle-1'],
        subject_refs: ['char.hero'],
        predicate: 'status',
        chapter_range: { start: 1, end: 1 },
        reason: '状态变化需要单独审阅。',
      },
      {
        cluster_id: 'low:presence_count:chapter:1',
        risk_level: 'low',
        review_mode: 'batch',
        candidate_count: 2,
        item_ids: ['item-2', 'item-3'],
        bundle_ids: ['bundle-1'],
        subject_refs: ['char.hero', 'char.sidekick'],
        predicate: 'presence_count',
        chapter_range: { start: 1, end: 1 },
        reason: '局部出场统计可批量审阅。',
      },
    ],
  }
}

function createBundleDetail(
  itemStatus = 'pending',
  reviewAction: string | null = null,
  approvedClaimId: string | null = null,
) {
  const bundleStatus =
    itemStatus === 'pending'
      ? 'pending'
      : itemStatus === 'rolled_back'
        ? 'rolled_back'
        : 'approved'
  return {
    bundle: createBundle(bundleStatus),
    items: [
      {
        id: 'item-1',
        bundle_id: 'bundle-1',
        parent_item_id: null,
        item_status: itemStatus,
        claim_id: 'claim.hero.rank',
        subject_ref: 'char.hero',
        predicate: 'rank',
        object_ref_or_value: 'captain',
        claim_layer: 'truth',
        evidence_refs: [],
        authority_type: 'authoritative_structured',
        confidence: 0.9,
        contract_version: 'world.contract.v1',
        approved_claim_id: approvedClaimId,
        created_by: 'writer.alpha',
        created_at: '2026-04-20T00:00:00Z',
      },
    ],
    reviews: reviewAction
      ? [
          {
            id: 'review-1',
            bundle_id: 'bundle-1',
            proposal_item_id: 'item-1',
            review_action: reviewAction,
            reviewer_ref: 'editor.alpha',
            reason: '通过',
            evidence_refs: ['chapter.01'],
            edited_fields: {},
            created_truth_claim_id: approvedClaimId,
            rollback_to_review_id: null,
            created_at: '2026-04-20T00:00:01Z',
          },
        ]
      : [],
    impact_snapshots: [],
    conflicts: [],
  }
}

function createBundleDetailWithItems(
  items: Array<{
    id: string
    item_status: string
    review_action?: string | null
    approved_claim_id?: string | null
    object_ref_or_value?: string
  }>,
) {
  return {
    bundle: createBundle(),
    items: items.map((item, index) => ({
      id: item.id,
      bundle_id: 'bundle-1',
      parent_item_id: null,
      item_status: item.item_status,
      claim_id: `claim.hero.rank.${index + 1}`,
      subject_ref: 'char.hero',
      predicate: 'rank',
      object_ref_or_value: item.object_ref_or_value ?? `rank-${index + 1}`,
      claim_layer: 'truth',
      evidence_refs: [],
      authority_type: 'authoritative_structured',
      confidence: 0.9,
      contract_version: 'world.contract.v1',
      approved_claim_id: item.approved_claim_id ?? null,
      created_by: 'writer.alpha',
      created_at: `2026-04-20T00:00:0${index + 1}Z`,
    })),
    reviews: items
      .filter((item) => item.review_action)
      .map((item, index) => ({
        id: `review-${index + 1}`,
        bundle_id: 'bundle-1',
        proposal_item_id: item.id,
        review_action: item.review_action!,
        reviewer_ref: 'editor.alpha',
        reason: '通过',
        evidence_refs: ['chapter.01'],
        edited_fields: {},
        created_truth_claim_id: item.approved_claim_id ?? null,
        rollback_to_review_id: null,
        created_at: `2026-04-20T00:00:1${index + 1}Z`,
      })),
    impact_snapshots: [],
    conflicts: [],
  }
}

describe('worldModel store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
    vi.mocked(api.getWorldModelDashboard).mockResolvedValue(createDashboard())
    vi.mocked(api.listWorldFactClaims).mockResolvedValue([])
    vi.mocked(api.getWorldProposalReviewQueue).mockResolvedValue({
      project_id: 'project-1',
      profile_version: 1,
      total_items: 0,
      clusters: [],
    })
  })

  it('loadOverview() 只加载 profile 和投影，不触发 proposal 列表请求', async () => {
    vi.mocked(api.getWorldModelOverview).mockResolvedValue(createOverview('captain'))
    const store = useWorldModelStore()

    await store.loadOverview('project-1')

    expect(store.projectProfile?.id).toBe('profile-1')
    expect(store.projection?.facts['char.hero'].rank).toBe('captain')
    expect(store.loaded).toBe(true)
    expect(store.proposalBundlesLoaded).toBe(false)
    expect(api.getWorldModelOverview).toHaveBeenCalledWith('project-1', overviewWindowQuery)
    expect(api.listWorldProposalBundles).not.toHaveBeenCalled()
    expect(api.getWorldProposalBundle).not.toHaveBeenCalled()
  })

  it('loadOverview() 请求有界 truth projection 窗口', async () => {
    vi.mocked(api.getWorldModelOverview).mockResolvedValue(createOverview('captain'))
    const store = useWorldModelStore()

    await store.loadOverview('project-1')

    expect(api.getWorldModelOverview).toHaveBeenCalledWith('project-1', overviewWindowQuery)
  })

  it('loadDashboard() 只加载 Athena Overview 指标，不触发 proposal 详情请求', async () => {
    vi.mocked(api.getWorldModelDashboard).mockResolvedValue({
      project_profile: createOverview('captain').project_profile,
      metrics: {
        entity_count: 1,
        fact_count: 1,
        presence_count: 0,
        event_count: 0,
        pending_bundle_count: 1,
        pending_item_count: 2,
      },
      next_action: {
        action: 'review_proposals',
        label: '处理待审世界模型提案',
      },
    })
    const store = useWorldModelStore()

    await store.loadDashboard('project-1')

    expect(store.dashboard?.metrics.pending_item_count).toBe(2)
    expect(store.dashboard?.next_action.action).toBe('review_proposals')
    expect(api.getWorldModelDashboard).toHaveBeenCalledWith('project-1')
    expect(api.getWorldProposalBundle).not.toHaveBeenCalled()
  })

  it('loadFactClaims() 分页加载事实声明元数据', async () => {
    vi.mocked(api.getWorldModelOverview).mockRejectedValue(new Error('overview failed'))
    vi.mocked(api.listWorldFactClaims).mockResolvedValue([createFactClaim()])
    const store = useWorldModelStore()

    await store.loadOverview('project-1')
    expect(store.error).toBe('overview failed')

    await store.loadFactClaims('project-1')

    expect(store.factClaimsLoaded).toBe(true)
    expect(store.factClaims[0].claim_id).toBe('claim.hero.rank')
    expect(store.factClaims[0].disclosed_to_refs).toEqual(['char.hero'])
    expect(store.error).toBe('overview failed')
    expect(store.factClaimsHasMore).toBe(false)
    expect(api.listWorldFactClaims).toHaveBeenCalledWith('project-1', { offset: 0, limit: 200 })
  })

  it('loadMoreFactClaims() appends the next facts page', async () => {
    const firstPage = Array.from({ length: 200 }, (_item, index) => ({
      ...createFactClaim(),
      id: `fact-${index + 1}`,
      claim_id: `claim.hero.rank.${index + 1}`,
    }))
    const secondPage = [
      {
        ...createFactClaim(),
        id: 'fact-201',
        claim_id: 'claim.hero.rank.201',
      },
    ]
    vi.mocked(api.listWorldFactClaims)
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce(secondPage)
    const store = useWorldModelStore()

    await store.loadFactClaims('project-1')
    expect(store.factClaims).toHaveLength(200)
    expect(store.factClaimsHasMore).toBe(true)

    await store.loadMoreFactClaims('project-1')

    expect(store.factClaims).toHaveLength(201)
    expect(store.factClaims[200].claim_id).toBe('claim.hero.rank.201')
    expect(store.factClaimsHasMore).toBe(false)
    expect(api.listWorldFactClaims).toHaveBeenNthCalledWith(1, 'project-1', { offset: 0, limit: 200 })
    expect(api.listWorldFactClaims).toHaveBeenNthCalledWith(2, 'project-1', { offset: 200, limit: 200 })
  })

  it('loadFactClaims() 使用后端 has_more 元数据避免整页误判', async () => {
    const page = Array.from({ length: 200 }, (_item, index) => ({
      ...createFactClaim(),
      id: `fact-${index + 1}`,
      claim_id: `claim.hero.rank.${index + 1}`,
    }))
    vi.mocked(api.listWorldFactClaims).mockResolvedValue({
      claims: page,
      total: 200,
      offset: 0,
      limit: 200,
      has_more: false,
    })
    const store = useWorldModelStore()

    await store.loadFactClaims('project-1')

    expect(store.factClaims).toHaveLength(200)
    expect(store.factClaimsHasMore).toBe(false)
  })

  it('tracks loading state per request lane', async () => {
    const dashboardRequest = createDeferred<ReturnType<typeof createDashboard>>()
    vi.mocked(api.getWorldModelDashboard).mockReturnValue(dashboardRequest.promise)
    const store = useWorldModelStore()

    const pending = store.loadDashboard('project-1')

    expect(store.isLaneLoading('dashboard')).toBe(true)
    expect(store.isLaneLoading('bundles')).toBe(false)
    expect(store.isLaneLoading('detail')).toBe(false)

    dashboardRequest.resolve(createDashboard())
    await pending

    expect(store.isLaneLoading('dashboard')).toBe(false)
  })

  it('prevents stale subject knowledge responses from overwriting the selected subject', async () => {
    const firstRequest = createDeferred<ReturnType<typeof createOverview>>()
    const secondRequest = createDeferred<ReturnType<typeof createOverview>>()
    vi.mocked(api.getSubjectKnowledge)
      .mockReturnValueOnce(firstRequest.promise)
      .mockReturnValueOnce(secondRequest.promise)
    const store = useWorldModelStore()

    const firstLoad = store.loadSubjectKnowledge('project-1', 'char.old')
    const secondLoad = store.loadSubjectKnowledge('project-1', 'char.new')

    secondRequest.resolve(createOverview('new-rank'))
    await secondLoad
    expect(store.selectedSubjectRef).toBe('char.new')
    expect(store.subjectKnowledge?.facts['char.hero'].rank).toBe('new-rank')

    firstRequest.resolve(createOverview('old-rank'))
    await firstLoad
    expect(store.selectedSubjectRef).toBe('char.new')
    expect(store.subjectKnowledge?.facts['char.hero'].rank).toBe('new-rank')
  })

  it('clears old subject knowledge while a new subject is loading', async () => {
    const nextRequest = createDeferred<ReturnType<typeof createOverview>>()
    vi.mocked(api.getSubjectKnowledge).mockReturnValue(nextRequest.promise)
    const store = useWorldModelStore()
    store.subjectKnowledge = createOverview('old-rank').projection

    const pending = store.loadSubjectKnowledge('project-1', 'char.new')

    expect(store.selectedSubjectRef).toBe('char.new')
    expect(store.subjectKnowledge).toBeNull()

    nextRequest.resolve(createOverview('new-rank'))
    await pending
    expect(store.subjectKnowledge?.facts['char.hero'].rank).toBe('new-rank')
  })

  it('prevents stale chapter snapshots from overwriting the selected chapter', async () => {
    const firstRequest = createDeferred<ReturnType<typeof createOverview>>()
    const secondRequest = createDeferred<ReturnType<typeof createOverview>>()
    vi.mocked(api.getChapterSnapshot)
      .mockReturnValueOnce(firstRequest.promise)
      .mockReturnValueOnce(secondRequest.promise)
    const store = useWorldModelStore()

    const firstLoad = store.loadChapterSnapshot('project-1', 1)
    const secondLoad = store.loadChapterSnapshot('project-1', 2)

    secondRequest.resolve(createOverview('chapter-two'))
    await secondLoad
    expect(store.selectedChapterIndex).toBe(2)
    expect(store.chapterSnapshot?.facts['char.hero'].rank).toBe('chapter-two')

    firstRequest.resolve(createOverview('chapter-one'))
    await firstLoad
    expect(store.selectedChapterIndex).toBe(2)
    expect(store.chapterSnapshot?.facts['char.hero'].rank).toBe('chapter-two')
  })

  it('clears old chapter snapshot while a new chapter snapshot is loading', async () => {
    const nextRequest = createDeferred<ReturnType<typeof createOverview>>()
    vi.mocked(api.getChapterSnapshot).mockReturnValue(nextRequest.promise)
    const store = useWorldModelStore()
    store.chapterSnapshot = createOverview('chapter-one').projection

    const pending = store.loadChapterSnapshot('project-1', 2)

    expect(store.selectedChapterIndex).toBe(2)
    expect(store.chapterSnapshot).toBeNull()

    nextRequest.resolve(createOverview('chapter-two'))
    await pending
    expect(store.chapterSnapshot?.facts['char.hero'].rank).toBe('chapter-two')
  })

  it('loadSetupPanelData() 会加载当前 profile、投影和 bundles，并默认选中首个 bundle', async () => {
    vi.mocked(api.getWorldModelOverview).mockResolvedValue({
      project_profile: {
        id: 'profile-1',
        project_id: 'project-1',
        genre_profile_id: 'genre-1',
        version: 3,
        contract_version: 'world.contract.v1',
        profile_payload: { theme: '雾海城邦' },
        created_at: '2026-04-20T00:00:00Z',
      },
      projection: {
        view_type: 'current_truth',
        entities: {
          'char.hero': {
            entity_type: 'character',
            attributes: { status: 'alive' },
          },
        },
        relations: {},
        presence: {},
        occurred_events: {},
        event_links: {},
        facts: {
          'char.hero': {
            rank: 'captain',
          },
        },
      },
    })
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue({
      items: [
        {
          id: 'bundle-1',
          project_id: 'project-1',
          project_profile_version_id: 'profile-1',
          profile_version: 3,
          parent_bundle_id: null,
          bundle_status: 'pending',
          title: '候选设定',
          summary: '',
          created_by: 'writer.alpha',
          created_at: '2026-04-20T00:00:00Z',
          updated_at: '2026-04-20T00:00:00Z',
        },
      ],
      total: 1,
      offset: 0,
      limit: 20,
    })
    vi.mocked(api.getWorldProposalBundle).mockResolvedValue({
      bundle: {
        id: 'bundle-1',
        project_id: 'project-1',
        project_profile_version_id: 'profile-1',
        profile_version: 3,
        parent_bundle_id: null,
        bundle_status: 'pending',
        title: '候选设定',
        summary: '',
        created_by: 'writer.alpha',
        created_at: '2026-04-20T00:00:00Z',
        updated_at: '2026-04-20T00:00:00Z',
      },
      items: [],
      reviews: [],
      impact_snapshots: [],
      conflicts: [],
    })

    const store = useWorldModelStore()
    await store.loadSetupPanelData('project-1')

    expect(store.projectProfile?.version).toBe(3)
    expect(store.projection?.facts['char.hero'].rank).toBe('captain')
    expect(store.proposalBundlesLoaded).toBe(true)
    expect(store.proposalBundles).toHaveLength(1)
    expect(store.selectedBundleId).toBe('bundle-1')
    expect(store.selectedBundleDetail?.bundle.id).toBe('bundle-1')
  })

  it('loadSetupPanelData() 会加载提案审阅队列聚合状态', async () => {
    vi.mocked(api.getWorldModelOverview).mockResolvedValue(createOverview('captain'))
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue({
      items: [createBundle()],
      total: 1,
      offset: 0,
      limit: 20,
    })
    vi.mocked(api.getWorldProposalBundle).mockResolvedValue(createBundleDetail())
    vi.mocked(api.getWorldProposalReviewQueue).mockResolvedValue(createProposalReviewQueue())
    const store = useWorldModelStore()

    await store.loadSetupPanelData('project-1')

    expect(api.getWorldProposalReviewQueue).toHaveBeenCalledWith('project-1', { offset: 0, limit: 200 })
    expect(store.proposalReviewQueue?.total_items).toBe(3)
    expect(store.proposalReviewQueue?.clusters.map((cluster) => cluster.risk_level)).toEqual(['high', 'low'])
  })

  it('loadMoreProposalReviewQueue() 使用 returned_items 追加下一段审阅队列窗口', async () => {
    const firstQueue = {
      project_id: 'project-1',
      profile_version: 1,
      total_items: 4,
      returned_items: 2,
      offset: 0,
      limit: 200,
      has_more: true,
      clusters: [
        {
          cluster_id: 'high:status:item-1',
          risk_level: 'high',
          review_mode: 'individual',
          candidate_count: 1,
          item_ids: ['item-1'],
          bundle_ids: ['bundle-1'],
          subject_refs: ['char.hero'],
          predicate: 'status',
          chapter_range: { start: 1, end: 1 },
          reason: '状态变化需要单独审阅。',
        },
        {
          cluster_id: 'medium:rank:item-2',
          risk_level: 'medium',
          review_mode: 'individual',
          candidate_count: 1,
          item_ids: ['item-2'],
          bundle_ids: ['bundle-1'],
          subject_refs: ['char.hero'],
          predicate: 'rank',
          chapter_range: { start: 2, end: 2 },
          reason: '等级变化需要单独审阅。',
        },
      ],
    }
    const secondQueue = {
      project_id: 'project-1',
      profile_version: 1,
      total_items: 4,
      returned_items: 2,
      offset: 2,
      limit: 200,
      has_more: false,
      clusters: [
        {
          cluster_id: 'low:presence_count:chapter:3',
          risk_level: 'low',
          review_mode: 'batch',
          candidate_count: 1,
          item_ids: ['item-3'],
          bundle_ids: ['bundle-1'],
          subject_refs: ['char.sidekick'],
          predicate: 'presence_count',
          chapter_range: { start: 3, end: 3 },
          reason: '出场统计可批量审阅。',
        },
        {
          cluster_id: 'low:presence_count:chapter:4',
          risk_level: 'low',
          review_mode: 'batch',
          candidate_count: 1,
          item_ids: ['item-4'],
          bundle_ids: ['bundle-1'],
          subject_refs: ['char.rival'],
          predicate: 'presence_count',
          chapter_range: { start: 4, end: 4 },
          reason: '出场统计可批量审阅。',
        },
      ],
    }
    vi.mocked(api.getWorldModelOverview).mockResolvedValue(createOverview('captain'))
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue({
      items: [createBundle()],
      total: 1,
      offset: 0,
      limit: 20,
    })
    vi.mocked(api.getWorldProposalBundle).mockResolvedValue(createBundleDetail())
    vi.mocked(api.getWorldProposalReviewQueue)
      .mockResolvedValueOnce(firstQueue)
      .mockResolvedValueOnce(secondQueue)
    const store = useWorldModelStore()

    await store.loadSetupPanelData('project-1')
    await store.loadMoreProposalReviewQueue('project-1')

    expect(api.getWorldProposalReviewQueue).toHaveBeenNthCalledWith(1, 'project-1', { offset: 0, limit: 200 })
    expect(api.getWorldProposalReviewQueue).toHaveBeenNthCalledWith(2, 'project-1', { offset: 2, limit: 200 })
    expect(store.proposalReviewQueue?.returned_items).toBe(4)
    expect(store.proposalReviewQueue?.has_more).toBe(false)
    expect(store.proposalReviewQueue?.clusters.map((cluster) => cluster.cluster_id)).toEqual([
      'high:status:item-1',
      'medium:rank:item-2',
      'low:presence_count:chapter:3',
      'low:presence_count:chapter:4',
    ])
    expect(store.loadingMoreProposalReviewQueue).toBe(false)
  })

  it('reviewProposalItem() 会执行审批并刷新 bundles 和当前 detail', async () => {
    const store = useWorldModelStore()
    store.projectProfile = createOverview('lieutenant').project_profile
    store.projection = createOverview('lieutenant').projection
    store.proposalBundles = [createBundle()]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetail()
    store.factClaims = [createFactClaim()]
    store.factClaimsLoaded = true
    vi.mocked(api.reviewWorldProposalItem).mockResolvedValue({
      id: 'review-1',
      bundle_id: 'bundle-1',
      proposal_item_id: 'item-1',
      review_action: 'approve',
      reviewer_ref: 'editor.alpha',
      reason: '通过',
      evidence_refs: ['chapter.01'],
      edited_fields: {},
      created_truth_claim_id: 'claim.hero.rank',
      rollback_to_review_id: null,
      created_at: '2026-04-20T00:00:01Z',
    })
    vi.mocked(api.getWorldModelOverview).mockResolvedValue(createOverview('captain'))
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue({ items: [createBundle('approved')], total: 1, offset: 0, limit: 20 })
    vi.mocked(api.getWorldProposalBundle).mockResolvedValue(
      createBundleDetail('approved', 'approve', 'claim.hero.rank'),
    )

    await store.reviewProposalItem('project-1', 'item-1', {
      reviewer_ref: 'editor.alpha',
      action: 'approve',
      reason: '通过',
      evidence_refs: ['chapter.01'],
      edited_fields: {},
    })

    expect(api.reviewWorldProposalItem).toHaveBeenCalledWith('project-1', 'item-1', {
      reviewer_ref: 'editor.alpha',
      action: 'approve',
      reason: '通过',
      evidence_refs: ['chapter.01'],
      edited_fields: {},
    })
    expect(api.getWorldModelDashboard).toHaveBeenCalledWith('project-1')
    expect(api.getWorldModelOverview).toHaveBeenCalledWith('project-1', overviewWindowQuery)
    expect(api.listWorldProposalBundles).toHaveBeenCalledWith('project-1', expect.any(Object))
    expect(api.getWorldProposalBundle).toHaveBeenCalledWith('project-1', 'bundle-1', {
      item_offset: 0,
      item_limit: 100,
    })
    expect(store.dashboard?.next_action.action).toBe('inspect_projection')
    expect(store.projection?.facts['char.hero'].rank).toBe('captain')
    expect(store.factClaimsLoaded).toBe(false)
    expect(store.factClaims).toEqual([])
    expect(store.proposalBundles[0].bundle_status).toBe('approved')
    expect(store.selectedBundleDetail?.items[0].item_status).toBe('approved')
    expect(store.selectedBundleDetail?.reviews[0].review_action).toBe('approve')
  })

  it('reviewProposalItem() 主请求失败时会显式写 error，且不会抛出 unhandled reject', async () => {
    const store = useWorldModelStore()
    store.projectProfile = createOverview('lieutenant').project_profile
    store.projection = createOverview('lieutenant').projection
    store.proposalBundles = [createBundle()]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetail()

    vi.mocked(api.reviewWorldProposalItem).mockRejectedValue(new Error('review request failed'))

    await expect(
      store.reviewProposalItem('project-1', 'item-1', {
        reviewer_ref: 'editor.alpha',
        action: 'approve',
        reason: '通过',
        evidence_refs: ['chapter.01'],
        edited_fields: {},
      }),
    ).resolves.toBeUndefined()

    expect(store.error).toBe('review request failed')
    expect(api.getWorldModelOverview).not.toHaveBeenCalled()
    expect(api.listWorldProposalBundles).not.toHaveBeenCalled()
    expect(api.getWorldProposalBundle).not.toHaveBeenCalled()
    expect(store.selectedBundleDetail?.items[0].item_status).toBe('pending')
  })

  it('同项目并发 loadSetupPanelData() 时，新请求结果必须赢，旧响应不能回写覆盖', async () => {
    const store = useWorldModelStore()
    const firstOverview = createDeferred<ReturnType<typeof createOverview>>()
    const secondOverview = createDeferred<ReturnType<typeof createOverview>>()
    const newerDetail = createDeferred<ReturnType<typeof createBundleDetail>>()
    const olderDetail = createDeferred<ReturnType<typeof createBundleDetail>>()

    vi.mocked(api.listWorldProposalBundles).mockResolvedValue({ items: [createBundle('approved', 2)], total: 1, offset: 0, limit: 20 })
    vi.mocked(api.getWorldModelOverview)
      .mockReturnValueOnce(firstOverview.promise)
      .mockReturnValueOnce(secondOverview.promise)
    vi.mocked(api.getWorldProposalBundle)
      .mockReturnValueOnce(newerDetail.promise)
      .mockReturnValueOnce(olderDetail.promise)

    const firstLoad = store.loadSetupPanelData('project-1')
    const secondLoad = store.loadSetupPanelData('project-1')

    secondOverview.resolve(createOverview('captain', 2))
    newerDetail.resolve({
      ...createBundleDetail('approved', 'approve', 'claim.hero.rank'),
      bundle: createBundle('approved', 2),
      items: [
        {
          ...createBundleDetail('approved', 'approve', 'claim.hero.rank').items[0],
          object_ref_or_value: 'captain',
        },
      ],
    })
    await secondLoad

    firstOverview.resolve(createOverview('lieutenant', 1))
    olderDetail.resolve({
      ...createBundleDetail('approved', 'approve', 'claim.hero.rank'),
      bundle: createBundle('approved', 1),
      items: [
        {
          ...createBundleDetail('approved', 'approve', 'claim.hero.rank').items[0],
          object_ref_or_value: 'lieutenant',
        },
      ],
    })
    await firstLoad

    expect(store.projectProfile?.version).toBe(2)
    expect(store.projection?.facts['char.hero'].rank).toBe('captain')
    expect(store.selectedBundleDetail?.bundle.profile_version).toBe(2)
    expect(store.selectedBundleDetail?.items[0].object_ref_or_value).toBe('captain')
  })

  it('selectBundle() 失败时会显式写 error，清空旧 detail，且不会抛出 unhandled reject', async () => {
    const store = useWorldModelStore()
    store.proposalBundles = [
      createBundle(),
      {
        ...createBundle('pending'),
        id: 'bundle-2',
      },
    ]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetail('approved', 'approve', 'claim.hero.rank')

    vi.mocked(api.getWorldProposalBundle).mockRejectedValue(new Error('detail load failed'))

    await expect(store.selectBundle('project-1', 'bundle-2')).resolves.toBeUndefined()

    expect(store.error).toBe('detail load failed')
    expect(store.selectedBundleId).toBe('bundle-2')
    expect(store.selectedBundleDetail).toBeNull()
  })

  it('reviewProposalItem() 在 overview refresh 失败时会显式写 error，并继续刷新 bundles/detail', async () => {
    const store = useWorldModelStore()
    store.projectProfile = createOverview('lieutenant').project_profile
    store.projection = createOverview('lieutenant').projection
    store.proposalBundles = [createBundle()]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetail()

    vi.mocked(api.reviewWorldProposalItem).mockResolvedValue({
      id: 'review-1',
      bundle_id: 'bundle-1',
      proposal_item_id: 'item-1',
      review_action: 'approve',
      reviewer_ref: 'editor.alpha',
      reason: '通过',
      evidence_refs: ['chapter.01'],
      edited_fields: {},
      created_truth_claim_id: 'claim.hero.rank',
      rollback_to_review_id: null,
      created_at: '2026-04-20T00:00:01Z',
    })
    vi.mocked(api.getWorldModelOverview).mockRejectedValue(new Error('overview refresh failed'))
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue({ items: [createBundle('approved')], total: 1, offset: 0, limit: 20 })
    vi.mocked(api.getWorldProposalBundle).mockResolvedValue(
      createBundleDetail('approved', 'approve', 'claim.hero.rank'),
    )

    await expect(
      store.reviewProposalItem('project-1', 'item-1', {
        reviewer_ref: 'editor.alpha',
        action: 'approve',
        reason: '通过',
        evidence_refs: ['chapter.01'],
        edited_fields: {},
      }),
    ).resolves.toBeUndefined()

    expect(store.error).toBe('overview refresh failed')
    expect(store.proposalBundles[0].bundle_status).toBe('approved')
    expect(store.selectedBundleDetail?.items[0].item_status).toBe('approved')
    expect(store.selectedBundleDetail?.reviews[0].review_action).toBe('approve')
  })

  it('reviewProposalItem() 在 bundles refresh 失败时会显式写 error，且不会抛出 unhandled reject', async () => {
    const store = useWorldModelStore()
    store.projectProfile = createOverview('lieutenant').project_profile
    store.projection = createOverview('lieutenant').projection
    store.proposalBundles = [createBundle()]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetail()

    vi.mocked(api.reviewWorldProposalItem).mockResolvedValue({
      id: 'review-1',
      bundle_id: 'bundle-1',
      proposal_item_id: 'item-1',
      review_action: 'approve',
      reviewer_ref: 'editor.alpha',
      reason: '通过',
      evidence_refs: ['chapter.01'],
      edited_fields: {},
      created_truth_claim_id: 'claim.hero.rank',
      rollback_to_review_id: null,
      created_at: '2026-04-20T00:00:01Z',
    })
    vi.mocked(api.getWorldModelOverview).mockResolvedValue(createOverview('captain'))
    vi.mocked(api.listWorldProposalBundles).mockRejectedValue(new Error('bundles refresh failed'))
    vi.mocked(api.getWorldProposalBundle).mockResolvedValue(
      createBundleDetail('approved', 'approve', 'claim.hero.rank'),
    )

    await expect(
      store.reviewProposalItem('project-1', 'item-1', {
        reviewer_ref: 'editor.alpha',
        action: 'approve',
        reason: '通过',
        evidence_refs: ['chapter.01'],
        edited_fields: {},
      }),
    ).resolves.toBeUndefined()

    expect(store.error).toBe('bundles refresh failed')
    expect(store.projection?.facts['char.hero'].rank).toBe('captain')
    expect(store.selectedBundleDetail?.items[0].item_status).toBe('approved')
    expect(store.selectedBundleDetail?.reviews[0].review_action).toBe('approve')
  })

  it('reviewProposalItem() 在 detail refresh 失败时会显式写 error，且不会抛出 unhandled reject', async () => {
    const store = useWorldModelStore()
    store.projectProfile = createOverview('lieutenant').project_profile
    store.projection = createOverview('lieutenant').projection
    store.proposalBundles = [createBundle()]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetail()

    vi.mocked(api.reviewWorldProposalItem).mockResolvedValue({
      id: 'review-1',
      bundle_id: 'bundle-1',
      proposal_item_id: 'item-1',
      review_action: 'approve',
      reviewer_ref: 'editor.alpha',
      reason: '通过',
      evidence_refs: ['chapter.01'],
      edited_fields: {},
      created_truth_claim_id: 'claim.hero.rank',
      rollback_to_review_id: null,
      created_at: '2026-04-20T00:00:01Z',
    })
    vi.mocked(api.getWorldModelOverview).mockResolvedValue(createOverview('captain'))
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue({ items: [createBundle('approved')], total: 1, offset: 0, limit: 20 })
    vi.mocked(api.getWorldProposalBundle).mockRejectedValue(new Error('detail refresh failed'))

    await expect(
      store.reviewProposalItem('project-1', 'item-1', {
        reviewer_ref: 'editor.alpha',
        action: 'approve',
        reason: '通过',
        evidence_refs: ['chapter.01'],
        edited_fields: {},
      }),
    ).resolves.toBeUndefined()

    expect(store.error).toBe('detail refresh failed')
    expect(store.projection?.facts['char.hero'].rank).toBe('captain')
    expect(store.proposalBundles[0].bundle_status).toBe('approved')
    expect(store.selectedBundleDetail?.items[0].item_status).toBe('pending')
  })

  it('rollbackProposalReview() 会刷新 overview，避免继续显示回滚前的旧 truth', async () => {
    const store = useWorldModelStore()
    store.projectProfile = createOverview('captain').project_profile
    store.projection = createOverview('captain').projection
    store.proposalBundles = [createBundle('approved')]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetail('approved', 'approve', 'claim.hero.rank')
    store.factClaims = [createFactClaim()]
    store.factClaimsLoaded = true

    vi.mocked(api.rollbackWorldProposalReview).mockResolvedValue({
      id: 'review-rollback-1',
      bundle_id: 'bundle-1',
      proposal_item_id: 'item-1',
      review_action: 'rollback',
      reviewer_ref: 'editor.alpha',
      reason: '新证据推翻旧结论',
      evidence_refs: ['chapter.02'],
      edited_fields: {},
      created_truth_claim_id: 'claim.hero.rank',
      rollback_to_review_id: 'review-1',
      created_at: '2026-04-20T00:00:02Z',
    })
    vi.mocked(api.getWorldModelOverview).mockResolvedValue(createOverview('lieutenant'))
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue({ items: [createBundle('rolled_back')], total: 1, offset: 0, limit: 20 })
    vi.mocked(api.getWorldProposalBundle).mockResolvedValue({
      ...createBundleDetail('rolled_back', 'rollback', 'claim.hero.rank'),
      bundle: createBundle('rolled_back'),
    })

    await store.rollbackProposalReview('project-1', 'review-1', {
      reviewer_ref: 'editor.alpha',
      reason: '新证据推翻旧结论',
      evidence_refs: ['chapter.02'],
    })

    expect(api.rollbackWorldProposalReview).toHaveBeenCalledWith('project-1', 'review-1', {
      reviewer_ref: 'editor.alpha',
      reason: '新证据推翻旧结论',
      evidence_refs: ['chapter.02'],
    })
    expect(api.getWorldModelOverview).toHaveBeenCalledWith('project-1', overviewWindowQuery)
    expect(store.projection?.facts['char.hero'].rank).toBe('lieutenant')
    expect(store.factClaimsLoaded).toBe(false)
    expect(store.factClaims).toEqual([])
    expect(store.proposalBundles[0].bundle_status).toBe('rolled_back')
    expect(store.selectedBundleDetail?.items[0].item_status).toBe('rolled_back')
    expect(store.selectedBundleDetail?.reviews[0].review_action).toBe('rollback')
  })

  it('rollbackProposalReview() 在 overview refresh 失败时会显式写 error，并继续刷新 bundles/detail', async () => {
    const store = useWorldModelStore()
    store.projectProfile = createOverview('captain').project_profile
    store.projection = createOverview('captain').projection
    store.proposalBundles = [createBundle('approved')]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetail('approved', 'approve', 'claim.hero.rank')

    vi.mocked(api.rollbackWorldProposalReview).mockResolvedValue({
      id: 'review-rollback-1',
      bundle_id: 'bundle-1',
      proposal_item_id: 'item-1',
      review_action: 'rollback',
      reviewer_ref: 'editor.alpha',
      reason: '新证据推翻旧结论',
      evidence_refs: ['chapter.02'],
      edited_fields: {},
      created_truth_claim_id: 'claim.hero.rank',
      rollback_to_review_id: 'review-1',
      created_at: '2026-04-20T00:00:02Z',
    })
    vi.mocked(api.getWorldModelOverview).mockRejectedValue(new Error('overview refresh failed'))
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue({ items: [createBundle('rolled_back')], total: 1, offset: 0, limit: 20 })
    vi.mocked(api.getWorldProposalBundle).mockResolvedValue({
      ...createBundleDetail('rolled_back', 'rollback', 'claim.hero.rank'),
      bundle: createBundle('rolled_back'),
    })

    await expect(
      store.rollbackProposalReview('project-1', 'review-1', {
        reviewer_ref: 'editor.alpha',
        reason: '新证据推翻旧结论',
        evidence_refs: ['chapter.02'],
      }),
    ).resolves.toBeUndefined()

    expect(store.error).toBe('overview refresh failed')
    expect(store.proposalBundles[0].bundle_status).toBe('rolled_back')
    expect(store.selectedBundleDetail?.items[0].item_status).toBe('rolled_back')
    expect(store.selectedBundleDetail?.reviews[0].review_action).toBe('rollback')
  })

  it('rollbackProposalReview() 在 detail refresh 失败时会显式写 error，且不会抛出 unhandled reject', async () => {
    const store = useWorldModelStore()
    store.projectProfile = createOverview('captain').project_profile
    store.projection = createOverview('captain').projection
    store.proposalBundles = [createBundle('approved')]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetail('approved', 'approve', 'claim.hero.rank')

    vi.mocked(api.rollbackWorldProposalReview).mockResolvedValue({
      id: 'review-rollback-1',
      bundle_id: 'bundle-1',
      proposal_item_id: 'item-1',
      review_action: 'rollback',
      reviewer_ref: 'editor.alpha',
      reason: '新证据推翻旧结论',
      evidence_refs: ['chapter.02'],
      edited_fields: {},
      created_truth_claim_id: 'claim.hero.rank',
      rollback_to_review_id: 'review-1',
      created_at: '2026-04-20T00:00:02Z',
    })
    vi.mocked(api.getWorldModelOverview).mockResolvedValue(createOverview('lieutenant'))
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue({ items: [createBundle('rolled_back')], total: 1, offset: 0, limit: 20 })
    vi.mocked(api.getWorldProposalBundle).mockRejectedValue(new Error('detail refresh failed'))

    await expect(
      store.rollbackProposalReview('project-1', 'review-1', {
        reviewer_ref: 'editor.alpha',
        reason: '新证据推翻旧结论',
        evidence_refs: ['chapter.02'],
      }),
    ).resolves.toBeUndefined()

    expect(store.error).toBe('detail refresh failed')
    expect(store.projection?.facts['char.hero'].rank).toBe('lieutenant')
    expect(store.proposalBundles[0].bundle_status).toBe('rolled_back')
    expect(store.selectedBundleDetail?.items[0].item_status).toBe('approved')
  })

  it('splitProposalBundle() 在 bundles refresh 失败时会显式写 error，且不会抛出 unhandled reject', async () => {
    const store = useWorldModelStore()
    store.projectProfile = createOverview('captain').project_profile
    store.projection = createOverview('captain').projection
    store.proposalBundles = [createBundle('approved')]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetailWithItems([
      {
        id: 'item-1',
        item_status: 'approved',
        review_action: 'approve',
        approved_claim_id: 'claim.hero.rank.1',
        object_ref_or_value: 'captain',
      },
      {
        id: 'item-2',
        item_status: 'approved',
        review_action: 'approve',
        approved_claim_id: 'claim.hero.rank.2',
        object_ref_or_value: 'lieutenant',
      },
    ])

    vi.mocked(api.splitWorldProposalBundle).mockResolvedValue({
      bundle: {
        ...createBundle('pending'),
        id: 'bundle-2',
        parent_bundle_id: 'bundle-1',
      },
      items: [
        {
          ...createBundleDetailWithItems([
            {
              id: 'item-2',
              item_status: 'approved',
              review_action: 'approve',
              approved_claim_id: 'claim.hero.rank.2',
              object_ref_or_value: 'lieutenant',
            },
          ]).items[0],
          id: 'item-2',
          bundle_id: 'bundle-2',
        },
      ],
      reviews: [],
      impact_snapshots: [],
      conflicts: [],
    })
    vi.mocked(api.listWorldProposalBundles).mockRejectedValue(new Error('bundles refresh failed'))

    await expect(
      store.splitProposalBundle('project-1', 'bundle-1', {
        reviewer_ref: 'editor.alpha',
        reason: '拆分 item-2',
        evidence_refs: [],
        item_ids: ['item-2'],
      }),
    ).resolves.toBeUndefined()

    expect(store.error).toBe('bundles refresh failed')
    expect(store.selectedBundleId).toBe('bundle-2')
    expect(store.selectedBundleDetail?.bundle.id).toBe('bundle-2')
    expect(store.selectedBundleDetail?.items[0].id).toBe('item-2')
  })

  it('splitProposalBundle() 主请求失败时会显式写 error，且不会抛出 unhandled reject', async () => {
    const store = useWorldModelStore()
    store.projectProfile = createOverview('captain').project_profile
    store.projection = createOverview('captain').projection
    store.proposalBundles = [createBundle('approved')]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetailWithItems([
      {
        id: 'item-1',
        item_status: 'approved',
        review_action: 'approve',
        approved_claim_id: 'claim.hero.rank.1',
        object_ref_or_value: 'captain',
      },
    ])

    vi.mocked(api.splitWorldProposalBundle).mockRejectedValue(new Error('split request failed'))

    await expect(
      store.splitProposalBundle('project-1', 'bundle-1', {
        reviewer_ref: 'editor.alpha',
        reason: '拆分 item-1',
        evidence_refs: [],
        item_ids: ['item-1'],
      }),
    ).resolves.toBeUndefined()

    expect(store.error).toBe('split request failed')
    expect(api.listWorldProposalBundles).not.toHaveBeenCalled()
    expect(store.selectedBundleId).toBe('bundle-1')
    expect(store.selectedBundleDetail?.bundle.id).toBe('bundle-1')
  })

  it('rollbackProposalReview() 主请求失败时会显式写 error，且不会抛出 unhandled reject', async () => {
    const store = useWorldModelStore()
    store.projectProfile = createOverview('captain').project_profile
    store.projection = createOverview('captain').projection
    store.proposalBundles = [createBundle('approved')]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetail('approved', 'approve', 'claim.hero.rank')

    vi.mocked(api.rollbackWorldProposalReview).mockRejectedValue(new Error('rollback request failed'))

    await expect(
      store.rollbackProposalReview('project-1', 'review-1', {
        reviewer_ref: 'editor.alpha',
        reason: '新证据推翻旧结论',
        evidence_refs: ['chapter.02'],
      }),
    ).resolves.toBeUndefined()

    expect(store.error).toBe('rollback request failed')
    expect(api.getWorldModelOverview).not.toHaveBeenCalled()
    expect(api.listWorldProposalBundles).not.toHaveBeenCalled()
    expect(api.getWorldProposalBundle).not.toHaveBeenCalled()
    expect(store.selectedBundleDetail?.items[0].item_status).toBe('approved')
  })

  it('reviewProposalItem() 和 rollbackProposalReview() overlap 时会分别跟踪 item 级 loading，并各自清理', async () => {
    const store = useWorldModelStore()
    store.projectProfile = createOverview('captain').project_profile
    store.projection = createOverview('captain').projection
    store.proposalBundles = [createBundle('approved')]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = createBundleDetailWithItems([
      {
        id: 'item-1',
        item_status: 'approved',
        review_action: 'approve',
        approved_claim_id: 'claim.hero.rank.1',
        object_ref_or_value: 'captain',
      },
      {
        id: 'item-2',
        item_status: 'approved',
        review_action: 'approve',
        approved_claim_id: 'claim.hero.rank.2',
        object_ref_or_value: 'lieutenant',
      },
    ])

    const reviewResponse = {
      id: 'review-approve-1',
      bundle_id: 'bundle-1',
      proposal_item_id: 'item-1',
      review_action: 'approve',
      reviewer_ref: 'editor.alpha',
      reason: '通过',
      evidence_refs: ['chapter.01'],
      edited_fields: {},
      created_truth_claim_id: 'claim.hero.rank.1',
      rollback_to_review_id: null,
      created_at: '2026-04-20T00:00:01Z',
    }
    const rollbackResponse = {
      id: 'review-rollback-2',
      bundle_id: 'bundle-1',
      proposal_item_id: 'item-2',
      review_action: 'rollback',
      reviewer_ref: 'editor.alpha',
      reason: '新证据推翻旧结论',
      evidence_refs: ['chapter.02'],
      edited_fields: {},
      created_truth_claim_id: 'claim.hero.rank.2',
      rollback_to_review_id: 'review-2',
      created_at: '2026-04-20T00:00:02Z',
    }
    const reviewRequest = createDeferred<typeof reviewResponse>()
    const rollbackRequest = createDeferred<typeof rollbackResponse>()
    vi.mocked(api.reviewWorldProposalItem).mockReturnValue(reviewRequest.promise)
    vi.mocked(api.rollbackWorldProposalReview).mockReturnValue(rollbackRequest.promise)
    vi.mocked(api.getWorldModelOverview).mockResolvedValue(createOverview('lieutenant'))
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue({ items: [createBundle('rolled_back')], total: 1, offset: 0, limit: 20 })
    vi.mocked(api.getWorldProposalBundle).mockResolvedValue(
      createBundleDetailWithItems([
        {
          id: 'item-1',
          item_status: 'approved',
          review_action: 'approve',
          approved_claim_id: 'claim.hero.rank.1',
          object_ref_or_value: 'captain',
        },
        {
          id: 'item-2',
          item_status: 'rolled_back',
          review_action: 'rollback',
          approved_claim_id: 'claim.hero.rank.2',
          object_ref_or_value: 'lieutenant',
        },
      ]),
    )

    const reviewPromise = store.reviewProposalItem('project-1', 'item-1', {
      reviewer_ref: 'editor.alpha',
      action: 'approve',
      reason: '通过',
      evidence_refs: ['chapter.01'],
      edited_fields: {},
    })
    const rollbackPromise = store.rollbackProposalReview(
      'project-1',
      'review-2',
      {
        reviewer_ref: 'editor.alpha',
        reason: '新证据推翻旧结论',
        evidence_refs: ['chapter.02'],
      },
      'item-2',
    )

    expect(store.submitting).toBe(true)
    expect(store.isActionPending('item-1')).toBe(true)
    expect(store.isActionPending('item-2')).toBe(true)

    reviewRequest.resolve(reviewResponse)
    await reviewPromise

    expect(store.submitting).toBe(true)
    expect(store.isActionPending('item-1')).toBe(false)
    expect(store.isActionPending('item-2')).toBe(true)

    rollbackRequest.resolve(rollbackResponse)
    await rollbackPromise

    expect(store.submitting).toBe(false)
    expect(store.isActionPending('item-1')).toBe(false)
    expect(store.isActionPending('item-2')).toBe(false)
  })

  it('ignores stale loadMoreBundles responses after the project scope changes', async () => {
    const pageRequest = createDeferred<{
      items: ReturnType<typeof createBundle>[]
      total: number
      offset: number
      limit: number
    }>()
    vi.mocked(api.listWorldProposalBundles).mockReturnValue(pageRequest.promise)
    const store = useWorldModelStore()
    store.resetProjectScopedState('project-1')
    store.proposalBundles = [createBundle()]
    store.bundlesOffset = 0

    const pending = store.loadMoreBundles('project-1')
    store.resetProjectScopedState('project-2')
    pageRequest.resolve({
      items: [{ ...createBundle(), id: 'stale-bundle' }],
      total: 2,
      offset: 20,
      limit: 20,
    })
    await pending

    expect(store.proposalBundles).toEqual([])
    expect(store.bundlesOffset).toBe(0)
    expect(store.bundlesTotal).toBe(0)
  })

  it('ignores stale loadMoreBundles errors after the project scope changes', async () => {
    const pageRequest = createDeferred<{
      items: ReturnType<typeof createBundle>[]
      total: number
      offset: number
      limit: number
    }>()
    vi.mocked(api.listWorldProposalBundles).mockReturnValue(pageRequest.promise)
    const store = useWorldModelStore()

    const pending = store.loadMoreBundles('project-1')
    store.resetProjectScopedState('project-2')
    pageRequest.reject(new Error('old project failed'))
    await pending

    expect(store.error).toBe('')
  })

  it('ignores overlapping loadMoreBundles calls while one page is already loading', async () => {
    const pageRequest = createDeferred<{
      items: ReturnType<typeof createBundle>[]
      total: number
      offset: number
      limit: number
    }>()
    vi.mocked(api.listWorldProposalBundles).mockReturnValue(pageRequest.promise)
    const store = useWorldModelStore()
    store.resetProjectScopedState('project-1')
    store.proposalBundles = [createBundle()]
    store.bundlesOffset = 0

    const first = store.loadMoreBundles('project-1')
    const second = store.loadMoreBundles('project-1')

    expect(api.listWorldProposalBundles).toHaveBeenCalledTimes(1)
    expect(store.loadingMoreBundles).toBe(true)

    pageRequest.resolve({
      items: [{ ...createBundle(), id: 'bundle-2' }],
      total: 2,
      offset: 20,
      limit: 20,
    })
    await Promise.all([first, second])

    expect(store.loadingMoreBundles).toBe(false)
    expect(store.proposalBundles.map((bundle) => bundle.id)).toEqual(['bundle-1', 'bundle-2'])
  })
})
