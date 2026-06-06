// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunTraceAnomalyLongRunSamplesPanel from './AgentRunTraceAnomalyLongRunSamplesPanel.vue'

describe('AgentRunTraceAnomalyLongRunSamplesPanel', () => {
  it('renders trace anomaly long run samples without raw run or step internals', () => {
    const wrapper = mount(AgentRunTraceAnomalyLongRunSamplesPanel, {
      props: {
        output: {
          status: 'completed',
          filters: {
            limit: 6,
            chapter_index: 4,
            minimum_review_run_count: 4,
          },
          sample_collection: {
            status: 'ready_for_threshold_review',
            candidate_run_count: 4,
            minimum_review_run_count: 4,
            missing_run_count: 0,
            step_count: 7,
            status_counts: {
              blocked: 1,
              failed: 1,
              success: 2,
            },
            entrypoint_counts: {
              dialog_auto_plan: 4,
            },
            chapter_indexes: [4, 5],
            run_id: 'run-long-secret-id',
            step_id: 'step-long-secret-id',
          },
          review_window: {
            limit: 2,
            baseline_limit: 2,
            chapter_index: 4,
          },
          recommended_next_tools: [
            'inspect_agent_trace_anomaly_threshold_review',
            'inspect_agent_dogfood_evidence',
          ],
          recommended_next_tool_calls: [
            {
              tool_name: 'inspect_agent_trace_anomaly_threshold_review',
              params: {
                limit: 2,
                baseline_limit: 2,
                chapter_index: 4,
              },
            },
          ],
          side_effects: { executed: [], skipped: [] },
          trace: {
            source: 'inspect_agent_trace_anomaly_long_run_samples',
            version: 'phase243.agent_trace_anomaly_long_run_samples.v1',
            mutability: 'read',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('Trace 长跑样本')
    expect(text).toContain('已完成')
    expect(text).toContain('可复核')
    expect(text).toMatch(/候选运行\s*4/)
    expect(text).toMatch(/最低样本\s*4/)
    expect(text).toMatch(/缺失样本\s*0/)
    expect(text).toMatch(/工具步骤\s*7/)
    expect(text).toContain('第4章')
    expect(text).toContain('第5章')
    expect(text).toContain('成功 2')
    expect(text).toContain('已阻塞 1')
    expect(text).toContain('失败 1')
    expect(text).toContain('复核窗口')
    expect(text).toContain('最近 2 / 基线 2')
    expect(text).toContain('inspect_agent_trace_anomaly_threshold_review')
    expect(text).toContain('inspect_agent_dogfood_evidence')
    expect(text).not.toContain('run-long-secret-id')
    expect(text).not.toContain('step-long-secret-id')
    expect(text).not.toContain('phase243.agent_trace_anomaly_long_run_samples')
    expect(text).not.toContain('dialog_auto_plan')
    expect(text).not.toContain('recommended_next_tool_calls')
    expect(text).not.toContain('params')
    expect(text).not.toContain('mutability')
  })
})
