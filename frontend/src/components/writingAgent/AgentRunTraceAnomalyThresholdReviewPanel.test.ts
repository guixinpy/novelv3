// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunTraceAnomalyThresholdReviewPanel from './AgentRunTraceAnomalyThresholdReviewPanel.vue'

describe('AgentRunTraceAnomalyThresholdReviewPanel', () => {
  it('renders trace anomaly threshold review without raw policy or config internals', () => {
    const wrapper = mount(AgentRunTraceAnomalyThresholdReviewPanel, {
      props: {
        output: {
          status: 'completed',
          review: {
            status: 'ready_for_manual_review',
            policy_decision: 'keep_current_thresholds',
            sample: {
              recent_run_count: 2,
              baseline_run_count: 2,
              reviewed_run_count: 4,
              minimum_review_run_count: 4,
            },
            signal_count: 1,
            policy: {
              run_id: 'threshold-policy-secret-run',
              trace_id: 'threshold-policy-secret-trace',
            },
          },
          threshold_candidate: {
            affected_run_rate_delta: 0.5,
            critical_issue_rate_delta: 0.25,
          },
          recommended_next_tools: [
            'prepare_record_agent_trace_anomaly_threshold_config',
            'inspect_agent_dogfood_evidence',
          ],
          recommended_next_tool_calls: [
            {
              tool_name: 'prepare_record_agent_trace_anomaly_threshold_config',
              params: {
                affected_run_rate_delta: 0.5,
                critical_issue_rate_delta: 0.25,
                source: 'trace_anomaly_threshold_review',
                reviewed_run_count: 4,
                reason: 'manual_review_from_trace_anomaly_threshold_review',
              },
            },
          ],
          side_effects: {
            executed: [],
            skipped: ['record_agent_trace_anomaly_threshold_config'],
          },
          trace: {
            source: 'inspect_agent_trace_anomaly_threshold_review',
            version: 'phase242.agent_trace_anomaly_threshold_review.v1',
            mutability: 'read',
            config_key: 'Project.style_config.agent_trace_anomaly_thresholds',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('Trace 阈值复核')
    expect(text).toContain('已完成')
    expect(text).toContain('可人工复核')
    expect(text).toContain('保持当前阈值')
    expect(text).toContain('样本 2/2')
    expect(text).toContain('已复核 4/4')
    expect(text).toContain('阈值信号 1')
    expect(text).toContain('异常阈值 50%')
    expect(text).toContain('严重阈值 25%')
    expect(text).toContain('配置准备')
    expect(text).toContain('已跳过直接写入')
    expect(text).toContain('prepare_record_agent_trace_anomaly_threshold_config')
    expect(text).toContain('inspect_agent_dogfood_evidence')
    expect(text).not.toContain('threshold-policy-secret-run')
    expect(text).not.toContain('threshold-policy-secret-trace')
    expect(text).not.toContain('phase242.agent_trace_anomaly_threshold_review')
    expect(text).not.toContain('manual_review_from_trace_anomaly_threshold_review')
    expect(text).not.toContain('Project.style_config.agent_trace_anomaly_thresholds')
    expect(text).not.toContain('recommended_next_tool_calls')
    expect(text).not.toContain('params')
    expect(text).not.toContain('mutability')
  })
})
