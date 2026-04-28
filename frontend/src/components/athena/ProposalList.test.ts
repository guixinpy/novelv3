// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProposalList from './ProposalList.vue'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({
  api: {
    getAthenaProposalDetail: vi.fn(),
    reviewAthenaProposalItem: vi.fn(),
    getAthenaEvolutionProposals: vi.fn(),
  },
}))

describe('ProposalList', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders bundle_status from proposal list endpoint', () => {
    const wrapper = mount(ProposalList, {
      props: {
        proposals: {
          items: [
            {
              id: 'bundle-1',
              title: 'Athena 对话待审世界更新',
              bundle_status: 'pending',
            },
          ],
        },
      },
    })

    expect(wrapper.text()).toContain('Athena 对话待审世界更新')
    expect(wrapper.text()).toContain('pending')
    expect(wrapper.text()).not.toContain('0 项')
  })

  it('loads detail and exposes batch approval for low-risk items', async () => {
    vi.mocked(api.getAthenaProposalDetail).mockResolvedValue({
      bundle: {
        id: 'bundle-1',
        project_id: 'project-1',
        project_profile_version_id: 'profile-1',
        profile_version: 1,
        parent_bundle_id: null,
        bundle_status: 'pending',
        title: '第1章世界事实候选',
        summary: '',
        created_by: 'athena.chapter_analyzer',
        created_at: '2026-04-28T00:00:00Z',
        updated_at: '2026-04-28T00:00:00Z',
      },
      items: [
        {
          id: 'item-1',
          bundle_id: 'bundle-1',
          parent_item_id: null,
          item_status: 'pending',
          claim_id: 'claim.1',
          subject_ref: 'char.林舟',
          predicate: 'presence_count',
          object_ref_or_value: { count: 2 },
          claim_layer: 'truth',
          evidence_refs: ['chapter:1'],
          authority_type: 'derived',
          confidence: 0.9,
          contract_version: 'world.contract.v1',
          approved_claim_id: null,
          created_by: 'athena.chapter_analyzer',
          created_at: '2026-04-28T00:00:00Z',
        },
      ],
      reviews: [],
      impact_snapshots: [],
      conflicts: [],
    })
    vi.mocked(api.reviewAthenaProposalItem).mockResolvedValue({
      id: 'review-1',
      bundle_id: 'bundle-1',
      proposal_item_id: 'item-1',
      review_action: 'approve',
      reviewer_ref: 'athena.batch',
      reason: '批量通过低风险候选',
      evidence_refs: [],
      edited_fields: {},
      created_truth_claim_id: 'claim.1',
      rollback_to_review_id: null,
      created_at: '2026-04-28T00:00:00Z',
    })
    vi.mocked(api.getAthenaEvolutionProposals).mockResolvedValue({ items: [], total: 0, offset: 0, limit: 20 })
    const wrapper = mount(ProposalList, {
      props: {
        projectId: 'project-1',
        proposals: {
          items: [{ id: 'bundle-1', title: '第1章世界事实候选', bundle_status: 'pending' }],
        },
      },
    })

    await wrapper.find('button.proposal-list__header').trigger('click')
    await vi.waitFor(() => expect(wrapper.text()).toContain('char.林舟.presence_count'))

    await wrapper.find('[data-testid="batch-approve-low-risk"]').trigger('click')

    expect(api.reviewAthenaProposalItem).toHaveBeenCalledWith('project-1', 'item-1', expect.objectContaining({
      action: 'approve',
      reason: '批量通过低风险候选',
    }))
  })
})
