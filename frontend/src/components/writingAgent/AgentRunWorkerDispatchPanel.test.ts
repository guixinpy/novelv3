// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunWorkerDispatchPanel from './AgentRunWorkerDispatchPanel.vue'

describe('AgentRunWorkerDispatchPanel', () => {
  it('renders worker dispatch projection without run or task internals', () => {
    const wrapper = mount(AgentRunWorkerDispatchPanel, {
      props: {
        output: {
          version: 'phase230.agent_worker_dispatch.v1',
          status: 'blocked',
          summary: {
            workers: 2,
            planned_tasks: 2,
            blocked_tasks: 1,
            issues: 1,
          },
          definition_registry: {
            version: 'phase229.agent_definition_registry.v1',
            definitions: [{ profile: 'drafting_worker', allowed_tools: ['secret_tool'] }],
          },
          route_registry: {
            status: 'needs_attention',
            summary: {
              routes: 40,
              ready_routes: 39,
              unrouted_allowed_tools: 1,
              issues: 1,
            },
            routes: [{ tool_name: 'secret_route_tool', worker: 'retrieval_worker' }],
          },
          orphan_recovery: {
            version: 'phase236.agent_worker_orphan_recovery.v1',
            status: 'needs_attention',
            summary: {
              active_worker_runs: 3,
              orphan_worker_runs: 1,
              recovery_actions: 2,
            },
            orphan_worker_runs: [
              {
                run_id: 'worker-run-secret-id',
                parent_run_id: 'parent-run-secret-id',
                background_task_id: 'background-task-secret-id',
                reason_code: 'worker_parent_run_missing',
              },
            ],
            recovery_actions: [
              {
                action: 'mark_worker_run_blocked',
                run_id: 'worker-run-secret-id',
                preview_only: true,
              },
            ],
            recommended_tools: ['inspect_agent_trace_audit', 'plan_recovery_tools'],
          },
          worker_dispatches: [
            {
              status: 'ready',
              worker: { name: 'reviewer_worker', role: 'worker', allowed_tools: ['review_chapter_quality'] },
              summary: { planned_tasks: 1, blocked_tasks: 0, issues: 0 },
              task_envelopes: [
                {
                  tool_name: 'review_chapter_quality',
                  parent_run_id: 'parent-run-secret-id',
                  params: { query: 'secret-query' },
                },
              ],
            },
            {
              status: 'blocked',
              worker: { name: 'retrieval_worker', role: 'worker', allowed_tools: ['search_agent_retrieval_context'] },
              summary: { planned_tasks: 1, blocked_tasks: 1, issues: 1 },
              issues: [
                {
                  code: 'child_dispatch_not_allowed',
                  tool_name: 'search_agent_retrieval_context',
                  worker: 'retrieval_worker',
                },
              ],
            },
          ],
          issues: [
            {
              code: 'child_dispatch_not_allowed',
              tool_name: 'search_agent_retrieval_context',
              worker: 'retrieval_worker',
            },
          ],
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('Worker 分派审计')
    expect(text).toContain('已阻塞')
    expect(text).toMatch(/Worker\s*2/)
    expect(text).toMatch(/计划任务\s*2/)
    expect(text).toMatch(/阻塞任务\s*1/)
    expect(text).toMatch(/问题\s*1/)
    expect(text).toContain('路由审计')
    expect(text).toContain('需处理')
    expect(text).toMatch(/未路由工具\s*1/)
    expect(text).toContain('孤儿恢复')
    expect(text).toContain('活跃 worker 3')
    expect(text).toContain('孤儿 worker 1')
    expect(text).toContain('恢复动作 2')
    expect(text).toContain('审稿执行者')
    expect(text).toContain('检索取证者')
    expect(text).toContain('child_dispatch_not_allowed')
    expect(text).toContain('inspect_agent_trace_audit')
    expect(text).toContain('plan_recovery_tools')
    expect(text).not.toContain('worker-run-secret-id')
    expect(text).not.toContain('parent-run-secret-id')
    expect(text).not.toContain('background-task-secret-id')
    expect(text).not.toContain('secret-query')
    expect(text).not.toContain('secret_tool')
    expect(text).not.toContain('secret_route_tool')
    expect(text).not.toContain('phase230.agent_worker_dispatch')
    expect(text).not.toContain('phase236.agent_worker_orphan_recovery')
    expect(text).not.toContain('definition_registry')
    expect(text).not.toContain('task_envelopes')
  })
})
