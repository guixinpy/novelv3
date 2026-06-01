// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ChatMessage from './ChatMessage.vue'

describe('ChatMessage', () => {
  it('shows assistant message creation time to separate old answers from current context', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          content: '这是历史回复。',
          created_at: '2026-05-12T12:34:56Z',
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('2026-05-12 12:34')
  })

  it('emits openTrace when clicking assistant trace button', async () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          content: '这是带模型调用上下文的回复。',
          trace_id: 'trace-1',
        },
        isLatest: false,
        loading: false,
      },
    })

    await wrapper.get('[data-testid="open-trace"]').trigger('click')

    expect(wrapper.emitted('openTrace')).toEqual([['trace-1']])
  })

  it('does not render trace button without trace id', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          content: '这是普通回复。',
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.find('[data-testid="open-trace"]').exists()).toBe(false)
  })

  it('does not render trace button for user messages', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'user',
          content: '用户消息不显示上下文按钮。',
          trace_id: 'trace-user',
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.find('[data-testid="open-trace"]').exists()).toBe(false)
  })

  it('renders unavailable command feedback with command name and reasons', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'command',
          content: '/continue 暂不可用：缺少 Agent 工具适配器：prepare_generate_chapter_execution。该命令未执行。',
          meta: {
            command_name: 'continue',
            command_available: false,
            unavailable_reasons: ['缺少 Agent 工具适配器：prepare_generate_chapter_execution'],
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    const feedback = wrapper.get('[data-testid="command-feedback"]')
    expect(feedback.text()).toContain('/continue')
    expect(feedback.text()).toContain('暂不可用')
    expect(feedback.text()).toContain('缺少 Agent 工具适配器：prepare_generate_chapter_execution')
    expect(wrapper.text()).toContain('该命令未执行')
  })

  it('renders agent health projection for status command messages', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'command',
          content: 'Agent 状态：部分降级。',
          meta: {
            command_name: 'status',
            agent_health_projection: {
              status: 'degraded',
              agent_worker_route_registry: {
                status: 'passed',
                summary: {
                  routes: 35,
                  ready_routes: 35,
                  unrouted_allowed_tools: 0,
                  issues: 0,
                },
              },
              diagnostics: [
                { code: 'agent_tool_contract_gaps', message: 'Agent 工具契约仍存在迁移或 schema 差距。' },
              ],
              recommended_next_tools: ['inspect_agent_tool_contracts', 'inspect_agent_write_gate_coverage'],
            },
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    const card = wrapper.get('[data-testid="agent-health-card"]')
    expect(card.text()).toContain('Agent 状态')
    expect(card.text()).toContain('部分降级')
    expect(card.text()).toContain('Worker 路由')
    expect(card.text()).toContain('通过')
    expect(card.text()).toContain('未路由 0')
    expect(card.text()).toContain('Agent 工具契约仍存在迁移或 schema 差距')
    expect(card.text()).toContain('inspect_agent_tool_contracts')
  })

  it('renders agent control projection for continue command messages', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'plain',
          content: '第2章正文生成计划已准备完成，等待确认执行。',
          meta: {
            agent_control: {
              version: 'phase32.continue_agent_control.v1',
              command_name: 'continue',
              selected_route: 'chapter_generation',
              reason_code: 'no_recovery_or_followup',
              required_agent_tools: [
                'inspect_agent_health_projection',
                'plan_recovery_tools',
                'plan_recommended_followups',
                'prepare_generate_chapter_execution',
              ],
            },
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    const card = wrapper.get('[data-testid="agent-control-card"]')
    expect(card.text()).toContain('/continue')
    expect(card.text()).toContain('生成下一章')
    expect(card.text()).toContain('无恢复或推荐后继')
    expect(card.text()).toContain('inspect_agent_health_projection')
    expect(card.text()).toContain('prepare_generate_chapter_execution')
  })

  it('emits openTrace for system action messages with trace id', async () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          content: '设定生成完成。',
          trace_id: 'trace-system',
          action_result: { type: 'generate_setup', status: 'success' },
        },
        isLatest: false,
        loading: false,
      },
    })

    await wrapper.get('[data-testid="open-trace"]').trigger('click')

    expect(wrapper.emitted('openTrace')).toEqual([['trace-system']])
  })

  it('renders chapter generation action results with a user-facing label', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '第1章正文生成完成。',
          action_result: { type: 'generate_chapter', status: 'success' },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('生成正文执行成功')
    expect(wrapper.text()).not.toContain('generate_chapter')
  })

  it('renders chapter approval-required action results with a user-facing label', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '第2章正文生成计划已准备完成，等待确认执行。',
          action_result: { type: 'generate_chapter', status: 'approval_required' },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('生成正文等待确认')
    expect(wrapper.text()).not.toContain('approval_required')
  })

  it('prefers backend-projected action result labels when available', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '状态已更新。',
          action_result: { type: 'generate_chapter', status: 'raw_status' },
          action_result_view: {
            type: 'generate_chapter',
            status: 'raw_status',
            label: '后端投影文案',
            variant: 'success',
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('后端投影文案')
    expect(wrapper.text()).not.toContain('raw_status')
  })

  it('renders backend-projected approval decision details without raw hashes', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '操作已确认，正在生成中...',
          action_result: {
            type: 'generate_chapter',
            status: 'generating',
            data: {
              approval_decision: {
                approval_contract_hash: 'approval:secret-hash',
              },
            },
          },
          action_result_view: {
            type: 'generate_chapter',
            status: 'generating',
            label: '正文生成中...',
            variant: 'neutral',
            detail_items: [
              { label: '用户决策', value: '已确认' },
              { label: '审批契约', value: '已绑定' },
            ],
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('用户决策')
    expect(wrapper.text()).toContain('已确认')
    expect(wrapper.text()).toContain('审批契约')
    expect(wrapper.text()).toContain('已绑定')
    expect(wrapper.text()).not.toContain('approval:secret-hash')
  })

  it('emits openAgentRun from recovery preview action results', async () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'plain',
          content: '上一轮 Agent 运行存在可恢复阻塞，我已先规划恢复工具链。',
          action_result: {
            type: 'plan_recovery_tools',
            status: 'success',
            data: { agent_run_id: 'run-1' },
          },
          action_result_view: {
            type: 'plan_recovery_tools',
            status: 'success',
            label: '恢复预览已生成',
            variant: 'success',
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    await wrapper.get('[data-testid="open-agent-run"]').trigger('click')

    expect(wrapper.emitted('openAgentRun')).toEqual([['run-1']])
  })

  it('renders recovery preview fallback labels when backend view is missing', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'plain',
          content: '上一轮 Agent 运行存在可恢复阻塞，我已先规划恢复工具链。',
          action_result: {
            type: 'plan_recovery_tools',
            status: 'success',
            data: {
              agent_run_id: 'run-1',
              source_run_id: 'source-run-123456',
              recovery: { status: 'recommended' },
              execution_policy: { status: 'ready' },
              tools: [{ tool_name: 'prepare_generate_chapter_execution' }],
            },
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('恢复预览已生成')
    expect(wrapper.text()).toContain('执行策略')
    expect(wrapper.text()).toContain('可执行')
    expect(wrapper.text()).not.toContain('plan_recovery_tools')
  })

  it('renders trace audit fallback labels when backend view is missing', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: 'Trace 审计已完成。',
          action_result: {
            type: 'inspect_agent_trace_audit',
            status: 'success',
            data: {
              run: { id: 'run-audit-1', status: 'failed' },
              audit: { step_count: 3, trace_count: 2 },
              failure: { reason_code: 'tool_failed' },
              recommended_actions: [{ tool_name: 'plan_recovery_tools' }],
            },
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('Trace 审计已生成')
    expect(wrapper.text()).toContain('工具步骤')
    expect(wrapper.text()).toContain('3 个')
    expect(wrapper.text()).not.toContain('inspect_agent_trace_audit')
  })

  it('renders longform batch inspection fallback labels when backend view is missing', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '长篇批次队列检查已完成。',
          action_result: {
            type: 'inspect_longform_chapter_batch',
            status: 'success',
            data: {
              status: 'completed',
              summary: { total: 3, returned: 2, selected: true },
              queue: { depth: 2, active: 1, terminal: 1 },
              selected_task: {
                status: 'pending',
                chapter_range: { start: 21, end: 23 },
                execution_readiness: { status: 'materialized_only' },
              },
            },
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('长篇批次检查已生成')
    expect(wrapper.text()).toContain('章节范围')
    expect(wrapper.text()).toContain('第21-23章')
    expect(wrapper.text()).not.toContain('inspect_longform_chapter_batch')
  })

  it('renders longform preflight fallback labels when backend view is missing', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '长篇批次预检已完成。',
          action_result: {
            type: 'execute_longform_chapter_batch_preflight',
            status: 'success',
            data: {
              status: 'ready',
              canonical_execution_plan: { chapters_to_run: [21], stopped_before_node: 'chapter_generation' },
              checkpoint: {
                status: 'ready',
                selected_chapter_indexes: [21],
                ready_chapter_indexes: [21],
                blocked_chapter_indexes: [],
              },
              recommended_next_tools: ['inspect_longform_chapter_batch'],
            },
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('长篇批次预检已就绪')
    expect(wrapper.text()).toContain('预检章节')
    expect(wrapper.text()).toContain('第21章')
    expect(wrapper.text()).not.toContain('execute_longform_chapter_batch_preflight')
  })

  it('renders longform prepare fallback labels when backend view is missing', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '长篇批次执行准备已完成。',
          action_result: {
            type: 'prepare_longform_chapter_batch_execution',
            status: 'success',
            data: {
              status: 'approval_required',
              attempt_manifest: {
                chapter_indexes: [21],
                stopped_before_node: 'chapter_generation',
                execution_steps: [{ tool_name: 'generate_chapter' }],
              },
              approval_contract: {
                consume_tool: 'execute_longform_chapter_batch',
                high_risk_side_effects: ['chapter_generation', 'world_model_intake'],
              },
              agent_plan_approval_contract: { status: 'requires_confirmation', write_step_count: 1 },
              recommended_next_tools: ['execute_longform_chapter_batch'],
            },
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('长篇批次执行准备待确认')
    expect(wrapper.text()).toContain('审批状态')
    expect(wrapper.text()).toContain('等待确认')
    expect(wrapper.text()).not.toContain('prepare_longform_chapter_batch_execution')
  })

  it('renders longform execute fallback labels when backend view is missing', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '长篇批次执行已完成。',
          action_result: {
            type: 'execute_longform_chapter_batch',
            status: 'success',
            data: {
              status: 'completed',
              chapter_index: 21,
              executed_chapter_indexes: [21],
              generation: { status: 'success' },
              evidence: {
                chapter_content_written: true,
                agent_plan_approval_verified: true,
              },
              execution_resource_binding: { status: 'ready' },
              side_effects: { executed: ['generate_chapter', 'background_task_result_execution_checkpoint'] },
              recommended_next_tools: ['review_chapter_quality', 'review_chapter_continuity'],
            },
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('长篇批次执行已完成')
    expect(wrapper.text()).toContain('章节写入')
    expect(wrapper.text()).toContain('已写入')
    expect(wrapper.text()).not.toContain('execute_longform_chapter_batch')
  })

  it('renders longform review fallback labels when backend view is missing', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '长篇批次执行后审查已完成。',
          action_result: {
            type: 'review_longform_chapter_batch_execution',
            status: 'success',
            data: {
              status: 'completed',
              chapter_index: 21,
              review_gate: { status: 'passed', blocker_count: 0, warning_count: 1 },
              reviews: {
                quality: { status: 'ready' },
                continuity: { status: 'ready' },
                world_model: { status: 'completed' },
              },
              recommended_next_tools: ['inspect_longform_chapter_batch', 'prepare_longform_chapter_batch_execution'],
            },
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('长篇批次审查已通过')
    expect(wrapper.text()).toContain('审查闸门')
    expect(wrapper.text()).toContain('已通过')
    expect(wrapper.text()).not.toContain('review_longform_chapter_batch_execution')
  })

  it('renders longform route fallback labels when backend view is missing', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '长篇批次审查后路由已完成。',
          action_result: {
            type: 'route_longform_chapter_batch_after_review',
            status: 'success',
            data: {
              status: 'completed',
              chapter_index: 21,
              route_decision: {
                decision: 'continue_to_next_batch',
                next_chapter_index: 22,
                next_batch_size: 2,
              },
              next_batch_plan: { batch: { chapter_indexes: [22, 23] } },
              recommended_next_tools: ['enqueue_longform_chapter_batch', 'inspect_longform_chapter_batch'],
            },
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('长篇批次已路由到下一批')
    expect(wrapper.text()).toContain('下一批')
    expect(wrapper.text()).toContain('第22-23章')
    expect(wrapper.text()).not.toContain('route_longform_chapter_batch_after_review')
  })

  it('emits openAgentRun from recovery execution action results', async () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '恢复执行已创建，可在运行详情中查看执行步骤。',
          action_result: {
            type: 'ui_recovery_execute',
            status: 'success',
            data: { agent_run_id: 'run-executed' },
          },
          action_result_view: {
            type: 'ui_recovery_execute',
            status: 'success',
            label: '恢复执行已完成',
            variant: 'success',
            detail_items: [
              { label: '运行 ID', value: 'run-executed' },
              { label: '状态', value: '已完成' },
            ],
          },
        },
        isLatest: false,
        loading: false,
      },
    })

    await wrapper.get('[data-testid="open-agent-run"]').trigger('click')

    expect(wrapper.emitted('openAgentRun')).toEqual([['run-executed']])
  })

  it('emits executeRecommendedFollowups from recommended followup preview action results', async () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'plain',
          content: '上一轮 Agent 运行给出了推荐后继，我已先规划后继工具链。',
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
            },
          },
          action_result_view: {
            type: 'plan_recommended_followups',
            status: 'success',
            label: '推荐后继预览已生成',
            variant: 'success',
          },
        },
        isLatest: true,
        loading: false,
      },
    })

    await wrapper.get('[data-testid="execute-recommended-followups"]').trigger('click')

    expect(wrapper.emitted('executeRecommendedFollowups')).toEqual([
      [{ sourceRunId: 'source-run-2', planHash: 'followup-plan-hash-1' }],
    ])
  })

  it('renders pending chapter conflict as a warning before confirmation', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'plain',
          content: '准备生成章节。',
          pending_action: {
            id: 'pending-1',
            type: 'preview_chapter',
            description: '我可以生成第2章正文，完成后会进入 Calliope 和正文进度。 注意：第2章已有待确认或运行中的生成任务，请确认是否仍要继续。',
            params: {
              chapter_index: 2,
              chapter_target_conflict: {
                status: 'reserved',
                chapter_index: 2,
                reason: 'pending_or_running_generation',
              },
            },
          },
        },
        isLatest: true,
        loading: false,
      },
    })

    const warning = wrapper.get('[data-testid="chapter-target-conflict"]')
    expect(warning.text()).toContain('第2章已有待确认或运行中的生成任务')
    expect(warning.text()).toContain('确认前请检查是否要继续覆盖同一章节')
    expect(wrapper.get('.action-card__copy').text()).not.toContain('注意：')
  })

  it('renders pending chapter conflict source labels', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'plain',
          content: '准备生成章节。',
          pending_action: {
            id: 'pending-1',
            type: 'preview_chapter',
            description: '我可以生成第2章正文，完成后会进入 Calliope 和正文进度。 注意：第2章已有批量生成任务，请确认是否仍要继续。',
            params: {
              chapter_index: 2,
              chapter_target_conflict: {
                status: 'reserved',
                chapter_index: 2,
                reason: 'pending_or_running_generation',
                source: 'range_task',
                source_label: '批量生成任务',
              },
            },
          },
        },
        isLatest: true,
        loading: false,
      },
    })

    const warning = wrapper.get('[data-testid="chapter-target-conflict"]')
    expect(warning.text()).toContain('第2章已有批量生成任务')
    expect(wrapper.get('.action-card__copy').text()).not.toContain('注意：')
  })

  it('emits pending action safety actions from the action card', async () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'plain',
          content: '准备生成设定。',
          pending_action: {
            id: 'pending-safety-1',
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
                    pending_action_id: 'pending-safety-1',
                    auto_execute: false,
                    guarded_apply: false,
                  },
                },
              ],
            },
          },
        },
        isLatest: true,
        loading: false,
      },
    })

    await wrapper.get('[data-testid="pending-action-safety-prepare"]').trigger('click')

    expect(wrapper.emitted('safetyAction')).toEqual([
      [
        {
          kind: 'prepare_route_upgrade_contract',
          label: '生成审批契约',
          pending_action_id: 'pending-safety-1',
          auto_execute: false,
          guarded_apply: false,
        },
      ],
    ])
  })

  it('renders generating action progress without repeating the action verb', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '操作已确认，正在生成中...',
          action_result: { type: 'generate_setup', status: 'generating' },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('设定生成中...')
    expect(wrapper.text()).not.toContain('生成设定生成中')
  })
})
