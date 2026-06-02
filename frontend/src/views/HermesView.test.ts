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
    getChatCommandCatalog: vi.fn(),
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
          emits: ['openAgentRun', 'safetyAction', 'executeRecommendedFollowups'],
          template: '<div data-testid="chat-message-list"><button data-testid="stub-open-agent-run" @click="$emit(\'openAgentRun\', \'run-1\')">open run</button><button data-testid="stub-safety-action" @click="$emit(\'safetyAction\', { kind: \'prepare_route_upgrade_contract\', label: \'生成审批契约\', pending_action_id: \'action-1\', auto_execute: false, guarded_apply: false })">safety</button><button data-testid="stub-chat-execute-followups" @click="$emit(\'executeRecommendedFollowups\', { sourceRunId: \'source-run-chat\', planHash: \'followup-plan-hash-chat\' })">chat execute followups</button><span data-testid="stub-last-message">{{ messages[messages.length - 1]?.content }}</span></div>',
        },
        ChatInput: {
          props: ['commands'],
          template: '<div data-testid="chat-input">{{ commands?.map((command) => command.name).join(",") }}</div>',
        },
        ExportModal: { template: '<div />' },
        VersionsModal: { template: '<div />' },
        ModelTraceDrawer: { template: '<div />' },
        AgentRunDrawer: {
          props: ['open', 'run', 'memoryTreeHistory'],
          emits: ['close', 'executeRecovery', 'executeRecommendedFollowups', 'executePlannerPlan', 'refresh', 'applyRouteUpgrade'],
          template: '<div v-if="open" data-testid="agent-run-drawer">{{ run && run.id }}<span data-testid="stub-memory-tree-history">{{ (memoryTreeHistory || []).map((item) => item.label).join("|") }}</span><button data-testid="stub-close-agent-run" @click="$emit(\'close\')">close</button><button data-testid="stub-execute-recovery" @click="$emit(\'executeRecovery\', { sourceRunId: \'source-run-1\', planHash: \'plan-hash-1\' })">execute</button><button data-testid="stub-execute-followups" @click="$emit(\'executeRecommendedFollowups\', { sourceRunId: \'source-run-2\', planHash: \'followup-plan-hash-1\' })">execute followups</button><button data-testid="stub-execute-planner-plan" @click="$emit(\'executePlannerPlan\', { sourceRunId: run && run.id, sourcePlanId: \'plan:review-12\', goal: \'执行规划工具链：审稿章节\', tools: [{ tool_name: \'review_chapter_quality\', params: { chapter_index: 12 }, planner: { plan_id: \'plan:review-12\' } }], planner: { trace: { plan_id: \'plan:review-12\' }, approval_contract: { status: \'not_required\' }, tools: [{ tool_name: \'review_chapter_quality\', params: { chapter_index: 12 }, planner: { plan_id: \'plan:review-12\' } }] } })">execute planner</button><button data-testid="stub-execute-memory-tree-plan" @click="$emit(\'executePlannerPlan\', { sourceRunId: run && run.id, sourcePlanId: \'memory-tree-node-expand:0\', goal: \'展开 Memory Tree：第2章\', tools: [{ tool_name: \'inspect_agent_memory_tree\', params: { expand_node_id: \'scene:memory-3\', include_ancestors: true, max_depth: 1 }, planner: { plan_id: \'memory-tree-node-expand:0\', mutability: \'read\', requires_confirmation: false } }], planner: { trace: { plan_id: \'memory-tree-node-expand:0\' }, approval_contract: { status: \'not_required\' }, tools: [{ tool_name: \'inspect_agent_memory_tree\', params: { expand_node_id: \'scene:memory-3\', include_ancestors: true, max_depth: 1 }, planner: { plan_id: \'memory-tree-node-expand:0\', mutability: \'read\', requires_confirmation: false } }] } })">memory tree</button><button data-testid="stub-execute-planner-plan-approved" @click="$emit(\'executePlannerPlan\', { sourceRunId: run && run.id, sourcePlanId: \'plan:chapter-2\', goal: \'执行规划工具链：续写下一章\', tools: [{ tool_name: \'generate_chapter\', params: { chapter_index: 2 }, planner: { plan_id: \'plan:chapter-2\', mutability: \'write\', requires_confirmation: true } }], planner: { trace: { plan_id: \'plan:chapter-2\' }, approval_contract: { status: \'requires_confirmation\', approval: { approval_contract_hash: \'approval:secret\' } }, tools: [{ tool_name: \'generate_chapter\', params: { chapter_index: 2 }, planner: { plan_id: \'plan:chapter-2\', mutability: \'write\', requires_confirmation: true } }] }, approvalContractHash: \'approval:secret\', approvalContract: { status: \'requires_confirmation\', approval: { approval_contract_hash: \'approval:secret\' } } })">execute approved planner</button><button data-testid="stub-execute-planner-plan-stale" @click="$emit(\'executePlannerPlan\', { sourceRunId: \'stale-run\', sourcePlanId: \'plan:review-12\', goal: \'执行规划工具链：审稿章节\', tools: [{ tool_name: \'review_chapter_quality\', params: { chapter_index: 12 } }], planner: { trace: { plan_id: \'plan:review-12\' }, approval_contract: { status: \'not_required\' } } })">stale planner</button><button data-testid="stub-refresh-agent-run" @click="$emit(\'refresh\')">refresh</button><button data-testid="stub-apply-route-upgrade" @click="$emit(\'applyRouteUpgrade\', { sourceRunId: run && run.id, pendingActionId: \'action-1\', approvalContractHash: \'approval:secret\', approvalContract: { approval: { approval_contract_hash: \'approval:secret\' } } })">apply route</button><button data-testid="stub-apply-route-upgrade-stale" @click="$emit(\'applyRouteUpgrade\', { sourceRunId: \'stale-run\', pendingActionId: \'action-1\', approvalContractHash: \'approval:secret\', approvalContract: { approval: { approval_contract_hash: \'approval:secret\' } } })">stale route</button></div>',
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
    vi.mocked(api.getChatCommandCatalog).mockResolvedValue({
      version: 'phase26.agent_chat_command_catalog.v1',
      public_command_names: ['continue', 'status', 'clear', 'compact'],
      legacy_alias_names: ['setup', 'storyline', 'outline', 'chapter'],
      commands: [
        {
          name: 'continue',
          label: '/continue',
          description: '继续',
          example: '/continue',
          supports_args: false,
          public: true,
        },
        {
          name: 'setup',
          label: '/setup',
          description: '旧命令',
          example: '/setup',
          supports_args: true,
          public: false,
          legacy: true,
        },
      ],
    } as any)
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

  it('loads backend command catalog and passes it to chat input', async () => {
    const wrapper = await mountHermesView()

    expect(api.getChatCommandCatalog).toHaveBeenCalled()
    expect(wrapper.get('[data-testid="chat-input"]').text()).toContain('continue')
    expect(wrapper.get('[data-testid="chat-input"]').text()).toContain('setup')

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

  it('creates a confirmed recommended followup execution run from the agent drawer', async () => {
    vi.mocked((api as any).createAgentRun).mockResolvedValueOnce({
      id: 'run-followups-executed',
      project_id: 'project-1',
      goal: '执行推荐后继',
      status: 'success',
      entrypoint: 'ui_recommended_followup_execute',
      input: {},
      output: null,
      error: null,
      steps: [],
    })
    const wrapper = await mountHermesView()

    await wrapper.get('[data-testid="stub-open-agent-run"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="stub-execute-followups"]').trigger('click')
    await flushPromises()

    expect((api as any).createAgentRun).toHaveBeenCalledWith('project-1', {
      goal: '执行推荐后继工具链',
      entrypoint: 'ui_recommended_followup_execute',
      input: {
        auto_plan: true,
        recommended_followup_run_id: 'source-run-2',
        execute_recommended_followups: true,
        confirm_execute: true,
        recommended_followup_plan_hash: 'followup-plan-hash-1',
      },
    })
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).toContain('run-followups-executed')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).toContain('推荐后继执行已创建')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).not.toContain('followup-plan-hash-1')

    wrapper.unmount()
  })

  it('creates a confirmed recommended followup execution run from the chat action card', async () => {
    vi.mocked((api as any).createAgentRun).mockResolvedValueOnce({
      id: 'run-chat-followups-executed',
      project_id: 'project-1',
      goal: '执行推荐后继',
      status: 'success',
      entrypoint: 'ui_recommended_followup_execute',
      input: {},
      output: null,
      error: null,
      steps: [],
    })
    const wrapper = await mountHermesView()

    await wrapper.get('[data-testid="stub-chat-execute-followups"]').trigger('click')
    await flushPromises()

    expect((api as any).createAgentRun).toHaveBeenCalledWith('project-1', {
      goal: '执行推荐后继工具链',
      entrypoint: 'ui_recommended_followup_execute',
      input: {
        auto_plan: true,
        recommended_followup_run_id: 'source-run-chat',
        execute_recommended_followups: true,
        confirm_execute: true,
        recommended_followup_plan_hash: 'followup-plan-hash-chat',
      },
    })
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).toContain('推荐后继执行已创建')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).not.toContain('followup-plan-hash-chat')

    wrapper.unmount()
  })

  it('creates a planner continuation run from the active agent drawer without leaking approval internals', async () => {
    vi.mocked((api as any).createAgentRun).mockResolvedValueOnce({
      id: 'run-planner-executed',
      project_id: 'project-1',
      goal: '执行规划工具链：审稿章节',
      status: 'success',
      entrypoint: 'ui_planner_continuation_execute',
      input: {},
      output: null,
      error: null,
      steps: [{ id: 'step-1', tool_name: 'review_chapter_quality', status: 'success' }],
    })
    const wrapper = await mountHermesView()

    await wrapper.get('[data-testid="stub-open-agent-run"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="stub-execute-planner-plan"]').trigger('click')
    await flushPromises()

    expect((api as any).createAgentRun).toHaveBeenCalledWith('project-1', {
      goal: '执行规划工具链：审稿章节',
      entrypoint: 'ui_planner_continuation_execute',
      tools: [
        {
          tool_name: 'review_chapter_quality',
          params: { chapter_index: 12 },
          planner: { plan_id: 'plan:review-12' },
        },
      ],
      input: {
        planner_continuation: true,
        source_run_id: 'run-1',
        source_plan_id: 'plan:review-12',
        planner: {
          trace: { plan_id: 'plan:review-12' },
          approval_contract: { status: 'not_required' },
          tools: [
            {
              tool_name: 'review_chapter_quality',
              params: { chapter_index: 12 },
              planner: { plan_id: 'plan:review-12' },
            },
          ],
        },
      },
    })
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).toContain('run-planner-executed')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).toContain('规划工具链执行已创建')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).not.toContain('approval_contract')

    wrapper.unmount()
  })

  it('preserves safe memory tree navigation history after a planner continuation run', async () => {
    vi.mocked((api as any).createAgentRun).mockResolvedValueOnce({
      id: 'run-memory-tree-result',
      project_id: 'project-1',
      goal: '展开 Memory Tree：第2章',
      status: 'success',
      entrypoint: 'ui_planner_continuation_execute',
      input: {},
      output: null,
      error: null,
      steps: [
        {
          id: 'step-memory-tree',
          tool_name: 'inspect_agent_memory_tree',
          status: 'success',
        },
      ],
    })
    const wrapper = await mountHermesView()

    await wrapper.get('[data-testid="stub-open-agent-run"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="stub-execute-memory-tree-plan"]').trigger('click')
    await flushPromises()

    expect((api as any).createAgentRun).toHaveBeenCalledWith('project-1', {
      goal: '展开 Memory Tree：第2章',
      entrypoint: 'ui_planner_continuation_execute',
      tools: [
        {
          tool_name: 'inspect_agent_memory_tree',
          params: {
            expand_node_id: 'scene:memory-3',
            include_ancestors: true,
            max_depth: 1,
          },
          planner: {
            plan_id: 'memory-tree-node-expand:0',
            mutability: 'read',
            requires_confirmation: false,
          },
        },
      ],
      input: {
        planner_continuation: true,
        source_run_id: 'run-1',
        source_plan_id: 'memory-tree-node-expand:0',
        planner: {
          trace: { plan_id: 'memory-tree-node-expand:0' },
          approval_contract: { status: 'not_required' },
          tools: [
            {
              tool_name: 'inspect_agent_memory_tree',
              params: {
                expand_node_id: 'scene:memory-3',
                include_ancestors: true,
                max_depth: 1,
              },
              planner: {
                plan_id: 'memory-tree-node-expand:0',
                mutability: 'read',
                requires_confirmation: false,
              },
            },
          ],
        },
      },
    })
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).toContain('run-memory-tree-result')
    expect(wrapper.get('[data-testid="stub-memory-tree-history"]').text()).toContain('节点展开：第2章')
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).not.toContain('scene:memory-3')
    const memoryTreePanel = document.querySelector('[data-testid="memory-tree-history-panel"]') as HTMLElement
    expect(memoryTreePanel).not.toBeNull()
    expect(memoryTreePanel.textContent).toContain('Memory Tree')
    expect(memoryTreePanel.textContent).toContain('节点展开：第2章')
    expect(memoryTreePanel.textContent).not.toContain('scene:memory-3')

    await wrapper.get('[data-testid="stub-close-agent-run"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="agent-run-drawer"]').exists()).toBe(false)

    vi.mocked(api.getAgentRun).mockResolvedValueOnce({
      id: 'run-memory-tree-result',
      project_id: 'project-1',
      goal: '展开 Memory Tree：第2章',
      status: 'success',
      entrypoint: 'ui_planner_continuation_execute',
      input: {},
      output: null,
      error: null,
      steps: [],
    } as any)
    const historyButton = document.querySelector('[data-testid="memory-tree-history-open"]') as HTMLButtonElement
    expect(historyButton).not.toBeNull()
    historyButton.click()
    await flushPromises()
    expect(api.getAgentRun).toHaveBeenCalledWith('project-1', 'run-memory-tree-result')
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).toContain('run-memory-tree-result')
    expect(wrapper.get('[data-testid="stub-memory-tree-history"]').text()).toContain('节点展开：第2章')

    wrapper.unmount()
  })

  it('creates a read-only memory tree search run from the subnav panel', async () => {
    vi.mocked((api as any).createAgentRun).mockResolvedValueOnce({
      id: 'run-memory-tree-search',
      project_id: 'project-1',
      goal: '搜索 Memory Tree：灯塔旧回声',
      status: 'success',
      entrypoint: 'ui_memory_tree_panel_search',
      input: {},
      output: null,
      error: null,
      steps: [
        {
          id: 'step-memory-tree-search',
          tool_name: 'inspect_agent_memory_tree',
          status: 'success',
          output: {
            status: 'ready',
            filters: {
              query: '灯塔旧回声',
              include_ancestors: true,
            },
            summary: {
              volume_nodes: 1,
              chapter_nodes: 1,
              scene_nodes: 1,
              beat_nodes: 0,
            },
            nodes: [
              {
                id: 'chapter:2',
                level: 'chapter',
                chapter_index: 2,
                title: '灯塔旧回声',
                summary: '主角在灯塔发现旧回声线索。',
                source_refs: [
                  { source_type: 'chapter_content', source_id: 'chapter-content-2' },
                  { source_type: 'longform_memory', source_id: 'memory-2' },
                ],
                relevance: {
                  score: 1.2,
                },
              },
              {
                id: 'scene:memory-3',
                level: 'scene',
                chapter_index: 2,
                summary: '补充场景摘要。',
                source_refs: [{ source_type: 'longform_memory', source_id: 'memory-3' }],
              },
            ],
          },
        },
      ],
    })
    const wrapper = await mountHermesView()

    const panel = document.querySelector('[data-testid="memory-tree-history-panel"]') as HTMLElement
    expect(panel).not.toBeNull()
    const input = document.querySelector('[data-testid="memory-tree-panel-query"]') as HTMLInputElement
    expect(input).not.toBeNull()
    input.value = '灯塔旧回声'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    await flushPromises()
    const searchButton = document.querySelector('[data-testid="memory-tree-panel-search"]') as HTMLButtonElement
    searchButton.click()
    await flushPromises()

    expect((api as any).createAgentRun).toHaveBeenCalledWith('project-1', {
      goal: '搜索 Memory Tree：灯塔旧回声',
      entrypoint: 'ui_memory_tree_panel_search',
      tools: [
        {
          tool_name: 'inspect_agent_memory_tree',
          params: {
            query: '灯塔旧回声',
            include_ancestors: true,
            max_depth: 2,
          },
        },
      ],
      input: {
        memory_tree_panel_search: true,
        query: '灯塔旧回声',
      },
    })
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).toContain('run-memory-tree-search')
    expect(wrapper.get('[data-testid="stub-memory-tree-history"]').text()).toContain('搜索：灯塔旧回声')
    expect(panel.textContent).toContain('搜索：灯塔旧回声')
    const resultPanel = document.querySelector('[data-testid="memory-tree-panel-results"]') as HTMLElement
    expect(resultPanel).not.toBeNull()
    expect(resultPanel.textContent).toContain('返回 2 个')
    expect(resultPanel.textContent).toContain('卷 1 / 章节 1 / 场景 1 / 节拍 0')
    const resultNodes = Array.from(document.querySelectorAll('[data-testid="memory-tree-panel-result-node"]'))
    expect(resultNodes).toHaveLength(2)
    expect(resultNodes[0].textContent).toContain('章节')
    expect(resultNodes[0].textContent).toContain('第2章')
    expect(resultNodes[0].textContent).toContain('灯塔旧回声')
    expect(resultNodes[0].textContent).toContain('主角在灯塔发现旧回声线索。')
    expect(resultNodes[0].textContent).toContain('相关度 1.20')
    expect(resultNodes[1].textContent).toContain('场景')
    expect(resultNodes[1].textContent).toContain('补充场景摘要。')
    expect(panel.textContent).not.toContain('approval')
    expect(panel.textContent).not.toContain('chapter-content-2')
    expect(panel.textContent).not.toContain('memory-2')
    expect(panel.textContent).not.toContain('scene:memory-3')
    expect(panel.textContent).not.toContain('source_refs')

    wrapper.unmount()
  })

  it('creates a read-only memory tree expand run from a subnav result node', async () => {
    const searchRun = {
      id: 'run-memory-tree-search',
      project_id: 'project-1',
      goal: '搜索 Memory Tree：灯塔旧回声',
      status: 'success',
      entrypoint: 'ui_memory_tree_panel_search',
      input: {},
      output: null,
      error: null,
      steps: [
        {
          id: 'step-memory-tree-search',
          tool_name: 'inspect_agent_memory_tree',
          status: 'success',
          output: {
            status: 'ready',
            summary: {
              volume_nodes: 1,
              chapter_nodes: 1,
              scene_nodes: 1,
              beat_nodes: 0,
            },
            nodes: [
              {
                id: 'chapter:2',
                level: 'chapter',
                chapter_index: 2,
                title: '灯塔旧回声',
                summary: '主角在灯塔发现旧回声线索。',
                children: ['scene:memory-3'],
                source_refs: [{ source_type: 'chapter_content', source_id: 'chapter-content-2' }],
              },
            ],
          },
        },
      ],
    }
    const expandedRun = {
      id: 'run-memory-tree-expanded',
      project_id: 'project-1',
      goal: '展开 Memory Tree：灯塔旧回声',
      status: 'success',
      entrypoint: 'ui_memory_tree_panel_expand',
      input: {},
      output: null,
      error: null,
      steps: [
        {
          id: 'step-memory-tree-expanded',
          tool_name: 'inspect_agent_memory_tree',
          status: 'success',
          output: {
            status: 'ready',
            navigation: {
              mode: 'expanded_subtree',
              expanded_node_id: 'chapter:2',
            },
            nodes: [
              {
                id: 'chapter:2',
                level: 'chapter',
                chapter_index: 2,
                title: '灯塔旧回声',
                summary: '主角在灯塔发现旧回声线索。',
                children: ['scene:memory-3'],
              },
              {
                id: 'scene:memory-3',
                level: 'scene',
                chapter_index: 2,
                summary: '补充场景摘要。',
              },
            ],
          },
        },
      ],
    }
    vi.mocked((api as any).createAgentRun).mockImplementation(async (_projectId: string, payload: any) => (
      payload.entrypoint === 'ui_memory_tree_panel_expand' ? expandedRun : searchRun
    ))
    const wrapper = await mountHermesView()

    const input = document.querySelector('[data-testid="memory-tree-panel-query"]') as HTMLInputElement
    input.value = '灯塔旧回声'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    await flushPromises()
    const searchButton = document.querySelector('[data-testid="memory-tree-panel-search"]') as HTMLButtonElement
    searchButton.click()
    await flushPromises()

    const expandButton = document.querySelector('[data-testid="memory-tree-panel-result-expand"]') as HTMLButtonElement
    expect(expandButton).not.toBeNull()
    expandButton.click()
    await flushPromises()

    expect((api as any).createAgentRun).toHaveBeenNthCalledWith(2, 'project-1', {
      goal: '展开 Memory Tree：灯塔旧回声',
      entrypoint: 'ui_memory_tree_panel_expand',
      tools: [
        {
          tool_name: 'inspect_agent_memory_tree',
          params: {
            expand_node_id: 'chapter:2',
            include_ancestors: true,
            max_depth: 1,
          },
        },
      ],
      input: {
        memory_tree_panel_expand: true,
        source_run_id: 'run-memory-tree-search',
        expand_node_label: '灯塔旧回声',
      },
    })
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).toContain('run-memory-tree-expanded')
    expect(wrapper.get('[data-testid="stub-memory-tree-history"]').text()).toContain('节点展开：灯塔旧回声')
    const panel = document.querySelector('[data-testid="memory-tree-history-panel"]') as HTMLElement
    expect(panel.textContent).toContain('当前展开：灯塔旧回声')
    expect(panel.textContent).not.toContain('chapter:2')
    expect(panel.textContent).not.toContain('scene:memory-3')
    expect(panel.textContent).not.toContain('chapter-content-2')

    wrapper.unmount()
  })

  it('creates a confirmed planner continuation run with approval contract binding', async () => {
    vi.mocked((api as any).createAgentRun).mockResolvedValueOnce({
      id: 'run-planner-approved-executed',
      project_id: 'project-1',
      goal: '执行规划工具链：续写下一章',
      status: 'success',
      entrypoint: 'ui_planner_continuation_execute',
      input: {},
      output: null,
      error: null,
      steps: [{ id: 'step-1', tool_name: 'generate_chapter', status: 'success' }],
    })
    const wrapper = await mountHermesView()

    await wrapper.get('[data-testid="stub-open-agent-run"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="stub-execute-planner-plan-approved"]').trigger('click')
    await flushPromises()

    expect((api as any).createAgentRun).toHaveBeenCalledWith('project-1', {
      goal: '执行规划工具链：续写下一章',
      entrypoint: 'ui_planner_continuation_execute',
      tools: [
        {
          tool_name: 'generate_chapter',
          params: { chapter_index: 2 },
          planner: { plan_id: 'plan:chapter-2', mutability: 'write', requires_confirmation: true },
        },
      ],
      input: {
        planner_continuation: true,
        source_run_id: 'run-1',
        source_plan_id: 'plan:chapter-2',
        confirm_execute: true,
        approval_contract_hash: 'approval:secret',
        approval_contract: {
          status: 'requires_confirmation',
          approval: { approval_contract_hash: 'approval:secret' },
        },
        planner: {
          trace: { plan_id: 'plan:chapter-2' },
          approval_contract: {
            status: 'requires_confirmation',
            approval: { approval_contract_hash: 'approval:secret' },
          },
          tools: [
            {
              tool_name: 'generate_chapter',
              params: { chapter_index: 2 },
              planner: { plan_id: 'plan:chapter-2', mutability: 'write', requires_confirmation: true },
            },
          ],
        },
      },
    })
    expect(wrapper.get('[data-testid="agent-run-drawer"]').text()).toContain('run-planner-approved-executed')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).toContain('规划工具链执行已创建')
    expect(wrapper.get('[data-testid="stub-last-message"]').text()).not.toContain('approval:secret')

    wrapper.unmount()
  })

  it('rejects stale planner continuation events from inactive runs', async () => {
    const wrapper = await mountHermesView()

    await wrapper.get('[data-testid="stub-open-agent-run"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="stub-execute-planner-plan-stale"]').trigger('click')
    await flushPromises()

    expect((api as any).createAgentRun).not.toHaveBeenCalled()

    wrapper.unmount()
  })
})
