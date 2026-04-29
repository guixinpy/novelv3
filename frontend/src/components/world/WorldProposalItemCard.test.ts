// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import WorldProposalItemCard from './WorldProposalItemCard.vue'
import type { ProposalItem } from '../../api/types'

describe('WorldProposalItemCard', () => {
  it('renders deterministic evidence and quality metadata for review', () => {
    const item: ProposalItem = {
      id: 'item-1',
      bundle_id: 'bundle-1',
      parent_item_id: null,
      item_status: 'pending',
      claim_id: 'claim.1',
      subject_ref: 'char.林舟',
      predicate: 'present_at_location',
      object_ref_or_value: {
        location_ref: 'loc.雾港城',
        evidence_span: {
          ref: 'chapter:1',
          text: '林舟走进雾港城',
        },
        quality: {
          signal: 'cooccurrence',
          confidence_band: 'medium',
          review_priority: 'normal',
        },
      },
      claim_layer: 'truth',
      evidence_refs: ['chapter:1'],
      authority_type: 'derived',
      confidence: 0.78,
      contract_version: 'world.contract.v1',
      approved_claim_id: null,
      created_by: 'athena.chapter_analyzer',
      created_at: '2026-04-29T00:00:00Z',
    }

    const wrapper = mount(WorldProposalItemCard, {
      props: {
        item,
        busy: false,
        approvalReviewId: null,
        reviewerRef: 'athena.user',
        anchorOptions: [],
        conflicts: [],
      },
    })

    expect(wrapper.text()).toContain('chapter:1')
    expect(wrapper.text()).toContain('林舟走进雾港城')
    expect(wrapper.text()).toContain('cooccurrence')
    expect(wrapper.text()).toContain('medium')
  })
})
