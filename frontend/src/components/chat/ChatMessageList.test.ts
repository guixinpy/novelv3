// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ChatMessageList from './ChatMessageList.vue'

describe('ChatMessageList', () => {
  it('forwards openTrace from child messages', async () => {
    const wrapper = mount(ChatMessageList, {
      props: {
        messages: [
          {
            role: 'assistant',
            content: '带 trace 的回复',
            trace_id: 'trace-list-1',
          },
        ],
        loading: false,
      },
    })

    await wrapper.get('[data-testid="open-trace"]').trigger('click')

    expect(wrapper.emitted('openTrace')).toEqual([['trace-list-1']])
  })

  it('forwards openAgentRun from child messages', async () => {
    const wrapper = mount(ChatMessageList, {
      props: {
        messages: [
          {
            role: 'assistant',
            content: '恢复预览已生成。',
            action_result: {
              type: 'plan_recovery_tools',
              status: 'success',
              data: { agent_run_id: 'run-list-1' },
            },
            action_result_view: {
              type: 'plan_recovery_tools',
              status: 'success',
              label: '恢复预览已生成',
              variant: 'success',
            },
          },
        ],
        loading: false,
      },
    })

    await wrapper.get('[data-testid="open-agent-run"]').trigger('click')

    expect(wrapper.emitted('openAgentRun')).toEqual([['run-list-1']])
  })

  it('forwards executeRecommendedFollowups from child messages', async () => {
    const wrapper = mount(ChatMessageList, {
      props: {
        messages: [
          {
            role: 'assistant',
            content: '推荐后继预览已生成。',
            action_result: {
              type: 'plan_recommended_followups',
              status: 'success',
              data: {
                agent_run_id: 'preview-run-1',
                source_run_id: 'source-run-2',
                plan_hash: 'followup-plan-hash-1',
                execution_policy: {
                  requires_followup_run: true,
                  requires_plan_hash: true,
                },
                tools: [{ tool_name: 'inspect_agent_memory_route' }],
              },
            },
            action_result_view: {
              type: 'plan_recommended_followups',
              status: 'success',
              label: '推荐后继预览已生成',
              variant: 'success',
            },
          },
        ],
        loading: false,
      },
    })

    await wrapper.get('[data-testid="execute-recommended-followups"]').trigger('click')

    expect(wrapper.emitted('executeRecommendedFollowups')).toEqual([
      [{ sourceRunId: 'source-run-2', planHash: 'followup-plan-hash-1' }],
    ])
  })

  it('forwards pending action safety actions from child messages', async () => {
    const wrapper = mount(ChatMessageList, {
      props: {
        messages: [
          {
            role: 'assistant',
            content: '准备生成设定。',
            pending_action: {
              id: 'pending-list-1',
              type: 'preview_setup',
              description: '我可以生成设定。',
              params: {},
              safety_view: {
                kind: 'pending_action_safety',
                recommendations: [
                  {
                    kind: 'route_upgrade_preview',
                    title: '可先生成路由升级审批契约',
                    message: '这只生成审批准备信息，不会执行当前待确认操作。',
                    severity: 'info',
                    auto_execute: false,
                    guarded_apply: false,
                    action: {
                      kind: 'prepare_route_upgrade_contract',
                      label: '生成审批契约',
                      pending_action_id: 'pending-list-1',
                      auto_execute: false,
                      guarded_apply: false,
                    },
                  },
                ],
              },
            },
          },
        ],
        loading: false,
      },
    })

    await wrapper.get('[data-testid="pending-action-safety-prepare"]').trigger('click')

    expect(wrapper.emitted('safetyAction')).toEqual([
      [
        {
          kind: 'prepare_route_upgrade_contract',
          label: '生成审批契约',
          pending_action_id: 'pending-list-1',
          auto_execute: false,
          guarded_apply: false,
        },
      ],
    ])
  })
})
