// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProposalWorkbench from './ProposalWorkbench.vue'
import { useWorldModelStore } from '../../stores/worldModel'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({
  api: {
    listWorldProposalBundles: vi.fn(),
    getWorldProposalBundle: vi.fn(),
    reviewWorldProposalItem: vi.fn(),
    splitWorldProposalBundle: vi.fn(),
    rollbackWorldProposalReview: vi.fn(),
    getWorldModelOverview: vi.fn(),
  },
}))

describe('ProposalWorkbench', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders selected proposal detail from worldModel store', () => {
    const store = useWorldModelStore()
    store.proposalBundles = [{
      id: 'bundle-1',
      project_id: 'project-1',
      project_profile_version_id: 'profile-1',
      profile_version: 1,
      parent_bundle_id: null,
      bundle_status: 'partially_approved',
      title: '第1章世界事实候选',
      summary: 'summary',
      created_by: 'athena.chapter_analyzer',
      created_at: '2026-04-29T00:00:00Z',
      updated_at: '2026-04-29T00:00:00Z',
    }]
    store.selectedBundleId = 'bundle-1'
    store.selectedBundleDetail = {
      bundle: store.proposalBundles[0],
      items: [{
        id: 'item-1',
        bundle_id: 'bundle-1',
        parent_item_id: null,
        item_status: 'pending',
        claim_id: 'claim.1',
        subject_ref: 'loc.tower',
        predicate: 'mentioned_in_chapter',
        object_ref_or_value: { chapter_index: 1, mention_count: 2 },
        claim_layer: 'truth',
        evidence_refs: ['chapter:1'],
        authority_type: 'derived',
        confidence: 0.8,
        contract_version: 'world.contract.v1',
        approved_claim_id: null,
        created_by: 'athena.chapter_analyzer',
        created_at: '2026-04-29T00:00:00Z',
      }],
      reviews: [],
      impact_snapshots: [],
      conflicts: [],
    }

    const wrapper = mount(ProposalWorkbench, { props: { projectId: 'project-1' } })

    expect(wrapper.text()).toContain('第1章世界事实候选')
    expect(wrapper.text()).toContain('loc.tower.mentioned_in_chapter')
    expect(wrapper.text()).toContain('部分通过')
    expect(wrapper.text()).not.toContain('partially_approved')
  })

  it('renders localized proposal review queue clusters without leaking raw backend labels', () => {
    const store = useWorldModelStore()
    store.proposalReviewQueue = {
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
          chapter_range: { start: 4, end: 4 },
          reason: '状态变化需要单独审阅。',
        },
        {
          cluster_id: 'low:presence_count:chapter:4',
          risk_level: 'low',
          review_mode: 'batch',
          candidate_count: 2,
          item_ids: ['item-2', 'item-3'],
          bundle_ids: ['bundle-1'],
          subject_refs: ['char.hero', 'char.sidekick'],
          predicate: 'presence_count',
          chapter_range: { start: 4, end: 4 },
          reason: '出场统计可批量审阅。',
        },
      ],
    }

    const wrapper = mount(ProposalWorkbench, { props: { projectId: 'project-1' } })

    expect(wrapper.text()).toContain('审阅队列')
    expect(wrapper.text()).toContain('高风险')
    expect(wrapper.text()).toContain('低风险')
    expect(wrapper.text()).toContain('单独审阅')
    expect(wrapper.text()).toContain('批量审阅')
    expect(wrapper.text()).not.toContain('high')
    expect(wrapper.text()).not.toContain('individual')
    expect(wrapper.text()).not.toContain('batch')
  })

  it('renders large proposal details in bounded batches', async () => {
    const store = useWorldModelStore()
    const bundle = {
      id: 'bundle-1',
      project_id: 'project-1',
      project_profile_version_id: 'profile-1',
      profile_version: 1,
      parent_bundle_id: null,
      bundle_status: 'pending',
      title: '长篇世界事实候选',
      summary: '',
      created_by: 'athena.chapter_analyzer',
      created_at: '2026-04-29T00:00:00Z',
      updated_at: '2026-04-29T00:00:00Z',
    }
    store.selectedBundleId = bundle.id
    const firstPageItems = Array.from({ length: 100 }, (_, index) => ({
      id: `item-${index + 1}`,
      bundle_id: bundle.id,
      parent_item_id: null,
      item_status: 'pending',
      claim_id: `claim.${index + 1}`,
      subject_ref: `char.${index + 1}`,
      predicate: 'presence_count',
      object_ref_or_value: { count: index + 1 },
      claim_layer: 'truth',
      evidence_refs: [`chapter:${index + 1}`],
      authority_type: 'derived',
      confidence: 0.8,
      contract_version: 'world.contract.v1',
      approved_claim_id: null,
      created_by: 'athena.chapter_analyzer',
      created_at: '2026-04-29T00:00:00Z',
    }))
    const secondPageItems = Array.from({ length: 50 }, (_, index) => ({
      id: `item-${index + 101}`,
      bundle_id: bundle.id,
      parent_item_id: null,
      item_status: 'pending',
      claim_id: `claim.${index + 101}`,
      subject_ref: `char.${index + 101}`,
      predicate: 'presence_count',
      object_ref_or_value: { count: index + 101 },
      claim_layer: 'truth',
      evidence_refs: [`chapter:${index + 101}`],
      authority_type: 'derived',
      confidence: 0.8,
      contract_version: 'world.contract.v1',
      approved_claim_id: null,
      created_by: 'athena.chapter_analyzer',
      created_at: '2026-04-29T00:00:00Z',
    }))
    store.selectedBundleDetail = {
      bundle,
      items: firstPageItems,
      items_total: 150,
      items_offset: 0,
      items_limit: 100,
      reviews: [],
      impact_snapshots: [],
      conflicts: [],
    }
    vi.mocked(api.getWorldProposalBundle).mockResolvedValue({
      bundle,
      items: secondPageItems,
      items_total: 150,
      items_offset: 100,
      items_limit: 100,
      reviews: [],
      impact_snapshots: [],
      conflicts: [],
    })

    const wrapper = mount(ProposalWorkbench, {
      props: { projectId: 'project-1' },
      global: {
        stubs: {
          WorldProposalBundleList: true,
          WorldProposalImpactList: true,
          WorldProposalItemCard: {
            props: ['item'],
            template: '<article data-testid="proposal-item-card">{{ item.claim_id }}</article>',
          },
        },
      },
    })

    expect(wrapper.findAll('[data-testid="proposal-item-card"]')).toHaveLength(100)
    expect(wrapper.text()).toContain('已显示 100/150 项')

    await wrapper.find('[data-testid="show-more-proposal-items"]').trigger('click')

    expect(api.getWorldProposalBundle).toHaveBeenCalledWith('project-1', 'bundle-1', {
      item_offset: 100,
      item_limit: 100,
    })
    await vi.waitFor(() => {
      expect(wrapper.findAll('[data-testid="proposal-item-card"]')).toHaveLength(150)
    })
    expect(wrapper.text()).toContain('已显示 150/150 项')
  })
})
