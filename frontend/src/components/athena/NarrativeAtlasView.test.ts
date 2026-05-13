// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import NarrativeAtlasView from './NarrativeAtlasView.vue'
import type { AthenaEvolutionPlan, AthenaTimeline, ChapterSummary } from '../../api/types'

const chapters: ChapterSummary[] = [
  { id: 'chapter-1', chapter_index: 1, title: '异常信号', word_count: 1200, status: 'draft' },
  { id: 'chapter-2', chapter_index: 2, title: '灯塔回声', word_count: 1800, status: 'draft' },
  { id: 'chapter-3', chapter_index: 3, title: '潮汐门', word_count: 2200, status: 'done' },
]

const plan = {
  outline: {
    id: 'outline-1',
    status: 'generated',
    total_chapters: 3,
    chapters: [
      { chapter_index: 1, title: '异常信号', summary: '潮汐门出现异常读数。' },
      { chapter_index: 2, title: '灯塔回声', summary: '林澈抵达旧灯塔。' },
      { chapter_index: 3, title: '潮汐门', summary: '旧计划浮出水面。' },
    ],
    plotlines: [],
  },
  storyline: {
    id: 'storyline-1',
    status: 'generated',
    plotlines: [
      {
        name: '主线：潮汐根源',
        type: 'main',
        milestones: [
          { chapter_index: 1, title: '发现异常', summary: '读数指向旧计划。' },
          { chapter_index: 3, title: '确认潮汐门真相' },
        ],
      },
    ],
    foreshadowing: [
      {
        hint: '潮汐钟慢了三分钟',
        planted_chapter: 2,
        status: 'pending',
      },
    ],
  },
} as unknown as AthenaEvolutionPlan

const timeline: AthenaTimeline = {
  anchors: [],
  events: [
    {
      id: 'event-row-1',
      event_id: 'event.tidegate.alert',
      chapter_index: 2,
      intra_chapter_seq: 1,
      event_type: 'discovery',
      description: '潮汐门警报触发。',
    },
  ],
}

function mountAtlas(props: { plan?: AthenaEvolutionPlan | null; timeline?: AthenaTimeline | null } = {}) {
  return mount(NarrativeAtlasView, {
    props: {
      plan: props.plan === undefined ? plan : props.plan,
      chapters,
      timeline: props.timeline === undefined ? timeline : props.timeline,
    },
  })
}

describe('NarrativeAtlasView', () => {
  it('renders graph metrics and chapter spine data', () => {
    const wrapper = mountAtlas()

    expect(wrapper.get('[data-testid="atlas-metric-chapters"]').text()).toContain('3')
    expect(wrapper.get('[data-testid="atlas-metric-plotlines"]').text()).toContain('1')
    expect(wrapper.get('[data-testid="atlas-metric-foreshadowing"]').text()).toContain('1')
    expect(wrapper.get('[data-testid="atlas-metric-events"]').text()).toContain('1')
    expect(wrapper.get('[data-atlas-node-id="chapter:1"]').text()).toContain('异常信号')
    expect(wrapper.find('[data-atlas-layer="trunk"]').exists()).toBe(true)
  })

  it('shows empty state when no plan exists', () => {
    const wrapper = mountAtlas({ plan: null, timeline: null })

    expect(wrapper.text()).toContain('尚未生成叙事规划')
    expect(wrapper.find('[data-testid="narrative-atlas-canvas"]').exists()).toBe(false)
  })

  it('shows loading state before narrative plan data resolves', () => {
    const wrapper = mount(NarrativeAtlasView, {
      props: {
        plan: null,
        chapters,
        timeline: null,
        loading: true,
      },
    })

    expect(wrapper.text()).toContain('正在读取叙事规划')
    expect(wrapper.text()).not.toContain('尚未生成叙事规划')
    expect(wrapper.find('[data-testid="narrative-atlas-canvas"]').exists()).toBe(false)
  })

  it('selects a node and renders its details', async () => {
    const wrapper = mountAtlas()

    await wrapper.get('[data-atlas-node-id="foreshadowing:潮汐钟慢了三分钟"]').trigger('click')

    expect(wrapper.get('[data-testid="atlas-detail-panel"]').text()).toContain('潮汐钟慢了三分钟')
    expect(wrapper.get('[data-testid="atlas-detail-panel"]').text()).toContain('待回收')
    expect(wrapper.get('[data-testid="atlas-detail-panel"]').text()).not.toContain('pending')
  })

  it('can hide and show foreshadowing layer', async () => {
    const wrapper = mountAtlas()

    expect(wrapper.findAll('[data-atlas-layer="foreshadowing"]').length).toBeGreaterThan(0)

    await wrapper.get('[data-testid="atlas-layer-foreshadowing"]').setValue(false)
    expect(wrapper.findAll('[data-atlas-layer="foreshadowing"]')).toHaveLength(0)

    await wrapper.get('[data-testid="atlas-layer-foreshadowing"]').setValue(true)
    expect(wrapper.findAll('[data-atlas-layer="foreshadowing"]').length).toBeGreaterThan(0)
  })

  it('emits navigation when detail panel action clicked', async () => {
    const wrapper = mountAtlas()

    await wrapper.get('[data-atlas-node-id="foreshadowing:潮汐钟慢了三分钟"]').trigger('click')
    await wrapper.get('[data-testid="atlas-detail-navigate"]').trigger('click')

    expect(wrapper.emitted('navigate')).toEqual([
      [{ view: 'foreshadowing', sourceKey: 'foreshadowing:潮汐钟慢了三分钟' }],
    ])
  })
})
