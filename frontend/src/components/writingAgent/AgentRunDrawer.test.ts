// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import AgentRunDrawer from './AgentRunDrawer.vue'

describe('AgentRunDrawer', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('renders writing agent run detail and steps', () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-1',
          project_id: 'project-1',
          goal: '恢复上一轮阻塞',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-1',
              run_id: 'run-1',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'describe_agent_tools',
              status: 'success',
              input: {},
              output: {},
            },
            {
              id: 'step-2',
              run_id: 'run-1',
              project_id: 'project-1',
              step_index: 2,
              tool_name: 'plan_recovery_tools',
              status: 'success',
              input: {},
              output: {},
            },
          ],
        },
      },
    })

    expect(document.body.textContent).toContain('恢复上一轮阻塞')
    expect(document.body.textContent).toContain('success')
    expect(document.body.textContent).toContain('run-1')
    expect(document.body.textContent).toContain('describe_agent_tools')
    expect(document.body.textContent).toContain('plan_recovery_tools')

    const refresh = document.body.querySelector('[data-testid="refresh-agent-run"]') as HTMLButtonElement
    expect(refresh).not.toBeNull()
    refresh.click()
    expect(wrapper.emitted('refresh')).toEqual([[]])
  })

  it('renders loading and error states', () => {
    const loading = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: true,
        error: '',
        run: null,
      },
    })

    expect(document.body.textContent).toContain('正在加载 Agent 运行详情')

    loading.unmount()
    document.body.innerHTML = ''
    const failed = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '加载失败',
        run: null,
      },
    })

    expect(document.body.textContent).toContain('加载失败')
    failed.unmount()
  })

  it('renders recovery execution policy and guardrails', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-recovery',
          project_id: 'project-1',
          goal: '恢复上一轮阻塞',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-recovery',
              run_id: 'run-recovery',
              project_id: 'project-1',
              step_index: 2,
              tool_name: 'plan_recovery_tools',
              status: 'success',
              input: {},
              output: {
                execution_policy: {
                  mode: 'preview',
                  status: 'requires_user_input',
                  requires_confirmation: true,
                  requires_plan_hash: true,
                  safe_auto_execute: false,
                },
                guardrails: {
                  status: 'blocked',
                  blockers: [
                    {
                      code: 'requires_user_input',
                      tool_name: 'prepare_generate_chapter_execution',
                      message: '恢复工具需要用户补充输入，不能自动执行。',
                    },
                  ],
                },
                tools: [{ tool_name: 'prepare_generate_chapter_execution' }],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('运行类型')
    expect(text).toContain('恢复预览')
    expect(text).toContain('恢复执行策略')
    expect(text).toContain('需要用户补充输入')
    expect(text).toContain('需要确认')
    expect(text).toContain('需要计划哈希')
    expect(text).toContain('不允许自动执行')
    expect(text).toContain('保护策略')
    expect(text).toContain('恢复工具需要用户补充输入')
    expect(text).toContain('prepare_generate_chapter_execution')
    expect(document.body.querySelector('[data-testid="execute-recovery"]')).toBeNull()
  })

  it('emits confirmed recovery execution payload when preview is executable', async () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-recovery',
          project_id: 'project-1',
          goal: '恢复上一轮阻塞',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-recovery',
              run_id: 'run-recovery',
              project_id: 'project-1',
              step_index: 2,
              tool_name: 'plan_recovery_tools',
              status: 'success',
              input: {},
              output: {
                can_execute: true,
                source_run_id: 'source-run-1',
                plan_hash: 'plan-hash-1',
                execution_policy: {
                  mode: 'preview',
                  status: 'ready',
                  requires_confirmation: true,
                  requires_plan_hash: true,
                  safe_auto_execute: false,
                },
                guardrails: {
                  status: 'ready',
                  blockers: [],
                },
                tools: [{ tool_name: 'prepare_generate_chapter_execution' }],
              },
            },
          ],
        },
      },
    })

    const button = document.body.querySelector('[data-testid="execute-recovery"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    expect(button.textContent).toContain('确认执行恢复')

    await button.click()

    expect(wrapper.emitted('executeRecovery')).toEqual([
      [{ sourceRunId: 'source-run-1', planHash: 'plan-hash-1' }],
    ])
  })

  it('renders route upgrade guarded apply only for eligible contract preview runs without leaking contract internals', async () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        pendingActionId: 'action-1',
        run: {
          id: 'run-contract',
          project_id: 'project-1',
          goal: '生成待确认操作的路由升级审批契约',
          status: 'success',
          entrypoint: 'pending_action_safety_action',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-contract',
              run_id: 'run-contract',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'preview_pending_action_route_approval_opt_in_apply_contract',
              status: 'success',
              input: {},
              output: {
                status: 'requires_confirmation',
                required_confirmation: true,
                pending_action_id: 'action-1',
                approval_contract_hash: 'approval:secret',
                approval_contract: { approval: { approval_contract_hash: 'approval:secret' } },
                recommended_next_tools: ['apply_pending_action_route_approval_opt_in'],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('路由升级审批')
    expect(text).toContain('等待确认')
    expect(text).toContain('需要确认')
    expect(text).not.toContain('approval:secret')
    expect(text).not.toContain('approval_contract')

    const button = document.body.querySelector('[data-testid="apply-route-upgrade"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    await button.click()

    expect(wrapper.emitted('applyRouteUpgrade')).toEqual([[
      {
        sourceRunId: 'run-contract',
        pendingActionId: 'action-1',
        approvalContractHash: 'approval:secret',
        approvalContract: { approval: { approval_contract_hash: 'approval:secret' } },
      },
    ]])
  })

  it('does not render route upgrade apply when contract preview is not confirmable', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-contract',
          project_id: 'project-1',
          goal: '无需升级',
          status: 'success',
          entrypoint: 'pending_action_safety_action',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-contract',
              run_id: 'run-contract',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'preview_pending_action_route_approval_opt_in_apply_contract',
              status: 'success',
              input: {},
              output: {
                status: 'not_required',
                required_confirmation: false,
                pending_action_id: 'action-1',
                recommended_next_tools: [],
              },
            },
          ],
        },
      },
    })

    expect(document.body.querySelector('[data-testid="apply-route-upgrade"]')).toBeNull()
  })

  it('does not render route upgrade apply for stale or unrelated contract runs', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        pendingActionId: 'action-current',
        run: {
          id: 'run-contract',
          project_id: 'project-1',
          goal: '生成待确认操作的路由升级审批契约',
          status: 'success',
          entrypoint: 'manual_debug_run',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-contract',
              run_id: 'run-contract',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'preview_pending_action_route_approval_opt_in_apply_contract',
              status: 'success',
              input: {},
              output: {
                status: 'requires_confirmation',
                required_confirmation: true,
                pending_action_id: 'action-stale',
                approval_contract_hash: 'approval:secret',
                approval_contract: { approval: { approval_contract_hash: 'approval:secret' } },
                recommended_next_tools: ['apply_pending_action_route_approval_opt_in'],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).not.toContain('approval:secret')
    expect(document.body.querySelector('[data-testid="apply-route-upgrade"]')).toBeNull()
  })

  it('labels confirmed recovery execution runs with source metadata', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-executed',
          project_id: 'project-1',
          goal: '执行恢复计划',
          status: 'success',
          entrypoint: 'ui_recovery_execute',
          input: {
            execute_recovery: true,
            recovery_run_id: 'source-run-1',
            recovery_plan_hash: 'plan-hash-1',
          },
          output: null,
          error: null,
          steps: [],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('运行类型')
    expect(text).toContain('恢复执行')
    expect(text).toContain('来源运行')
    expect(text).toContain('source-run-1')
    expect(text).toContain('计划哈希')
    expect(text).toContain('plan-hash-1')
  })
})
