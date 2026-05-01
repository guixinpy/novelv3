// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TruthLedger from './TruthLedger.vue'
import type { WorldFactClaim, WorldProjection } from '../../api/types'

const projection: WorldProjection = {
  view_type: 'current_truth',
  entities: {},
  relations: {},
  presence: {},
  occurred_events: {},
  event_links: {},
  facts: {
    'char.linshen': {
      motive: '关闭潮汐门',
    },
  },
}

const factClaims: WorldFactClaim[] = [
  {
    id: 'fact-1',
    project_id: 'project-1',
    project_profile_version_id: 'profile-1',
    profile_version: 1,
    contract_version: 'world.contract.v1',
    claim_id: 'claim.linshen.motive',
    chapter_index: 2,
    intra_chapter_seq: 1,
    subject_ref: 'char.linshen',
    predicate: 'motive',
    object_ref_or_value: '关闭潮汐门',
    claim_layer: 'truth',
    claim_status: 'confirmed',
    perspective_ref: 'char.su',
    disclosed_to_refs: ['char.su', 'char.zhou'],
    valid_from_anchor_id: 'anchor.2',
    valid_to_anchor_id: null,
    source_event_ref: 'event.tidegate.closed',
    evidence_refs: ['chapter.02'],
    authority_type: 'approved',
    confidence: 0.9,
    notes: '编辑确认',
    created_at: '2026-04-20T00:00:00Z',
  },
]

describe('TruthLedger', () => {
  it('renders flattened truth facts', () => {
    const wrapper = mount(TruthLedger, { props: { projection, factClaims, view: 'facts' } })

    expect(wrapper.text()).toContain('char.linshen')
    expect(wrapper.text()).toContain('motive')
    expect(wrapper.text()).toContain('关闭潮汐门')
    expect(wrapper.text()).toContain('chapter.02')
  })

  it('renders disclosure metadata for facts', () => {
    const wrapper = mount(TruthLedger, { props: { projection, factClaims, view: 'disclosure' } })

    expect(wrapper.text()).toContain('char.su / char.zhou')
    expect(wrapper.text()).toContain('event.tidegate.closed')
    expect(wrapper.text()).toContain('视角')
  })

  it('falls back to projection values when fact claim metadata is not loaded', () => {
    const wrapper = mount(TruthLedger, { props: { projection, factClaims: [], view: 'disclosure' } })

    expect(wrapper.text()).toContain('关闭潮汐门')
    expect(wrapper.text()).toContain('当前投影未携带披露元数据')
  })

  it('renders presence count facts as readable summaries', () => {
    const wrapper = mount(TruthLedger, {
      props: {
        projection,
        factClaims: [
          {
            ...factClaims[0],
            id: 'fact-presence',
            subject_ref: 'char.luci',
            predicate: 'presence_count',
            object_ref_or_value: {
              count: 51,
              chapter_index: 1,
              source: 'l1_rule',
              matched_names: ['陆辞'],
              quality: { confidence_band: 'medium' },
            },
          },
        ],
        view: 'disclosure',
      },
    })

    expect(wrapper.text()).toContain('第1章：陆辞出现 51 次（自动抽取，中置信）')
    expect(wrapper.text()).not.toContain('"count":51')
  })
})
