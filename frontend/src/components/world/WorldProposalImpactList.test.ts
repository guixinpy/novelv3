// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import WorldProposalImpactList from './WorldProposalImpactList.vue'
import type { ProposalImpactSnapshot } from '../../api/types'

function createSnapshot(summary: Record<string, unknown>): ProposalImpactSnapshot {
  return {
    id: 'impact-1',
    bundle_id: 'bundle-1',
    affected_subject_refs: ['char.陆辞'],
    affected_predicates: ['presence_count'],
    affected_truth_claim_ids: [],
    candidate_item_ids: ['item-1', 'item-2', 'item-3', 'item-4', 'item-5'],
    summary,
    created_at: '2026-04-30T00:00:00Z',
  }
}

describe('WorldProposalImpactList', () => {
  it('does not label low-risk extraction batches as high risk solely by candidate count', () => {
    const wrapper = mount(WorldProposalImpactList, {
      props: {
        snapshots: [createSnapshot({ candidate_count: 5, existing_truth_count: 0 })],
      },
    })

    expect(wrapper.text()).toContain('批量候选')
    expect(wrapper.text()).not.toContain('高风险变更')
  })

  it('explains when snapshots touch existing truth', () => {
    const wrapper = mount(WorldProposalImpactList, {
      props: {
        snapshots: [createSnapshot({ candidate_count: 1, existing_truth_count: 1 })],
      },
    })

    expect(wrapper.text()).toContain('覆盖既有真相')
    expect(wrapper.text()).not.toContain('高风险变更')
  })
})
