// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AgentRunTraceAnomalyTrendsPanel from './AgentRunTraceAnomalyTrendsPanel.vue'

describe('AgentRunTraceAnomalyTrendsPanel', () => {
  it('renders trace anomaly trends without raw run internals', () => {
    const wrapper = mount(AgentRunTraceAnomalyTrendsPanel, {
      props: {
        output: {
          status: 'completed',
          filters: { limit: 9, chapter_index: 4 },
          trend: {
            status: 'failed',
            run_count: 3,
            affected_run_count: 2,
            issue_count: 6,
            affected_run_rate: 0.67,
            issue_rate: 2,
            severity_counts: { critical: 2, warning: 3, info: 1 },
            issue_counts: {
              failed_model_trace: 1,
              failed_tool_step: 1,
              missing_trace_binding: 1,
              missing_result_message: 1,
              planned_tool_not_executed: 1,
              truncated_context_block: 1,
            },
            dominant_issue_code: 'failed_model_trace',
            project_id: 'project-secret-id',
          },
          baseline: {
            status: 'clear',
            run_count: 2,
            affected_run_count: 0,
            issue_count: 0,
            affected_run_rate: 0,
            issue_rate: 0,
            severity_counts: { critical: 0, warning: 0, info: 0 },
            issue_counts: {},
            dominant_issue_code: '',
            run_id: 'baseline-run-secret-id',
          },
          comparison: {
            affected_run_rate_delta: 0.67,
            issue_rate_delta: 2,
            critical_issue_rate_delta: 0.67,
          },
          thresholds: {
            affected_run_rate_delta: 0.5,
            critical_issue_rate_delta: 0.25,
          },
          threshold_config: {
            status: 'configured',
            source: 'Project.style_config.agent_trace_anomaly_thresholds',
            configured_keys: ['affected_run_rate_delta', 'critical_issue_rate_delta'],
            fallback_keys: [],
          },
          threshold_signals: [
            {
              code: 'affected_run_rate_spike',
              severity: 'warning',
              title: '受影响运行率升高',
              recent_value: 0.67,
              baseline_value: 0,
              delta: 0.67,
              threshold: 0.5,
              trace_id: 'signal-trace-secret-id',
            },
            {
              code: 'critical_issue_rate_spike',
              severity: 'critical',
              title: '严重异常率升高',
              recent_value: 0.67,
              baseline_value: 0,
              delta: 0.67,
              threshold: 0.25,
              step_id: 'signal-step-secret-id',
            },
          ],
          calibration: {
            status: 'needs_tuning',
            sample: {
              recent_run_count: 4,
              baseline_run_count: 4,
              minimum_run_count: 2,
              run_id: 'calibration-sample-secret-id',
            },
            current_signal_count: 2,
            current_thresholds: {
              affected_run_rate_delta: 0.5,
              critical_issue_rate_delta: 0.25,
            },
            suggested_thresholds: {
              affected_run_rate_delta: 0.67,
              critical_issue_rate_delta: 0.25,
            },
            false_negative_guard: {
              status: 'passed',
              reason: 'threshold_signal_present',
              missed_affected_run_count: 0,
              missed_issue_count: 0,
              step_id: 'calibration-fn-secret-step',
            },
            false_positive_guard: {
              status: 'triggered',
              reason: 'threshold_signal_has_only_info_anomalies',
              info_only_signal_count: 1,
              trace_id: 'calibration-fp-secret-trace',
            },
            policy: {
              status: 'review_required',
              decision: 'raise_affected_run_rate_delta_threshold',
              reviewed_run_count: 8,
              minimum_review_run_count: 4,
              promotion_candidate: false,
              recommended_thresholds: {
                affected_run_rate_delta: 0.67,
                critical_issue_rate_delta: 0.25,
              },
              recommended_next_tools: ['inspect_agent_trace_audit', 'inspect_agent_dogfood_evidence'],
              run_id: 'threshold-policy-secret-run',
            },
            recommended_next_tools: ['inspect_agent_trace_audit'],
            project_id: 'calibration-project-secret-id',
          },
          runs: [
            {
              run_index: 1,
              goal: '生成第5章',
              status: 'success',
              entrypoint: 'dialog_auto_plan',
              chapter_index: 5,
              anomaly_status: 'failed',
              issue_count: 5,
              critical_issue_count: 2,
              warning_issue_count: 2,
              info_issue_count: 1,
              top_issue_codes: ['failed_model_trace', 'failed_tool_step'],
              run_id: 'run-trend-secret-id',
              trace_id: 'trace-trend-secret-id',
            },
            {
              run_index: 2,
              goal: '预检第4章',
              status: 'success',
              entrypoint: 'dialog_auto_plan',
              chapter_index: 4,
              anomaly_status: 'needs_attention',
              issue_count: 1,
              critical_issue_count: 0,
              warning_issue_count: 1,
              info_issue_count: 0,
              top_issue_codes: ['missing_trace_binding'],
              step_id: 'step-trend-secret-id',
            },
          ],
          recommended_next_tools: ['inspect_agent_trace_audit', 'plan_recovery_tools'],
          trace: {
            source: 'inspect_agent_trace_anomaly_trends',
            version: 'phase74.agent_trace_anomaly_trends.v1',
            mutability: 'read',
            context_key: 'trend-secret-context-key',
          },
        },
      },
    })

    const text = wrapper.text()
    expect(text).toContain('Trace 异常趋势')
    expect(text).toContain('失败')
    expect(text).toContain('第4章')
    expect(text).toContain('运行 3')
    expect(text).toContain('受影响 2')
    expect(text).toContain('问题 6')
    expect(text).toContain('严重 2')
    expect(text).toContain('警告 3')
    expect(text).toContain('提示 1')
    expect(text).toContain('基线运行 2')
    expect(text).toContain('基线受影响 0')
    expect(text).toContain('异常率 +67%')
    expect(text).toContain('问题率 +200%')
    expect(text).toContain('受影响运行率升高')
    expect(text).toContain('严重异常率升高')
    expect(text).toContain('阈值 50%')
    expect(text).toContain('阈值 25%')
    expect(text).toContain('阈值来源')
    expect(text).toContain('项目配置')
    expect(text).toContain('校准')
    expect(text).toContain('需要调参')
    expect(text).toContain('样本 4/4')
    expect(text).toContain('当前信号 2')
    expect(text).toContain('建议异常阈值 67%')
    expect(text).toContain('建议严重阈值 25%')
    expect(text).toContain('漏报 guard')
    expect(text).toContain('阈值信号已触发')
    expect(text).toContain('误报 guard')
    expect(text).toContain('仅提示级异常触发')
    expect(text).toContain('提示信号 1')
    expect(text).toContain('固化策略')
    expect(text).toContain('需复核')
    expect(text).toContain('提高异常阈值')
    expect(text).toContain('复核样本 8/4')
    expect(text).toContain('不可固化')
    expect(text).toContain('主要问题')
    expect(text).toContain('模型 Trace 失败')
    expect(text).toContain('工具步骤失败')
    expect(text).toContain('缺少 Trace 绑定')
    expect(text).toContain('结果消息缺失')
    expect(text).toContain('计划工具未执行')
    expect(text).toContain('上下文块已截断')
    expect(text).toContain('生成第5章')
    expect(text).toContain('预检第4章')
    expect(text).toContain('inspect_agent_trace_audit')
    expect(text).toContain('plan_recovery_tools')
    expect(text).not.toContain('run-trend-secret-id')
    expect(text).not.toContain('trace-trend-secret-id')
    expect(text).not.toContain('step-trend-secret-id')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('trend-secret-context-key')
    expect(text).not.toContain('baseline-run-secret-id')
    expect(text).not.toContain('signal-trace-secret-id')
    expect(text).not.toContain('signal-step-secret-id')
    expect(text).not.toContain('calibration-project-secret-id')
    expect(text).not.toContain('calibration-sample-secret-id')
    expect(text).not.toContain('calibration-fn-secret-step')
    expect(text).not.toContain('calibration-fp-secret-trace')
    expect(text).not.toContain('threshold-policy-secret-run')
    expect(text).not.toContain('Project.style_config.agent_trace_anomaly_thresholds')
  })
})
