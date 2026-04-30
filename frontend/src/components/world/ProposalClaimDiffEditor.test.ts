// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ProposalClaimDiffEditor from './ProposalClaimDiffEditor.vue'
import type { ProposalItem } from '../../api/types'

describe('ProposalClaimDiffEditor', () => {
  function createItem(overrides: Partial<ProposalItem> = {}): ProposalItem {
    return {
      id: 'item-1',
      bundle_id: 'bundle-1',
      parent_item_id: null,
      item_status: 'pending',
      claim_id: 'claim.1',
      subject_ref: 'char.hero',
      predicate: 'status',
      object_ref_or_value: { status: 'unknown' },
      claim_layer: 'truth',
      evidence_refs: ['chapter:1'],
      authority_type: 'derived',
      confidence: 0.82,
      contract_version: 'world.contract.v1',
      approved_claim_id: null,
      created_by: 'athena.chapter_analyzer',
      created_at: '2026-04-29T00:00:00Z',
      ...overrides,
    }
  }

  it('submits edited object_ref_or_value as parsed JSON', async () => {
    const wrapper = mount(ProposalClaimDiffEditor, {
      props: {
        item: createItem(),
        anchorOptions: [],
      },
    })

    await wrapper
      .get('[data-testid="proposal-object-value-editor"]')
      .setValue('{"status":"wounded","severity":"minor"}')
    await wrapper.get('[data-testid="proposal-diff-submit"]').trigger('click')

    expect(wrapper.emitted('submit')).toEqual([
      [
        {
          object_ref_or_value: {
            status: 'wounded',
            severity: 'minor',
          },
        },
      ],
    ])
  })

  it('submits atomized subject and predicate edits for dialog intake items', async () => {
    const wrapper = mount(ProposalClaimDiffEditor, {
      props: {
        item: createItem({
          subject_ref: 'project.world_intake',
          predicate: 'user_proposed_update',
          object_ref_or_value: '把林舟设定为旧灯塔守夜人',
          created_by: 'athena.dialog',
        }),
        anchorOptions: [],
      },
    })

    await wrapper.get('[data-testid="proposal-field-subject_ref"]').setValue('char.林舟')
    await wrapper.get('[data-testid="proposal-field-predicate"]').setValue('role')
    await wrapper.get('[data-testid="proposal-object-value-editor"]').setValue('"旧灯塔守夜人"')
    await wrapper.get('[data-testid="proposal-diff-submit"]').trigger('click')

    expect(wrapper.emitted('submit')).toEqual([
      [
        {
          subject_ref: 'char.林舟',
          predicate: 'role',
          object_ref_or_value: '旧灯塔守夜人',
        },
      ],
    ])
  })
})
