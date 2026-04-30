// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CatalogWorkbench from './CatalogWorkbench.vue'
import type { AthenaOntology, WorldProjection } from '../../../api/types'

const ontology = {
  entities: {
    characters: [{ id: 'char.linche', name: '林澈', role_type: '主角', core_drives: ['查清旧案'] }],
    locations: [{ id: 'loc.lighthouse', name: '旧灯塔', location_type: '地标' }],
  },
  relations: [{ id: 'rel-1', source_ref: 'char.linche', target_ref: 'loc.lighthouse', relation_type: '常驻' }],
  rules: [{ id: 'rule-1', rule_id: 'rule.tide', description: '潮汐会吞没记忆' }],
  setup_summary: null,
  profile_version: 1,
} as unknown as AthenaOntology

const projection = {
  view_type: 'current_truth',
  entities: {},
  relations: {},
  presence: { 'char.linche': { location_ref: 'loc.lighthouse', presence_status: 'active' } },
  occurred_events: {},
  event_links: {},
  facts: { 'char.linche': { hidden_truth: '父亲失踪与潮汐门有关' } },
} as WorldProjection

describe('CatalogWorkbench', () => {
  it('renders nodes and selects the first matching node', () => {
    const wrapper = mount(CatalogWorkbench, {
      props: {
        ontology,
        projection,
        pendingProposalItems: [],
        nodeType: 'characters',
        view: 'nodes',
      },
    })

    expect(wrapper.text()).toContain('林澈')
    expect(wrapper.text()).toContain('完整节点信息')
    expect(wrapper.text()).toContain('父亲失踪与潮汐门有关')
    expect(wrapper.text()).toContain('关系摘要')
  })

  it('renders rules view', () => {
    const wrapper = mount(CatalogWorkbench, {
      props: {
        ontology,
        projection,
        pendingProposalItems: [],
        nodeType: 'all',
        view: 'rules',
      },
    })

    expect(wrapper.text()).toContain('规则约束')
    expect(wrapper.text()).toContain('潮汐会吞没记忆')
  })
})
