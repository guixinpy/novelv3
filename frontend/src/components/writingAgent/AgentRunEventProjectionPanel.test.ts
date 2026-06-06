// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunEventProjectionPanel from './AgentRunEventProjectionPanel.vue'

describe('AgentRunEventProjectionPanel', () => {
  it('renders agent event projection without source ids or trace internals', () => {
    const wrapper = mount(AgentRunEventProjectionPanel, {
      props: {
        output: {
          status: 'completed',
          version: 'phase234.agent_event_projection.v1',
          project_id: 'project-secret-id',
          selector: {
            task_id: 'task-secret-id',
            run_id: 'linked-run-secret-id',
            limit: 20,
          },
          boundary: {
            decision: 'projection_only',
            persistence: 'not_required',
            reason: 'existing task, run, and step records preserve enough causality',
          },
          summary: {
            total: 6,
            by_event_type: {
              task_started: 1,
              run_started: 1,
              tool_started: 2,
              tool_completed: 1,
              tool_error: 1,
            },
            by_source_type: {
              background_task: 1,
              writing_agent_run: 1,
              writing_agent_step: 4,
            },
          },
          events: [
            {
              event_id: 'background_task:task-secret-id:task_started',
              event_type: 'task_started',
              source_type: 'background_task',
              source_id: 'task-secret-id',
              project_id: 'project-secret-id',
              task_id: 'task-secret-id',
              status: 'running',
            },
            {
              event_id: 'writing_agent_step:step-secret-id:tool_error',
              event_type: 'tool_error',
              source_type: 'writing_agent_step',
              source_id: 'step-secret-id',
              project_id: 'project-secret-id',
              task_id: 'task-secret-id',
              run_id: 'linked-run-secret-id',
              step_id: 'step-secret-id',
              trace_id: 'trace-secret-id',
              tool_name: 'review_chapter_quality',
              status: 'failed',
              chapter_index: 3,
              error_preview: 'quality model timeout',
            },
          ],
          recommended_tools: ['inspect_agent_job_projection'],
          trace: {
            selected_sources: ['background_tasks', 'writing_agent_runs', 'writing_agent_steps'],
            rejected_sources: [{ source: 'event_bus', reason: 'not_required_for_current_projection' }],
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('Agent 事件投影')
    expect(text).toContain('已完成')
    expect(text).toMatch(/事件总数\s*6/)
    expect(text).toMatch(/后台任务事件\s*1/)
    expect(text).toMatch(/运行事件\s*1/)
    expect(text).toMatch(/工具事件\s*4/)
    expect(text).toMatch(/工具错误\s*1/)
    expect(text).toContain('任务开始')
    expect(text).toContain('工具错误')
    expect(text).toContain('后台任务')
    expect(text).toContain('工具步骤')
    expect(text).toContain('review_chapter_quality')
    expect(text).toContain('第3章')
    expect(text).toContain('失败')
    expect(text).toContain('quality model timeout')
    expect(text).toContain('inspect_agent_job_projection')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('task-secret-id')
    expect(text).not.toContain('linked-run-secret-id')
    expect(text).not.toContain('step-secret-id')
    expect(text).not.toContain('trace-secret-id')
    expect(text).not.toContain('phase234.agent_event_projection')
    expect(text).not.toContain('background_tasks')
    expect(text).not.toContain('event_bus')
    expect(text).not.toContain('selector')
  })
})
