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
  },
}))

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

async function mountHermesView() {
  document.body.innerHTML = '<div id="app"></div><div data-subnav-content></div>'
  setActivePinia(createPinia())
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/projects/:id/hermes', component: HermesView }],
  })
  await router.push('/projects/project-1/hermes')
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
})
