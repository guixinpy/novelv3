// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import AgentRunMemoryTreeLlmCandidateBatchPreparePanel from './AgentRunMemoryTreeLlmCandidateBatchPreparePanel.vue'

describe('AgentRunMemoryTreeLlmCandidateBatchPreparePanel', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('renders batch prepare output without internal approval details and emits execute action', async () => {
    const executeAction = {
      key: 'memory-tree-llm-candidate-batch-execute:1',
      label: '确认候选摘要：空白信来源',
      payload: {
        sourceRunId: 'run-memory-tree-batch',
        sourcePlanId: 'memory-tree-batch-plan-2',
        goal: '执行 Memory Tree 候选摘要写入：第2章 空白信来源',
        tools: [],
        planner: {},
      },
    }
    const wrapper = mount(AgentRunMemoryTreeLlmCandidateBatchPreparePanel, {
      attachTo: document.body,
      props: {
        executeActions: [executeAction],
        output: {
          status: 'approval_required',
          prepare_version: 'phase251.memory_tree_llm_candidate_summaries_batch_prepare.v1',
          summary: {
            candidate_traces: 2,
            prepared_candidates: 2,
            skipped_candidates: 0,
          },
          candidate_preparations: [
            {
              summary_plan: {
                candidate_trace_id: 'trace-secret-1',
                chapter_index: 2,
                quality_chapter_index: 2,
                quality_query: '灯塔旧回声',
              },
              agent_plan: {
                trace: { plan_id: 'memory-tree-batch-plan-1' },
              },
              agent_plan_approval_contract: {
                approval: { approval_contract_hash: 'approval-secret-1' },
              },
              agent_plan_approval_contract_hash: 'approval-secret-1',
              recommended_next_tool_call: {
                tool_name: 'execute_record_agent_memory_tree_llm_candidate_summary_with_approval',
                params: {
                  candidate_trace_id: 'trace-secret-1',
                  approval_contract_hash: 'approval-secret-1',
                },
                requires_confirmation: true,
              },
            },
            {
              summary_plan: {
                candidate_trace_id: 'trace-secret-2',
                chapter_index: 2,
                quality_chapter_index: 2,
                quality_query: '空白信来源',
              },
              agent_plan: {
                trace: { plan_id: 'memory-tree-batch-plan-2' },
              },
              agent_plan_approval_contract: {
                approval: { approval_contract_hash: 'approval-secret-2' },
              },
              agent_plan_approval_contract_hash: 'approval-secret-2',
              recommended_next_tool_call: {
                tool_name: 'execute_record_agent_memory_tree_llm_candidate_summary_with_approval',
                params: {
                  candidate_trace_id: 'trace-secret-2',
                  approval_contract_hash: 'approval-secret-2',
                },
                requires_confirmation: true,
              },
            },
          ],
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('Memory Tree 批量候选准备')
    expect(text).toContain('等待确认')
    expect(text).toContain('已准备 2 / 候选 2 / 跳过 0')
    expect(text).toContain('逐条确认')
    expect(text).toContain('第2章 灯塔旧回声')
    expect(text).toContain('质量查询：灯塔旧回声')
    expect(text).toContain('第2章 空白信来源')
    expect(text).toContain('质量查询：空白信来源')
    expect(text).toContain('写入 Memory Tree 候选摘要')
    expect(text).not.toContain('trace-secret-1')
    expect(text).not.toContain('trace-secret-2')
    expect(text).not.toContain('approval-secret-1')
    expect(text).not.toContain('approval-secret-2')
    expect(text).not.toContain('candidate_trace_id')
    expect(text).not.toContain('approval_contract')

    const rows = wrapper.findAll('[data-testid="memory-tree-llm-candidate-batch"]')
    expect(rows).toHaveLength(2)
    const button = wrapper.get('[data-testid="memory-tree-llm-candidate-batch-execute"]')
    await button.trigger('click')

    expect(wrapper.emitted('execute')).toEqual([[executeAction]])
  })
})
