// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ReviewInsightPanel from './ReviewInsightPanel.vue'
import type { ProposalBundle, ProposalBundleDetail } from '../../api/types'

const bundle: ProposalBundle = {
  id: 'bundle-1',
  project_id: 'project-1',
  project_profile_version_id: 'profile-1',
  profile_version: 1,
  parent_bundle_id: null,
  bundle_status: 'pending',
  title: '第十章事实候选',
  summary: '抽取三条事实。',
  created_by: 'athena',
  created_at: '2026-04-29T01:00:00',
  updated_at: '2026-04-29T01:00:00',
}

const detail = {
  bundle,
  items: [
    { id: 'item-1', subject_ref: 'char.linshen', item_status: 'pending' },
  ],
  reviews: [
    {
      id: 'review-1',
      bundle_id: 'bundle-1',
      proposal_item_id: 'item-1',
      review_action: 'approve',
      reviewer_ref: 'editor',
      reason: '可信',
      evidence_refs: [],
      edited_fields: {},
      created_truth_claim_id: 'claim-1',
      rollback_to_review_id: null,
      created_at: '2026-04-29T02:00:00',
    },
  ],
  impact_snapshots: [
    {
      id: 'impact-1',
      bundle_id: 'bundle-1',
      affected_subject_refs: ['char.linshen'],
      affected_predicates: ['presence_count'],
      affected_truth_claim_ids: [],
      candidate_item_ids: ['item-1'],
      summary: { candidate_count: 1 },
      created_at: '2026-04-29T02:00:00',
    },
  ],
  conflicts: [],
} as unknown as ProposalBundleDetail

describe('ReviewInsightPanel', () => {
  it('renders impact snapshot details', () => {
    const wrapper = mount(ReviewInsightPanel, { props: { detail, bundles: [bundle], view: 'impact' } })

    expect(wrapper.text()).toContain('影响主体')
    expect(wrapper.text()).toContain('char.linshen')
  })

  it('renders bundle and review history', () => {
    const wrapper = mount(ReviewInsightPanel, { props: { detail, bundles: [bundle], view: 'history' } })

    expect(wrapper.text()).toContain('第十章事实候选')
    expect(wrapper.text()).toContain('可信')
  })
})
