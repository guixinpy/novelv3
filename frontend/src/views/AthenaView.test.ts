// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { defineComponent } from 'vue'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import AthenaView from './AthenaView.vue'
import { api } from '../api/client'
import type { AthenaEvolutionPlan, AthenaTimeline, ChapterSummary } from '../api/types'

vi.mock('../api/client', () => ({
  api: {
    getProject: vi.fn(),
    listChapters: vi.fn(),
    getAthenaOntology: vi.fn(),
    getAthenaMessages: vi.fn(),
    getAthenaTimeline: vi.fn(),
    getAthenaEvolutionPlan: vi.fn(),
    getConsistencyIssues: vi.fn(),
  },
}))

const chapters: ChapterSummary[] = [
  { id: 'chapter-1', chapter_index: 1, title: '异常信号', word_count: 1200, status: 'draft' },
]

const timeline: AthenaTimeline = {
  anchors: [],
  events: [
    {
      id: 'event-row-1',
      event_id: 'event.tidegate.alert',
      chapter_index: 1,
      intra_chapter_seq: 1,
      event_type: 'discovery',
      description: '潮汐门警报触发。',
    },
  ],
}

const evolutionPlan = {
  outline: {
    chapters: [
      { chapter_index: 1, title: '异常信号', summary: '潮汐门出现异常读数。' },
    ],
  },
  storyline: {
    plotlines: [],
    foreshadowing: [],
  },
} as unknown as AthenaEvolutionPlan

const NarrativeAtlasViewStub = defineComponent({
  name: 'NarrativeAtlasView',
  props: {
    plan: { type: Object, default: null },
    chapters: { type: Array, required: true },
    timeline: { type: Object, default: null },
  },
  emits: ['navigate', 'loadChapterWindow'],
  template: `
    <section data-testid="narrative-atlas-view-stub">
      <button
        data-testid="atlas-navigate-storyline"
        @click="$emit('navigate', { view: 'storyline', sourceKey: 'plotline:main' })"
      >
        跳转故事线
      </button>
      <button
        type="button"
        data-testid="atlas-request-chapter-window"
        @click="$emit('loadChapterWindow', { offset: 80, limit: 80 })"
      >
        请求图谱章节窗口
      </button>
    </section>
  `,
})

const TimelineViewStub = defineComponent({
  name: 'TimelineView',
  props: {
    events: { type: Array, required: true },
    anchors: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
    fallbackSummary: { type: Object, default: null },
  },
  template: '<section data-testid="timeline-view-stub">{{ events.map((event) => event.description).join(" | ") }}</section>',
})

const NarrativeWorkbenchStub = defineComponent({
  name: 'NarrativeWorkbench',
  emits: ['loadChapterWindow', 'loadForeshadowingWindow', 'loadMilestoneWindow'],
  template: `
    <section data-testid="narrative-workbench-stub">
      <button
        type="button"
        data-testid="request-chapter-window"
        @click="$emit('loadChapterWindow', { offset: 200, limit: 50 })"
      >
        请求章节窗口
      </button>
      <button
        type="button"
        data-testid="request-foreshadowing-window"
        @click="$emit('loadForeshadowingWindow', { offset: 200, limit: 100 })"
      >
        请求伏笔窗口
      </button>
      <button
        type="button"
        data-testid="request-milestone-window"
        @click="$emit('loadMilestoneWindow', { offset: 80, limit: 80 })"
      >
        请求节点窗口
      </button>
    </section>
  `,
})

const ConsistencyListStub = defineComponent({
  name: 'ConsistencyList',
  props: {
    latestChapterIndex: {
      type: Number,
      default: null,
    },
  },
  template: '<section data-testid="consistency-latest">{{ latestChapterIndex }}</section>',
})

async function mountAthenaView(initialPath = '/projects/project-1/athena/narrative?view=graph') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      {
        path: '/projects/:id/athena/:section',
        component: AthenaView,
        meta: { workspace: 'athena' },
      },
    ],
  })

  await router.push(initialPath)
  await router.isReady()

  const wrapper = mount(AthenaView, {
    global: {
      plugins: [router],
      stubs: {
        Teleport: true,
        AthenaSubnav: true,
        TimelineView: TimelineViewStub,
        NarrativeWorkbench: NarrativeWorkbenchStub,
        NarrativeAtlasView: NarrativeAtlasViewStub,
        ConsistencyList: ConsistencyListStub,
        AthenaChatPanel: true,
      },
    },
  })
  await flushPromises()
  await flushPromises()
  return { wrapper, router }
}

describe('AthenaView narrative atlas integration', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.mocked(api.getProject).mockResolvedValue({
      id: 'project-1',
      name: '雾港二十夜',
      genre: '都市奇幻悬疑',
      current_word_count: 0,
      status: 'draft',
      updated_at: '2026-04-28T00:00:00Z',
    })
    vi.mocked(api.listChapters).mockResolvedValue({ chapters })
    vi.mocked(api.getAthenaOntology).mockResolvedValue({
      entities: {},
      relations: [],
      rules: [],
      setup_summary: null,
      profile_version: 1,
    })
    vi.mocked(api.getAthenaMessages).mockResolvedValue([])
    vi.mocked(api.getAthenaTimeline).mockResolvedValue(timeline)
    vi.mocked(api.getAthenaEvolutionPlan).mockResolvedValue(evolutionPlan)
    vi.mocked(api.getConsistencyIssues).mockResolvedValue([])
  })

  it('renders the narrative graph tab and atlas view without passing graph to the workbench', async () => {
    const { wrapper } = await mountAthenaView()

    expect(wrapper.get('nav[aria-label="Athena 当前分类视图"]').text()).toContain('图谱')
    expect(wrapper.find('[data-testid="narrative-atlas-view-stub"]').exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'NarrativeWorkbench' }).exists()).toBe(false)

    const atlas = wrapper.getComponent({ name: 'NarrativeAtlasView' })
    expect(atlas.props()).toMatchObject({
      plan: evolutionPlan,
      chapters,
      timeline,
    })
  })

  it('routes atlas detail navigation to the target narrative view without sourceKey query state', async () => {
    const { wrapper, router } = await mountAthenaView()

    await wrapper.get('[data-testid="atlas-navigate-storyline"]').trigger('click')
    await flushPromises()

    expect(router.currentRoute.value.path).toBe('/projects/project-1/athena/narrative')
    expect(router.currentRoute.value.query).toEqual({ view: 'storyline' })
  })

  it('loads a bounded graph plan window when atlas requests a chapter window', async () => {
    const { wrapper } = await mountAthenaView('/projects/project-1/athena/narrative?view=graph')
    vi.mocked(api.getAthenaEvolutionPlan).mockClear()

    await wrapper.get('[data-testid="atlas-request-chapter-window"]').trigger('click')
    await flushPromises()

    expect(api.getAthenaEvolutionPlan).toHaveBeenCalledWith('project-1', {
      mode: 'window',
      chapter_offset: 80,
      chapter_limit: 80,
      plotline_limit: 20,
      milestone_limit: 500,
      foreshadowing_limit: 500,
    })
  })

  it('uses narrative plan chapters as timeline fallback when timeline events are missing', async () => {
    vi.mocked(api.getAthenaTimeline).mockResolvedValue({ anchors: [], events: [] })

    const { wrapper } = await mountAthenaView('/projects/project-1/athena/narrative?view=timeline')
    const timelineStub = wrapper.getComponent({ name: 'TimelineView' })

    expect(wrapper.get('[data-testid="timeline-view-stub"]').text()).toContain('异常信号：潮汐门出现异常读数。')
    expect(timelineStub.props('events')).toMatchObject([
      {
        event_id: 'plan.chapter.1',
        chapter_index: 1,
        event_type: 'chapter_plan',
      },
    ])
  })

  it('uses narrative plan total metadata for timeline fallback summary', async () => {
    vi.mocked(api.getAthenaTimeline).mockResolvedValue({ anchors: [], events: [] })
    vi.mocked(api.getAthenaEvolutionPlan).mockResolvedValue({
      outline: {
        chapters: Array.from({ length: 50 }, (_, index) => ({
          chapter_index: index + 101,
          title: `窗口章节${index + 101}`,
        })),
        chapters_total: 1000,
        plotlines: [],
      },
      storyline: {
        plotlines: [
          { name: '主线', type: 'main', milestones: [] },
          { name: '支线', type: 'sub', milestones: [] },
        ],
        plotlines_total: 4,
        foreshadowing: Array.from({ length: 100 }, (_, index) => ({
          hint: `窗口伏笔${index + 1}`,
          planted_chapter: index + 1,
          resolved_chapter: index + 50,
          status: 'pending',
        })),
        foreshadowing_total: 300,
      },
    } as unknown as AthenaEvolutionPlan)

    const { wrapper } = await mountAthenaView('/projects/project-1/athena/narrative?view=timeline')
    const timelineStub = wrapper.getComponent({ name: 'TimelineView' })

    expect(timelineStub.props('fallbackSummary')).toEqual({
      chapters: 1000,
      plotlines: 4,
      foreshadowing: 300,
    })
  })

  it('loads a windowed narrative plan when chapter workbench requests a chapter window', async () => {
    const { wrapper } = await mountAthenaView('/projects/project-1/athena/narrative?view=chapters')
    vi.mocked(api.getAthenaEvolutionPlan).mockClear()

    await wrapper.get('[data-testid="request-chapter-window"]').trigger('click')
    await flushPromises()

    expect(api.getAthenaEvolutionPlan).toHaveBeenCalledWith('project-1', {
      mode: 'window',
      chapter_offset: 200,
      chapter_limit: 50,
      plotline_limit: 1,
      foreshadowing_limit: 1,
    })
  })

  it('loads a windowed narrative plan when workbench requests a foreshadowing window', async () => {
    const { wrapper } = await mountAthenaView('/projects/project-1/athena/narrative?view=foreshadowing')
    vi.mocked(api.getAthenaEvolutionPlan).mockClear()

    await wrapper.get('[data-testid="request-foreshadowing-window"]').trigger('click')
    await flushPromises()

    expect(api.getAthenaEvolutionPlan).toHaveBeenCalledWith('project-1', {
      mode: 'window',
      chapter_limit: 1,
      plotline_limit: 1,
      foreshadowing_offset: 200,
      foreshadowing_limit: 100,
    })
  })

  it('loads a windowed narrative plan when workbench requests a storyline milestone window', async () => {
    const { wrapper } = await mountAthenaView('/projects/project-1/athena/narrative?view=storyline')
    vi.mocked(api.getAthenaEvolutionPlan).mockClear()

    await wrapper.get('[data-testid="request-milestone-window"]').trigger('click')
    await flushPromises()

    expect(api.getAthenaEvolutionPlan).toHaveBeenCalledWith('project-1', {
      mode: 'window',
      chapter_limit: 1,
      plotline_limit: 20,
      milestone_offset: 80,
      milestone_limit: 80,
      foreshadowing_limit: 1,
    })
  })

  it('uses chapter list metadata for latest chapter when summaries are paginated', async () => {
    const firstPage = Array.from({ length: 200 }, (_, index) => ({
      id: `chapter-${index + 1}`,
      chapter_index: index + 1,
      title: `第${index + 1}章`,
      word_count: 1000,
      status: 'generated',
    }))
    vi.mocked(api.listChapters).mockResolvedValue({
      chapters: firstPage,
      total: 250,
      offset: 0,
      limit: 200,
      has_more: true,
      latest_chapter_index: 250,
    })

    const { wrapper } = await mountAthenaView('/projects/project-1/athena/review?view=conflicts')

    expect(wrapper.get('[data-testid="consistency-latest"]').text()).toBe('250')
  })
})
