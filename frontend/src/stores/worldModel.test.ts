import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useWorldModelStore } from './worldModel'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getWorldModelOverview: vi.fn(),
    listWorldProposalBundles: vi.fn(),
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
  }
}

describe('worldModel store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
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
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue([
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
    ])
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
    })

    const store = useWorldModelStore()
    await store.loadSetupPanelData('project-1')

    expect(store.projectProfile?.version).toBe(3)
    expect(store.projection?.facts['char.hero'].rank).toBe('captain')
    expect(store.proposalBundles).toHaveLength(1)
    expect(store.selectedBundleId).toBe('bundle-1')
    expect(store.selectedBundleDetail?.bundle.id).toBe('bundle-1')
  })

  it('reviewProposalItem() 会执行审批并刷新 bundles 和当前 detail', async () => {
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
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue([createBundle('approved')])
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
    expect(api.getWorldModelOverview).toHaveBeenCalledWith('project-1')
    expect(api.listWorldProposalBundles).toHaveBeenCalledWith('project-1')
    expect(api.getWorldProposalBundle).toHaveBeenCalledWith('project-1', 'bundle-1')
    expect(store.projection?.facts['char.hero'].rank).toBe('captain')
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

    vi.mocked(api.listWorldProposalBundles).mockResolvedValue([createBundle('approved', 2)])
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
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue([createBundle('approved')])
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
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue([createBundle('approved')])
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
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue([createBundle('rolled_back')])
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
    expect(api.getWorldModelOverview).toHaveBeenCalledWith('project-1')
    expect(store.projection?.facts['char.hero'].rank).toBe('lieutenant')
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
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue([createBundle('rolled_back')])
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
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue([createBundle('rolled_back')])
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
    vi.mocked(api.listWorldProposalBundles).mockResolvedValue([createBundle('rolled_back')])
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
})
