// @vitest-environment jsdom
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import HermesView from './HermesView.vue'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getWorkspaceBootstrap: vi.fn(),
    startWriting: vi.fn(),
    pauseWriting: vi.fn(),
    resumeWriting: vi.fn(),
    regenerateRevision: vi.fn(),
    getMessages: vi.fn(),
    getDiagnosis: vi.fn(),
    getProject: vi.fn(),
    listChapters: vi.fn(),
    listVersions: vi.fn(),
    getWritingState: vi.fn(),
    getChapter: vi.fn(),
  },
}))

const regeneratedChapter = {
  id: 'chapter-1',
  project_id: 'project-1',
  chapter_index: 1,
  title: '第一章',
  content: '重写后的正文',
  word_count: 6,
  status: 'generated',
  model: 'deepseek-chat',
  prompt_tokens: 10,
  completion_tokens: 20,
  generation_time: 1000,
  temperature: 0.7,
  created_at: '2026-04-24T00:00:00Z',
  updated_at: '2026-04-24T00:00:00Z',
}

function workspaceBootstrap() {
  return {
    project: {
      id: 'project-1',
      name: '长篇测试项目',
      current_word_count: 0,
    },
    diagnosis: {
      missing_items: [],
      completed_items: [],
      suggested_next_step: null,
    },
    setup: null,
    storyline: null,
    outline: null,
    chapters: [],
    versions: [],
    writing_state: {
      project_id: 'project-1',
      current_chapter: 12,
      status: 'idle',
      last_error: null,
    },
    dialogs: {
      hermes: { messages: [] },
    },
  }
}

async function mountHermesView(path = '/projects/project-1/hermes') {
  document.body.innerHTML = '<div id="app"></div><div data-subnav-content></div>'
  setActivePinia(createPinia())
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/projects/:id/hermes', component: HermesView }],
  })
  await router.push(path)
  await router.isReady()
  const wrapper = mount(HermesView, {
    attachTo: document.getElementById('app') as HTMLElement,
    global: {
      plugins: [router],
      stubs: {
        ChatMessageList: { template: '<div data-testid="chat-message-list" />' },
        ChatInput: { template: '<div data-testid="chat-input" />' },
        ExportModal: { template: '<div />' },
        VersionsModal: { template: '<div />' },
        ModelTraceDrawer: { template: '<div />' },
      },
    },
  })
  await flushPromises()
  return wrapper
}

describe('HermesView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getWorkspaceBootstrap).mockResolvedValue(workspaceBootstrap() as any)
    vi.mocked(api.startWriting).mockResolvedValue({
      project_id: 'project-1',
      current_chapter: 12,
      status: 'running',
      last_error: null,
    })
    vi.mocked(api.regenerateRevision).mockResolvedValue(regeneratedChapter as any)
    vi.mocked(api.getMessages).mockResolvedValue([])
    vi.mocked(api.getDiagnosis).mockResolvedValue({
      missing_items: [],
      completed_items: ['content'],
      suggested_next_step: null,
    })
    vi.mocked(api.getProject).mockResolvedValue({
      id: 'project-1',
      name: '长篇测试项目',
      current_word_count: 6,
    } as any)
    vi.mocked(api.listChapters).mockResolvedValue({
      chapters: [regeneratedChapter],
      total: 1,
      offset: 0,
      limit: 200,
      has_more: false,
      latest_chapter_index: 1,
    } as any)
    vi.mocked(api.listVersions).mockResolvedValue({
      versions: [],
      total: 0,
      offset: 0,
      limit: 20,
      has_more: false,
    } as any)
    vi.mocked(api.getWritingState).mockResolvedValue({
      project_id: 'project-1',
      current_chapter: 2,
      status: 'idle',
      last_error: null,
    } as any)
    vi.mocked(api.getChapter).mockResolvedValue(regeneratedChapter as any)
  })

  it('starts writing from the dashboard control', async () => {
    const wrapper = await mountHermesView()
    const control = document.querySelector('[data-testid="dashboard-writing-control"]') as HTMLButtonElement

    expect(control.textContent).toContain('开始')
    control.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    await flushPromises()

    expect(api.startWriting).toHaveBeenCalledWith('project-1')

    wrapper.unmount()
  })

  it('refreshes project totals and writing state after revision regeneration', async () => {
    const wrapper = await mountHermesView('/projects/project-1/hermes?revision_id=revision-1')

    expect(api.regenerateRevision).toHaveBeenCalledWith('project-1', 'revision-1')
    expect(api.getProject).toHaveBeenCalledWith('project-1')
    expect(api.listChapters).toHaveBeenCalledWith('project-1', undefined)
    expect(api.listVersions).toHaveBeenCalledWith('project-1', undefined, { offset: 0, limit: 50 })
    expect(api.getWritingState).toHaveBeenCalledWith('project-1')
    expect(api.getChapter).toHaveBeenCalledWith('project-1', 1)

    wrapper.unmount()
  })
})
