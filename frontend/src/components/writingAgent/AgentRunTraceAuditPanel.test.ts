// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunTraceAuditPanel from './AgentRunTraceAuditPanel.vue'

describe('AgentRunTraceAuditPanel', () => {
  it('renders trace audit projection without raw trace internals', () => {
    const wrapper = mount(AgentRunTraceAuditPanel, {
      props: {
        output: {
          status: 'completed',
          audit: {
            status: 'blocked',
            reason: 'agent_run_blocked',
            step_count: 2,
            trace_count: 1,
            event_chain_count: 5,
            context_block_count: 2,
            control_plane_gap_count: 2,
          },
          run: {
            id: 'audited-run-secret-id',
            goal: '生成第3章',
            status: 'blocked',
            entrypoint: 'dialog_auto_plan',
            background_task_id: 'task-secret-id',
          },
          intent_chain: {
            status: 'available',
            source: 'run_input_planner',
            rule_id: 'preflight_context_budget_intent',
            intent_class: 'preflight_context_budget',
            mapped_from_action_type: 'preflight_context_budget',
            chapter_index: 3,
            planned_tool_count: 1,
            executed_tool_count: 1,
            matched_tool_count: 1,
            planned_tools: [
              {
                tool_name: 'preflight_writing',
                status: 'executed',
                step_index: 1,
                source_plan_id: 'plan-secret-id',
                params: {
                  chapter_index: 3,
                  max_context_chars: 1200,
                },
              },
            ],
          },
          end_to_end_chain: {
            status: 'complete',
            planned_tool_count: 1,
            tool_step_count: 1,
            model_trace_count: 1,
            result_message: {
              status: 'available',
              action_type: 'preflight_writing',
              action_status: 'success',
              message_id: 'message-secret-id',
            },
            segments: [
              {
                stage: 'intent',
                status: 'available',
                intent_class: 'preflight_context_budget',
                chapter_index: 3,
                trace_id: 'trace-secret-id',
              },
              { stage: 'planned_tools', status: 'available', count: 1 },
              { stage: 'executed_tools', status: 'available', count: 1 },
              { stage: 'model_traces', status: 'available', count: 1 },
              {
                stage: 'result_message',
                status: 'available',
                action_type: 'preflight_writing',
                action_status: 'success',
                message_id: 'message-secret-id',
              },
            ],
          },
          anomaly_summary: {
            status: 'failed',
            issue_count: 6,
            severity_counts: { critical: 2, warning: 3, info: 1 },
            failed_step_count: 1,
            failed_trace_count: 1,
            missing_trace_binding_count: 1,
            unmatched_planned_tool_count: 1,
            missing_result_message: true,
            truncated_context_block_count: 1,
            issues: [
              {
                code: 'failed_tool_step',
                severity: 'critical',
                tool_name: 'generate_chapter',
                status: 'failed',
                step_index: 1,
                chapter_index: 4,
                step_id: 'step-secret-id',
              },
              {
                code: 'failed_model_trace',
                severity: 'critical',
                trace_type: 'chapter_generation',
                status: 'failed',
                chapter_index: 4,
                error_recorded: true,
                trace_id: 'trace-secret-id',
              },
              {
                code: 'missing_trace_binding',
                severity: 'warning',
                tool_name: 'preflight_writing',
                status: 'success',
                step_index: 2,
                chapter_index: 4,
                step_id: 'step-missing-trace-secret-id',
              },
              {
                code: 'planned_tool_not_executed',
                severity: 'warning',
                tool_name: 'inspect_agent_memory_route',
                source_plan_id: 'plan-secret-id',
              },
              {
                code: 'missing_result_message',
                severity: 'warning',
                stage: 'result_message',
                message_id: 'message-secret-id',
              },
              {
                code: 'truncated_context_block',
                severity: 'info',
                kind: 'longform_memory',
                title: '长篇记忆',
                char_count: 14,
                source_count: 1,
                trace_id: 'trace-secret-id',
                key: 'secret-context-key',
                content: '这段上下文不应进入异常摘要。',
              },
            ],
          },
          steps: [
            {
              id: 'step-secret-id-1',
              step_index: 1,
              tool_name: 'plan_writing_agent_run',
              status: 'success',
              trace_id: 'trace-secret-id',
            },
            {
              id: 'step-secret-id-2',
              step_index: 2,
              tool_name: 'generate_chapter',
              status: 'blocked',
              trace_id: 'trace-secret-id',
              target_id: 'chapter-content-secret-id',
              chapter_index: 3,
            },
          ],
          traces: [
            {
              id: 'trace-secret-id',
              trace_type: 'chapter_generation',
              status: 'failed',
              model: 'deepseek-chat',
              prompt_tokens: 100,
              completion_tokens: 20,
              latency_ms: 321,
              context_block_count: 2,
              context_char_count: 6000,
              error_message: 'provider timeout',
            },
          ],
          event_chain: [
            {
              event_type: 'dialog_route_decision',
              trace_id: 'route-trace-secret-id',
              selected_route_label: '生成下一章节',
              reason_label: '未发现恢复或后继，回落到章节生成',
            },
            {
              event_type: 'approval_decision',
              message_id: 'message-secret-id',
              action_type: 'generate_chapter',
              decision_label: '已确认',
            },
            {
              event_type: 'run_dispatched',
              run_id: 'audited-run-secret-id',
              status: 'blocked',
              entrypoint: 'dialog_auto_plan',
              background_task_id: 'task-secret-id',
            },
            {
              event_type: 'tool_step',
              step_id: 'step-secret-id-2',
              step_index: 2,
              tool_name: 'generate_chapter',
              status: 'blocked',
              trace_id: 'trace-secret-id',
            },
            {
              event_type: 'trace_attached',
              trace_id: 'trace-secret-id',
              trace_type: 'chapter_generation',
              status: 'failed',
              context_block_count: 2,
            },
          ],
          context: {
            total_blocks: 2,
            blocks: [
              {
                trace_id: 'trace-secret-id',
                key: 'longform-secret-key',
                kind: 'memory',
                title: '长篇记忆',
                char_count: 3200,
                source_count: 3,
                truncated: true,
              },
            ],
          },
          failure: {
            status: 'blocked',
            tool_name: 'generate_chapter',
            step_index: 2,
            reason_code: 'missing_preflight',
            message: '缺少 preflight gate',
          },
          recommended_actions: [
            {
              tool_name: 'plan_recovery_tools',
              reason_code: 'missing_preflight',
              source_step_index: 2,
            },
          ],
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('Trace 审计')
    expect(text).toContain('阻塞')
    expect(text).toContain('生成第3章')
    expect(text).toContain('步骤 2')
    expect(text).toContain('Trace 1')
    expect(text).toContain('事件 5')
    expect(text).toContain('上下文块 2')
    expect(text).toContain('控制面缺口 2')
    expect(text).toContain('generate_chapter')
    expect(text).toContain('missing_preflight')
    expect(text).toContain('缺少 preflight gate')
    expect(text).toContain('plan_recovery_tools')
    expect(text).toContain('生成下一章节')
    expect(text).toContain('已确认')
    expect(text).toContain('长篇记忆')
    expect(text).toContain('3200 字')
    expect(text).toContain('意图链路')
    expect(text).toContain('preflight_context_budget_intent')
    expect(text).toContain('preflight_context_budget')
    expect(text).toContain('第3章')
    expect(text).toContain('计划工具 1')
    expect(text).toContain('已执行 1')
    expect(text).toContain('已匹配 1')
    expect(text).toContain('preflight_writing')
    expect(text).toContain('端到端链路')
    expect(text).toContain('完整')
    expect(text).toContain('执行步骤 1')
    expect(text).toContain('模型 Trace 1')
    expect(text).toContain('结果消息')
    expect(text).toContain('成功')
    expect(text).toContain('异常摘要')
    expect(text).toContain('失败')
    expect(text).toContain('问题 6')
    expect(text).toContain('严重 2')
    expect(text).toContain('警告 3')
    expect(text).toContain('提示 1')
    expect(text).toContain('失败步骤 1')
    expect(text).toContain('失败 Trace 1')
    expect(text).toContain('缺 Trace 1')
    expect(text).toContain('未执行计划 1')
    expect(text).toContain('缺结果消息')
    expect(text).toContain('截断上下文 1')
    expect(text).toContain('工具步骤失败')
    expect(text).toContain('模型 Trace 失败')
    expect(text).toContain('缺少 Trace 绑定')
    expect(text).toContain('计划工具未执行')
    expect(text).toContain('结果消息缺失')
    expect(text).toContain('上下文块已截断')
    expect(text).toContain('chapter_generation')
    expect(text).toContain('inspect_agent_memory_route')
    expect(text).toContain('第4章')
    expect(text).toContain('14 字')
    expect(text).not.toContain('audited-run-secret-id')
    expect(text).not.toContain('step-secret-id')
    expect(text).not.toContain('trace-secret-id')
    expect(text).not.toContain('message-secret-id')
    expect(text).not.toContain('task-secret-id')
    expect(text).not.toContain('chapter-content-secret-id')
    expect(text).not.toContain('longform-secret-key')
    expect(text).not.toContain('plan-secret-id')
    expect(text).not.toContain('secret-context-key')
    expect(text).not.toContain('这段上下文不应进入异常摘要')
    expect(text).not.toContain('max_context_chars')
    expect(text).not.toContain('1200')
    expect(text).not.toContain('run_input_planner')
    expect(text).not.toContain('source_plan_id')
  })
})
