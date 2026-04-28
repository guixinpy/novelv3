// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent } from 'vue'
import ManuscriptView from './ManuscriptView.vue'
import { api } from '../api/client'
import type { ChapterContent } from '../api/types'

vi.mock('../api/client', () => ({
  api: {
    getProject: vi.fn(),
    listChapters: vi.fn(),
    getChapter: vi.fn(),
    getActiveRevision: vi.fn(),
  },
}))

const ChapterListStub = defineComponent({
  name: 'ChapterList',
  props: {
    chapters: {
      type: Array,
      required: true,
    },
    activeIndex: {
      type: Number,
      default: null,
    },
  },
  emits: ['select'],
  template: `
    <div>
      <button
        v-for="chapter in chapters"
        :key="chapter.index"
        data-testid="chapter-option"
        @click="$emit('select', chapter.index)"
      >
        第{{ chapter.index }}章
      </button>
    </div>
  `,
})

const ModelTraceDrawerStub = defineComponent({
  name: 'ModelTraceDrawer',
  props: {
    projectId: {
      type: String,
      required: true,
    },
    traceId: {
      type: String,
      default: null,
    },
    open: {
      type: Boolean,
      required: true,
    },
  },
  template: '<div data-testid="trace-drawer" />',
})

function makeChapter(chapterIndex: number, traceId: string | null): ChapterContent {
  return {
    id: `chapter-${chapterIndex}`,
    project_id: 'project-1',
    chapter_index: chapterIndex,
    title: `第${chapterIndex}章`,
    content: `第${chapterIndex}章第一段。\n\n第${chapterIndex}章第二段。`,
    word_count: 16,
    status: 'generated',
    model: '',
    prompt_tokens: 0,
    completion_tokens: 0,
    generation_time: 0,
    temperature: 0.7,
    last_generation_trace_id: traceId,
    created_at: '2026-04-28T00:00:00Z',
    updated_at: '2026-04-28T00:00:00Z',
  }
}

async function mountView(projectId = 'project-1') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/projects/:id/manuscript', component: { template: '<div />' } },
    ],
  })
  await router.push(`/projects/${projectId}/manuscript`)
  await router.isReady()

  const wrapper = mount(ManuscriptView, {
    global: {
      plugins: [router],
      stubs: {
        Teleport: true,
        ChapterList: ChapterListStub,
        ManuscriptEditor: true,
        RevisionSummaryPanel: true,
        RevisionSubmitModal: true,
        ModelTraceDrawer: ModelTraceDrawerStub,
      },
    },
  })
  await flushPromises()
  return { wrapper, router }
}

function findTraceButton(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('button').find((button) => button.text() === '生成上下文')
}

describe('ManuscriptView', () => {
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
    vi.mocked(api.listChapters).mockResolvedValue({
      chapters: [
        { chapter_index: 1, word_count: 16 },
        { chapter_index: 2, word_count: 18 },
      ],
    })
    vi.mocked(api.getChapter).mockImplementation(async (_projectId: string, chapterIndex: number) =>
      makeChapter(chapterIndex, `trace-chapter-${chapterIndex}`),
    )
    vi.mocked(api.getActiveRevision).mockResolvedValue(null)
  })

  it('shows chapter generation context action when loaded chapter has trace id', async () => {
    const { wrapper } = await mountView()

    expect(findTraceButton(wrapper)?.exists()).toBe(true)
  })

  it('passes selected chapter trace id to model trace drawer after clicking generation context', async () => {
    const { wrapper } = await mountView()

    await findTraceButton(wrapper)!.trigger('click')

    const drawer = wrapper.getComponent({ name: 'ModelTraceDrawer' })
    expect(drawer.props()).toMatchObject({
      projectId: 'project-1',
      traceId: 'trace-chapter-1',
      open: true,
    })
  })

  it('closes old trace drawer when selecting another chapter', async () => {
    const { wrapper } = await mountView()
    await findTraceButton(wrapper)!.trigger('click')

    await wrapper.findAll('[data-testid="chapter-option"]')[1].trigger('click')
    await flushPromises()

    const drawer = wrapper.getComponent({ name: 'ModelTraceDrawer' })
    expect(drawer.props()).toMatchObject({
      traceId: null,
      open: false,
    })
  })

  it('closes old trace drawer when switching project route', async () => {
    const { wrapper, router } = await mountView()
    await findTraceButton(wrapper)!.trigger('click')

    await router.push('/projects/project-2/manuscript')
    await flushPromises()

    const drawer = wrapper.getComponent({ name: 'ModelTraceDrawer' })
    expect(drawer.props()).toMatchObject({
      projectId: 'project-2',
      traceId: null,
      open: false,
    })
  })
})
