// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunJobProjectionPanel from './AgentRunJobProjectionPanel.vue'

describe('AgentRunJobProjectionPanel', () => {
  it('renders agent job projection without task or run internals', () => {
    const wrapper = mount(AgentRunJobProjectionPanel, {
      props: {
        output: {
          status: 'completed',
          project_id: 'project-secret-id',
          selector: {
            task_id: 'task-secret-id',
            chapter_index: '3',
          },
          summary: {
            total: 4,
            returned: 2,
            limit: 20,
            by_status: {
              running: 1,
              failed: 1,
            },
          },
          queue: {
            depth: 2,
            active: 1,
            terminal: 1,
            by_status: {
              running: 1,
              failed: 1,
            },
          },
          selected_task: {
            id: 'task-secret-id',
            task_type: 'generate_chapter',
            status: 'failed',
            chapter_index: 3,
            chapter_range: { start: 3, end: 5 },
            control_plane: {
              source: 'writing_start',
              version: 'phase71.control_plane.v1',
              tool_name: 'generate_chapter',
            },
            progress: {
              next_chapter_index: 4,
              completed_count: 1,
              total_count: 3,
              can_resume: true,
            },
            resume: {
              can_resume: true,
              next_chapter_index: 4,
              pending_chapter_indexes: [4, 5],
              completed_count: 1,
            },
            recovery: {
              can_retry: true,
              recommended_tools: ['inspect_agent_trace_audit', 'plan_recovery_tools'],
              reason: 'DeepSeek timeout secret detail',
            },
            event_projection: {
              status: 'completed',
              version: 'phase234.agent_event_projection.v1',
              summary: {
                total: 6,
                by_event_type: { tool_error: 1 },
                by_source_type: { writing_agent_step: 2 },
              },
              latest_events: [
                {
                  event_id: 'secret-event-id',
                  run_id: 'run-secret-id',
                  task_id: 'task-secret-id',
                  trace_id: 'trace-secret-id',
                  event_type: 'tool_error',
                },
              ],
            },
            agent_runs: [
              {
                id: 'run-secret-id',
                goal: 'secret goal',
                status: 'failed',
                entrypoint: 'writing_start',
              },
            ],
            control_plane_readiness: {
              status: 'degraded',
              summary: {
                total_gap_count: 2,
                tool_gap_count: 1,
                command_gap_count: 1,
              },
            },
            command_contracts: {
              status: 'completed',
              summary: {
                agent_control_commands: 2,
                gap_count: 1,
              },
              commands: [{ name: 'legacy_generate_secret' }],
            },
            error_preview: 'DeepSeek timeout',
          },
          chapter_reservation: {
            chapter_index: 3,
            status: 'reserved',
            active_task_count: 1,
            tasks: [
              {
                task_id: 'reservation-task-secret-id',
                task_type: 'generate_chapter_range',
                status: 'running',
                source: 'range_task',
                source_label: '批量生成任务',
                chapter_range: { start: 2, end: 4 },
              },
            ],
            recommended_tools: ['inspect_agent_job_projection', 'inspect_agent_trace_audit'],
            recovery_options: [
              {
                action: 'inspect_occupying_task',
                tool_name: 'inspect_agent_job_projection',
                params: { task_id: 'reservation-task-secret-id' },
              },
            ],
          },
          recommended_tools: ['inspect_agent_trace_audit', 'plan_recovery_tools'],
          trace: {
            source: 'inspect_agent_job_projection',
            version: 'phase75.agent_job_projection.v1',
            mutability: 'read',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('任务队列投影')
    expect(text).toContain('已完成')
    expect(text).toMatch(/队列深度\s*2/)
    expect(text).toMatch(/活跃任务\s*1/)
    expect(text).toMatch(/终止任务\s*1/)
    expect(text).toMatch(/返回任务\s*2 \/ 4/)
    expect(text).toContain('任务状态')
    expect(text).toContain('失败')
    expect(text).toContain('第3章')
    expect(text).toContain('第3-5章')
    expect(text).toMatch(/下一章\s*第4章/)
    expect(text).toMatch(/已完成章节\s*1/)
    expect(text).toContain('可恢复')
    expect(text).toContain('DeepSeek timeout')
    expect(text).toContain('控制平面')
    expect(text).toContain('需检查')
    expect(text).toMatch(/控制面缺口\s*2/)
    expect(text).toContain('命令契约')
    expect(text).toMatch(/控制命令\s*2/)
    expect(text).toMatch(/契约缺口\s*1/)
    expect(text).toContain('章节占用')
    expect(text).toContain('已占用')
    expect(text).toMatch(/占用任务\s*1/)
    expect(text).toContain('批量生成任务')
    expect(text).toContain('第2-4章')
    expect(text).toContain('事件投影')
    expect(text).toMatch(/事件\s*6/)
    expect(text).toMatch(/工具错误\s*1/)
    expect(text).toContain('inspect_agent_trace_audit')
    expect(text).toContain('plan_recovery_tools')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('task-secret-id')
    expect(text).not.toContain('reservation-task-secret-id')
    expect(text).not.toContain('run-secret-id')
    expect(text).not.toContain('trace-secret-id')
    expect(text).not.toContain('secret-event-id')
    expect(text).not.toContain('phase75.agent_job_projection')
    expect(text).not.toContain('phase234.agent_event_projection')
    expect(text).not.toContain('phase71.control_plane')
    expect(text).not.toContain('writing_start')
    expect(text).not.toContain('legacy_generate_secret')
    expect(text).not.toContain('DeepSeek timeout secret detail')
    expect(text).not.toContain('selector')
    expect(text).not.toContain('control_plane')
    expect(text).not.toContain('params')
    expect(text).not.toContain('mutability')
  })
})
