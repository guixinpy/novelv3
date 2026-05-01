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

const duplicateProjection = {
  ...projection,
  relations: {
    duplicateById: { id: 'rel-1', source_entity_ref: 'char.linche', target_entity_ref: 'loc.lighthouse', relation_type: '常驻' },
    duplicateByFields: { source_ref: 'char.linche', target_ref: 'loc.lighthouse', relation_type: '常驻' },
  },
} as unknown as WorldProjection

describe('CatalogWorkbench', () => {
  it('shows a loading state before ontology and projection are available', () => {
    const wrapper = mount(CatalogWorkbench, {
      props: {
        ontology: null,
        projection: null,
        pendingProposalItems: [],
        nodeType: 'all',
        view: 'nodes',
      },
    })

    expect(wrapper.text()).toContain('正在读取设定库')
    expect(wrapper.text()).not.toContain('暂无匹配节点')
    expect(wrapper.text()).not.toContain('选择一个节点查看完整信息')
  })

  it('shows a rule loading state before ontology is available', () => {
    const wrapper = mount(CatalogWorkbench, {
      props: {
        ontology: null,
        projection: null,
        pendingProposalItems: [],
        nodeType: 'all',
        view: 'rules',
      },
    })

    expect(wrapper.text()).toContain('正在读取规则约束')
    expect(wrapper.text()).not.toContain('暂无规则')
    expect(wrapper.text()).not.toContain('0 条')
  })

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

  it('keeps detail selection aligned with search results and empty state', async () => {
    const wrapper = mount(CatalogWorkbench, {
      props: {
        ontology,
        projection,
        pendingProposalItems: [],
        nodeType: 'all',
        view: 'nodes',
      },
    })

    await wrapper.find('input[type="search"]').setValue('旧灯塔')

    expect(wrapper.text()).toContain('旧灯塔')
    expect(wrapper.text()).toContain('地标')
    expect(wrapper.text()).not.toContain('父亲失踪与潮汐门有关')

    await wrapper.find('input[type="search"]').setValue('不存在')

    expect(wrapper.text()).toContain('暂无匹配节点')
    expect(wrapper.text()).toContain('选择一个节点查看完整信息')
  })

  it('labels catalog search as node filtering', () => {
    const wrapper = mount(CatalogWorkbench, {
      props: {
        ontology,
        projection,
        pendingProposalItems: [],
        nodeType: 'all',
        view: 'nodes',
      },
    })

    expect(wrapper.text()).toContain('过滤节点')
    expect(wrapper.find('input[type="search"]').attributes('placeholder')).toContain('按名称')
  })

  it('emits filter type changes from the node list', async () => {
    const wrapper = mount(CatalogWorkbench, {
      props: {
        ontology,
        projection,
        pendingProposalItems: [],
        nodeType: 'all',
        view: 'nodes',
      },
    })

    await wrapper.findAll('button').find((button) => button.text() === '地点')?.trigger('click')

    expect(wrapper.emitted('filterType')).toEqual([['locations']])
  })

  it('deduplicates graph relations before rendering', () => {
    const wrapper = mount(CatalogWorkbench, {
      props: {
        ontology,
        projection: duplicateProjection,
        pendingProposalItems: [],
        nodeType: 'all',
        view: 'graph',
      },
    })

    expect(wrapper.findAll('.catalog-graph-panel__row')).toHaveLength(1)
    expect(wrapper.text()).toContain('1 条关系')
  })

  it('shows isolated entities when graph has no relations yet', () => {
    const wrapper = mount(CatalogWorkbench, {
      props: {
        ontology: {
          ...ontology,
          relations: [],
        },
        projection: {
          ...projection,
          relations: {},
        },
        pendingProposalItems: [],
        nodeType: 'all',
        view: 'graph',
      },
    })

    expect(wrapper.text()).toContain('当前有 2 个实体，但尚未生成关系')
    expect(wrapper.text()).toContain('林澈')
    expect(wrapper.text()).toContain('旧灯塔')
  })

  it('does not show zero pending counts when pending counts are unavailable', () => {
    const wrapper = mount(CatalogWorkbench, {
      props: {
        ontology,
        projection,
        pendingProposalItems: [],
        pendingCountsAvailable: false,
        nodeType: 'characters',
        view: 'nodes',
      },
    })

    expect(wrapper.text()).not.toContain('待审 0')
    expect(wrapper.text()).not.toContain('计数待接入')
    expect(wrapper.text()).toContain('候选变更请在待审变更中查看')
  })
})
