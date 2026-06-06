// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunChapterConflictRecoveryPanel from './AgentRunChapterConflictRecoveryPanel.vue'

describe('AgentRunChapterConflictRecoveryPanel', () => {
  it('renders chapter conflict recovery projection without occupying task ids', () => {
    const wrapper = mount(AgentRunChapterConflictRecoveryPanel, {
      props: {
        output: {
          status: 'completed',
          version: 'phase141.chapter_conflict_recovery.v1',
          chapter_index: 3,
          conflict: {
            chapter_index: 3,
            status: 'reserved',
            active_task_count: 1,
            tasks: [
              {
                task_id: 'task-secret-id',
                task_type: 'generate_chapter_range',
                status: 'running',
                source: 'range_task',
                source_label: '批量生成任务',
                chapter_range: { start: 2, end: 4 },
              },
            ],
          },
          recovery: {
            status: 'recommended',
            reason_code: 'chapter_target_reserved',
            next_tool: 'inspect_agent_job_projection',
            next_params: { task_id: 'task-secret-id' },
            should_continue_current_run: false,
            requires_user_input: false,
          },
          tools: [
            { tool_name: 'inspect_agent_job_projection', params: { chapter_index: 3 } },
            { tool_name: 'inspect_agent_job_projection', params: { task_id: 'task-secret-id' } },
          ],
          recovery_options: [
            {
              action: 'inspect_occupying_task',
              tool_name: 'inspect_agent_job_projection',
              params: { task_id: 'task-secret-id' },
              safe_auto_execute: true,
            },
            {
              action: 'wait_for_occupying_task',
              safe_auto_execute: false,
              reason: '目标章节已有 pending/running 生成任务，继续写入前应等待。',
            },
          ],
          trace: {
            selected_tools: ['inspect_agent_job_projection'],
            rejected_tools: [],
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('章节冲突恢复')
    expect(text).toContain('已完成')
    expect(text).toContain('第3章')
    expect(text).toContain('已占用')
    expect(text).toMatch(/占用任务\s*1/)
    expect(text).toContain('建议处理')
    expect(text).toContain('inspect_agent_job_projection')
    expect(text).toMatch(/计划工具\s*2/)
    expect(text).toMatch(/恢复选项\s*2/)
    expect(text).toContain('批量生成任务')
    expect(text).toContain('第2-4章')
    expect(text).toContain('运行中')
    expect(text).toContain('检查占用任务')
    expect(text).toContain('等待占用任务')
    expect(text).not.toContain('task-secret-id')
    expect(text).not.toContain('phase141.chapter_conflict_recovery')
    expect(text).not.toContain('chapter_target_reserved')
    expect(text).not.toContain('next_params')
    expect(text).not.toContain('selected_tools')
    expect(text).not.toContain('rejected_tools')
  })
})
