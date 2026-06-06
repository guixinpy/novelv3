// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunMemoryTreeLlmCandidateBatchExecutePanel from './AgentRunMemoryTreeLlmCandidateBatchExecutePanel.vue'

describe('AgentRunMemoryTreeLlmCandidateBatchExecutePanel', () => {
  it('renders batch execute output without internal approval details', () => {
    const wrapper = mount(AgentRunMemoryTreeLlmCandidateBatchExecutePanel, {
      props: {
        output: {
          status: 'success',
          execute_version: 'phase252.memory_tree_llm_candidate_summaries_batch_with_approval_execute.v1',
          summary: {
            candidate_executions: 2,
            succeeded_candidates: 2,
            blocked_candidates: 0,
          },
          candidate_results: [
            {
              candidate_index: 1,
              candidate_trace_id: 'trace-secret-1',
              status: 'success',
              materialization: {
                summary: { created_nodes: 1, updated_nodes: 0 },
                nodes: [
                  {
                    id: 'memory-secret-1',
                    chapter_index: 1,
                    title: '雨巷空白信',
                  },
                ],
              },
              agent_plan_approval_verification: {
                approval_contract_hash: 'approval-secret-1',
              },
              execution_resource_binding: {
                target_id: 'trace-secret-1',
              },
              post_materialization_quality: {
                status: 'degraded',
                coverage: { summary_backed_chapter_nodes: 1 },
              },
            },
            {
              candidate_index: 2,
              candidate_trace_id: 'trace-secret-2',
              status: 'success',
              materialization: {
                summary: { created_nodes: 1, updated_nodes: 0 },
                nodes: [
                  {
                    id: 'memory-secret-2',
                    chapter_index: 2,
                    title: '灯塔旧回声',
                  },
                ],
              },
              agent_plan_approval_verification: {
                approval_contract_hash: 'approval-secret-2',
              },
              execution_resource_binding: {
                target_id: 'trace-secret-2',
              },
              post_materialization_quality: {
                status: 'ready',
                coverage: { summary_backed_chapter_nodes: 2 },
              },
            },
          ],
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('Memory Tree 批量候选写入')
    expect(text).toContain('已完成')
    expect(text).toContain('成功 2 / 阻塞 0 / 候选 2')
    expect(text).toContain('第1章')
    expect(text).toContain('创建 1 / 更新 0')
    expect(text).toContain('质量：降级')
    expect(text).toContain('第2章')
    expect(text).toContain('质量：通过')
    expect(text).not.toContain('trace-secret-1')
    expect(text).not.toContain('trace-secret-2')
    expect(text).not.toContain('approval-secret-1')
    expect(text).not.toContain('approval-secret-2')
    expect(text).not.toContain('agent_plan_approval_verification')
    expect(text).not.toContain('execution_resource_binding')
    expect(text).not.toContain('memory-secret')
  })
})
