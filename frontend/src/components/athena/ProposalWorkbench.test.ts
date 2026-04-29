// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProposalWorkbench from './ProposalWorkbench.vue'
import { useWorldModelStore } from '../../stores/worldModel'

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
      bundle_status: 'pending',
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
  })
})
