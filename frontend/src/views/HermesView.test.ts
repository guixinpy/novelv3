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
    getAgentRun: vi.fn(),
    createAgentRun: vi.fn(),
    resolveAction: vi.fn(),
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
        ChatMessageList: {
          props: ['messages'],
          emits: ['openAgentRun', 'safetyAction'],
          template: '<div data-testid="chat-message-list"><button data-testid="stub-open-agent-run" @click="$emit(\'openAgentRun\', \'run-1\')">open run</button><button data-testid="stub-safety-action" @click="$emit(\'safetyAction\', { kind: \'prepare_route_upgrade_contract\', label: \'生成审批契约\', pending_action_id: \'action-1\', auto_execute: false, guarded_apply: false })">safety</button><span data-testid="stub-last-message">{{ messages[messages.length - 1]?.content }}</span></div>',
        },
        ChatInput: { template: '<div data-testid="chat-input" />' },
        ExportModal: { template: '<div />' },
        VersionsModal: { template: '<div />' },
        ModelTraceDrawer: { template: '<div />' },
        AgentRunDrawer: {
          props: ['open', 'run'],
          emits: ['executeRecovery', 'refresh', 'applyRouteUpgrade'],
          template: '<div v-if="open" data-testid="agent-run-drawer">{{ run && run.id }}<button data-testid="stub-execute-recovery" @click="$emit(\'executeRecovery\', { sourceRunId: \'source-run-1\', planHash: \'plan-hash-1\' })">execute</button><button data-testid="stub-refresh-agent-run" @click="$emit(\'refresh\')">refresh</button><button data-testid="stub-apply-route-upgrade" @click="$emit(\'applyRouteUpgrade\', { sourceRunId: run && run.id, pendingActionId: \'action-1\', approvalContractHash: \'approval:secret\', approvalContract: { approval: { approval_contract_hash: \'approval:secret\' } } })">apply route</button><button data-testid="stub-apply-route-upgrade-stale" @click="$emit(\'applyRouteUpgrade\', { sourceRunId: \'stale-run\', pendingActionId: \'action-1\', approvalContractHash: \'approval:secret\', approvalContract: { approval: { approval_contract_hash: \'approval:secret\' } } })">stale route</button></div>',
        },
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
    vi.mocked(api.getAgentRun).mockResolvedValue({
      id: 'run-1',
      project_id: 'project-1',
      goal: '恢复上一轮阻塞',
      status: 'success',
      entrypoint: 'dialog_auto_plan',
      input: {},
      output: null,
      error: null,
      steps: [],
    } as any)
    vi.mocked((api as any).createAgentRun).mockResolvedValue({
      id: 'run-executed',
      project_id: 'project-1',
      goal: '执行恢复计划',
      status: 'success',
      entrypoint: 'ui_recovery_execute',
      input: {},
      output: null,
      error: null,
      steps: [],
    })
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

  it('opens writing agent run details from chat messages', async () => {
    const wrapper = await mountHermesView()

    await wrapper.get('[data-testid="stub-open-agent-run"]').trigger('click')
    await flushPromises()

    expect(api.getAgentRun).toHaveBeenCalledWith('project-1', 'run-1')
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).toContain('run-1')

    wrapper.unmount()
  })

  it('creates a route contract preview run from pending action safety action without resolving the pending action', async () => {
    vi.mocked(api.getWorkspaceBootstrap).mockResolvedValueOnce({
      ...workspaceBootstrap(),
      dialogs: {
        hermes: {
          messages: [
            {
              id: 'message-1',
              role: 'assistant',
              content: '准备生成设定。',
              created_at: '2026-05-24T10:00:00Z',
              pending_action: {
                id: 'action-1',
                type: 'preview_setup',
                description: '生成设定',
                params: { project_id: 'project-1' },
                requires_confirmation: true,
              },
            },
          ],
        },
      },
    } as any)
    vi.mocked((api as any).createAgentRun).mockResolvedValueOnce({
      id: 'run-safety-1',
      project_id: 'project-1',
      goal: '生成待确认操作的路由升级审批契约',
      status: 'success',
      entrypoint: 'pending_action_safety_action',
      input: {},
      output: null,
      error: null,
      steps: [
        {
          output: {
            status: 'requires_confirmation',
            required_confirmation: true,
            approval_contract_hash: 'approval:secret',
          },
        },
      ],
    })
    const wrapper = await mountHermesView()

    await wrapper.get('[data-testid="stub-safety-action"]').trigger('click')
    await flushPromises()

    expect((api as any).createAgentRun).toHaveBeenCalledWith('project-1', {
      goal: '生成待确认操作的路由升级审批契约',
      entrypoint: 'pending_action_safety_action',
      tools: [
        {
          tool_name: 'preview_pending_action_route_approval_opt_in_apply_contract',
          params: { pending_action_id: 'action-1' },
        },
      ],
      input: {
        safety_action: { kind: 'prepare_route_upgrade_contract' },
        pending_action_id: 'action-1',
      },
    })
    expect((api as any).resolveAction).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).toContain('run-safety-1')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).toContain('路由升级审批契约已生成')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).not.toContain('approval:secret')

    wrapper.unmount()
  })

  it('creates a guarded route upgrade apply run from the agent drawer without resolving the pending action', async () => {
    vi.mocked(api.getWorkspaceBootstrap).mockResolvedValueOnce({
      ...workspaceBootstrap(),
      dialogs: {
        hermes: {
          messages: [
            {
              id: 'message-apply',
              role: 'assistant',
              content: '准备生成设定。',
              created_at: '2026-05-24T10:00:00Z',
              pending_action: {
                id: 'action-1',
                type: 'preview_setup',
                description: '生成设定',
                params: { project_id: 'project-1' },
                requires_confirmation: true,
              },
            },
          ],
        },
      },
    } as any)
    vi.mocked((api as any).createAgentRun).mockResolvedValueOnce({
      id: 'run-apply-1',
      project_id: 'project-1',
      goal: '应用待确认操作的路由升级审批契约',
      status: 'success',
      entrypoint: 'pending_action_route_upgrade_apply',
      input: {
        tools: [
          {
            tool_name: 'apply_pending_action_route_approval_opt_in',
            params: {
              approval_contract_hash: 'approval:secret',
              approval_contract: { approval: { approval_contract_hash: 'approval:secret' } },
            },
          },
        ],
      },
      output: null,
      error: null,
      steps: [
        {
          output: {
            status: 'success',
            write_performed: true,
            reason: 'route_opt_in_apply_completed',
            approval_verification: {
              drift: { expected_approval_contract_hash: 'approval:secret' },
            },
          },
        },
      ],
    })
    const wrapper = await mountHermesView()

    await wrapper.get('[data-testid="stub-open-agent-run"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="stub-apply-route-upgrade"]').trigger('click')
    await flushPromises()

    expect((api as any).createAgentRun).toHaveBeenCalledWith('project-1', {
      goal: '应用待确认操作的路由升级审批契约',
      entrypoint: 'pending_action_route_upgrade_apply',
      tools: [
        {
          tool_name: 'apply_pending_action_route_approval_opt_in',
          params: {
            pending_action_id: 'action-1',
            confirm_apply: true,
            approval_contract_hash: 'approval:secret',
            approval_contract: { approval: { approval_contract_hash: 'approval:secret' } },
          },
        },
      ],
      input: {
        safety_action: { kind: 'apply_route_upgrade_contract' },
        source_run_id: 'run-1',
        pending_action_id: 'action-1',
      },
    })
    expect((api as any).resolveAction).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).toContain('run-apply-1')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).toContain('路由升级应用已创建')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).not.toContain('approval:secret')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).not.toContain('approval_contract')

    wrapper.unmount()
  })

  it('rejects stale route upgrade apply events from inactive runs', async () => {
    vi.mocked(api.getWorkspaceBootstrap).mockResolvedValueOnce({
      ...workspaceBootstrap(),
      dialogs: {
        hermes: {
          messages: [
            {
              id: 'message-apply',
              role: 'assistant',
              content: '准备生成设定。',
              created_at: '2026-05-24T10:00:00Z',
              pending_action: {
                id: 'action-1',
                type: 'preview_setup',
                description: '生成设定',
                params: { project_id: 'project-1' },
                requires_confirmation: true,
              },
            },
          ],
        },
      },
    } as any)
    const wrapper = await mountHermesView()

    await wrapper.get('[data-testid="stub-open-agent-run"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="stub-apply-route-upgrade-stale"]').trigger('click')
    await flushPromises()

    expect((api as any).createAgentRun).not.toHaveBeenCalled()
    expect((api as any).resolveAction).not.toHaveBeenCalled()

    wrapper.unmount()
  })

  it('refreshes the active writing agent run detail from the drawer', async () => {
    const wrapper = await mountHermesView()

    vi.mocked(api.getAgentRun)
      .mockResolvedValueOnce({
        id: 'run-1',
        project_id: 'project-1',
        goal: '恢复上一轮阻塞',
        status: 'running',
        entrypoint: 'dialog_auto_plan',
        input: {},
        output: null,
        error: null,
        steps: [],
      } as any)
      .mockResolvedValueOnce({
        id: 'run-1-refreshed',
        project_id: 'project-1',
        goal: '恢复上一轮阻塞',
        status: 'success',
        entrypoint: 'dialog_auto_plan',
        input: {},
        output: null,
        error: null,
        steps: [],
      } as any)

    await wrapper.get('[data-testid="stub-open-agent-run"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="stub-refresh-agent-run"]').trigger('click')
    await flushPromises()

    expect(api.getAgentRun).toHaveBeenNthCalledWith(1, 'project-1', 'run-1')
    expect(api.getAgentRun).toHaveBeenNthCalledWith(2, 'project-1', 'run-1')
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).toContain('run-1-refreshed')

    wrapper.unmount()
  })

  it('creates a confirmed recovery execution run from the agent drawer', async () => {
    const wrapper = await mountHermesView()

    await wrapper.get('[data-testid="stub-open-agent-run"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="stub-execute-recovery"]').trigger('click')
    await flushPromises()

    expect((api as any).createAgentRun).toHaveBeenCalledWith('project-1', {
      goal: '执行恢复计划',
      entrypoint: 'ui_recovery_execute',
      input: {
        auto_plan: true,
        recovery_run_id: 'source-run-1',
        execute_recovery: true,
        confirm_execute: true,
        recovery_plan_hash: 'plan-hash-1',
      },
    })
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).toContain('run-executed')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).toContain('恢复执行已创建')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).not.toContain('plan-hash-1')

    wrapper.unmount()
  })
})
