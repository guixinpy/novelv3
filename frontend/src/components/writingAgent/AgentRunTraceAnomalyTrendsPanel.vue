<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const trend = computed(() => recordValue(props.output.trend))
const baseline = computed(() => recordValue(props.output.baseline))
const comparison = computed(() => recordValue(props.output.comparison))
const filters = computed(() => recordValue(props.output.filters))
const issueCounts = computed(() => recordValue(trend.value.issue_counts))
const severityCounts = computed(() => recordValue(trend.value.severity_counts))
const thresholdSignals = computed(() => recordList(props.output.threshold_signals))
const thresholdConfig = computed(() => recordValue(props.output.threshold_config))
const calibration = computed(() => recordValue(props.output.calibration))
const calibrationSample = computed(() => recordValue(calibration.value.sample))
const suggestedThresholds = computed(() => recordValue(calibration.value.suggested_thresholds))
const falseNegativeGuard = computed(() => recordValue(calibration.value.false_negative_guard))
const falsePositiveGuard = computed(() => recordValue(calibration.value.false_positive_guard))
const policy = computed(() => recordValue(calibration.value.policy))
const recommendedTools = computed(() => stringList(props.output.recommended_next_tools))

const status = computed(() => stringValue(trend.value.status))
const chapterLabel = computed(() => chapterIndexLabel(filters.value.chapter_index))
const runCount = computed(() => numberValue(trend.value.run_count))
const affectedRunCount = computed(() => numberValue(trend.value.affected_run_count))
const issueCount = computed(() => numberValue(trend.value.issue_count))
const criticalCount = computed(() => numberValue(severityCounts.value.critical))
const warningCount = computed(() => numberValue(severityCounts.value.warning))
const infoCount = computed(() => numberValue(severityCounts.value.info))
const dominantIssueLabel = computed(() => anomalyCodeLabel(trend.value.dominant_issue_code))
const baselineRunCount = computed(() => numberValue(baseline.value.run_count))
const baselineAffectedRunCount = computed(() => numberValue(baseline.value.affected_run_count))
const affectedRunRateDeltaLabel = computed(() => signedPercentLabel(comparison.value.affected_run_rate_delta))
const issueRateDeltaLabel = computed(() => signedPercentLabel(comparison.value.issue_rate_delta))
const thresholdConfigLabel = computed(() => thresholdConfigStatusLabel(thresholdConfig.value.status))
const calibrationStatusLabel = computed(() => calibrationStatusLabelFor(calibration.value.status))
const calibrationRecentRunCount = computed(() => numberValue(calibrationSample.value.recent_run_count))
const calibrationBaselineRunCount = computed(() => numberValue(calibrationSample.value.baseline_run_count))
const calibrationCurrentSignalCount = computed(() => numberValue(calibration.value.current_signal_count))
const suggestedAffectedThresholdLabel = computed(() => (
  percentLabel(suggestedThresholds.value.affected_run_rate_delta)
))
const suggestedCriticalThresholdLabel = computed(() => (
  percentLabel(suggestedThresholds.value.critical_issue_rate_delta)
))
const policyStatusLabel = computed(() => policyStatusLabelFor(policy.value.status))
const policyDecisionLabel = computed(() => policyDecisionLabelFor(policy.value.decision))
const policyReviewedRunCount = computed(() => numberValue(policy.value.reviewed_run_count))
const policyMinimumRunCount = computed(() => numberValue(policy.value.minimum_review_run_count))
const policyPromotionLabel = computed(() => promotionLabel(policy.value.promotion_candidate))

const issueRows = computed(() => (
  Object.entries(issueCounts.value)
    .map(([code, count]) => ({
      key: `trace-anomaly-trend-issue:${code}`,
      label: anomalyCodeLabel(code),
      count: numberValue(count),
    }))
    .filter((row) => Boolean(row.label && row.count !== null))
    .sort((left, right) => (right.count ?? 0) - (left.count ?? 0) || left.label.localeCompare(right.label))
))

const runRows = computed(() => (
  recordList(props.output.runs)
    .slice(0, 6)
    .map((run, index) => {
      const runIndex = numberValue(run.run_index)
      const issueCount = numberValue(run.issue_count)
      const criticalCount = numberValue(run.critical_issue_count)
      const warningCount = numberValue(run.warning_issue_count)
      const infoCount = numberValue(run.info_issue_count)
      const topIssues = stringList(run.top_issue_codes)
        .map((code) => anomalyCodeLabel(code))
        .filter(Boolean)
      return {
        key: `trace-anomaly-trend-run:${runIndex ?? index}`,
        title: [runIndex !== null ? `#${runIndex}` : '', safeText(run.goal) || 'Agent run']
          .filter(Boolean)
          .join(' '),
        statusLabel: anomalyStatusLabel(run.anomaly_status),
        meta: [
          chapterIndexLabel(run.chapter_index),
          issueCount !== null ? `问题 ${issueCount}` : '',
          criticalCount !== null ? `严重 ${criticalCount}` : '',
          warningCount !== null ? `警告 ${warningCount}` : '',
          infoCount !== null ? `提示 ${infoCount}` : '',
          safeText(run.entrypoint),
          statusLabel(run.status),
        ].filter(Boolean).join(' · '),
        issueLabel: topIssues.join(' · '),
      }
    })
    .filter((row) => Boolean(row.title || row.statusLabel || row.meta || row.issueLabel))
))

const thresholdSignalRows = computed(() => (
  thresholdSignals.value
    .slice(0, 5)
    .map((signal, index) => {
      const delta = signedPercentLabel(signal.delta)
      const threshold = percentLabel(signal.threshold)
      const recent = percentLabel(signal.recent_value)
      const baseline = percentLabel(signal.baseline_value)
      return {
        key: `trace-anomaly-threshold-signal:${index}`,
        title: safeText(signal.title) || thresholdSignalLabel(signal.code),
        severityLabel: anomalySeverityLabel(signal.severity),
        meta: [
          delta ? `变化 ${delta}` : '',
          threshold ? `阈值 ${threshold}` : '',
          recent ? `当前 ${recent}` : '',
          baseline ? `基线 ${baseline}` : '',
        ].filter(Boolean).join(' · '),
      }
    })
    .filter((row) => Boolean(row.title || row.severityLabel || row.meta))
))

const calibrationGuardRows = computed(() => (
  [
    {
      key: 'trace-anomaly-calibration-fn',
      title: '漏报 guard',
      statusLabel: calibrationGuardStatusLabel(falseNegativeGuard.value.status),
      meta: [
        calibrationGuardReasonLabel(falseNegativeGuard.value.reason),
        numberValue(falseNegativeGuard.value.missed_affected_run_count) !== null
          ? `漏过运行 ${numberValue(falseNegativeGuard.value.missed_affected_run_count)}`
          : '',
        numberValue(falseNegativeGuard.value.missed_issue_count) !== null
          ? `漏过问题 ${numberValue(falseNegativeGuard.value.missed_issue_count)}`
          : '',
      ].filter(Boolean).join(' · '),
    },
    {
      key: 'trace-anomaly-calibration-fp',
      title: '误报 guard',
      statusLabel: calibrationGuardStatusLabel(falsePositiveGuard.value.status),
      meta: [
        calibrationGuardReasonLabel(falsePositiveGuard.value.reason),
        numberValue(falsePositiveGuard.value.info_only_signal_count) !== null
          ? `提示信号 ${numberValue(falsePositiveGuard.value.info_only_signal_count)}`
          : '',
      ].filter(Boolean).join(' · '),
    },
  ].filter((row) => Boolean(row.statusLabel || row.meta))
))

function safeText(label: unknown) {
  const value = stringValue(label)
  return value.length > 120 ? `${value.slice(0, 117)}...` : value
}

function percentLabel(value: unknown) {
  const numericValue = numberValue(value)
  if (numericValue === null) return ''
  return `${Math.round(numericValue * 100)}%`
}

function signedPercentLabel(value: unknown) {
  const numericValue = numberValue(value)
  if (numericValue === null) return ''
  const percent = Math.round(numericValue * 100)
  return `${percent > 0 ? '+' : ''}${percent}%`
}

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function statusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'completed' || value === 'success' || value === 'ready' || value === 'passed') return '已完成'
  if (value === 'blocked') return '阻塞'
  if (value === 'failed') return '失败'
  if (value === 'running') return '运行中'
  if (value === 'executed') return '已执行'
  if (value === 'pending') return '等待中'
  if (value === 'cancelled') return '已取消'
  if (value === 'needs_attention') return '需处理'
  return value || '未知'
}

function anomalyStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'clear') return '正常'
  if (value === 'informational') return '提示'
  if (value === 'needs_attention') return '需处理'
  return statusLabel(value)
}

function anomalySeverityLabel(severity: unknown) {
  const value = stringValue(severity)
  if (value === 'critical') return '严重'
  if (value === 'warning') return '警告'
  if (value === 'info') return '提示'
  return safeText(value)
}

function anomalyCodeLabel(code: unknown) {
  const value = stringValue(code)
  if (value === 'failed_tool_step') return '工具步骤失败'
  if (value === 'failed_model_trace') return '模型 Trace 失败'
  if (value === 'missing_trace_binding') return '缺少 Trace 绑定'
  if (value === 'planned_tool_not_executed') return '计划工具未执行'
  if (value === 'missing_result_message') return '结果消息缺失'
  if (value === 'truncated_context_block') return '上下文块已截断'
  return safeText(value)
}

function thresholdSignalLabel(code: unknown) {
  const value = stringValue(code)
  if (value === 'affected_run_rate_spike') return '受影响运行率升高'
  if (value === 'critical_issue_rate_spike') return '严重异常率升高'
  return safeText(value)
}

function thresholdConfigStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'configured') return '项目配置'
  if (value === 'partial') return '部分配置'
  if (value === 'default') return '内置默认'
  return ''
}

function calibrationStatusLabelFor(status: unknown) {
  const value = stringValue(status)
  if (value === 'needs_tuning') return '需要调参'
  if (value === 'calibrated') return '已校准'
  if (value === 'insufficient_data') return '样本不足'
  return statusLabel(value)
}

function calibrationGuardStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'triggered') return '触发'
  if (value === 'passed') return '通过'
  if (value === 'skipped') return '跳过'
  return statusLabel(value)
}

function calibrationGuardReasonLabel(reason: unknown) {
  const value = stringValue(reason)
  if (value === 'recent_anomalies_below_current_threshold') return '近期异常低于当前阈值'
  if (value === 'threshold_signal_has_only_info_anomalies') return '仅提示级异常触发'
  if (value === 'threshold_signal_present') return '阈值信号已触发'
  if (value === 'no_threshold_signal') return '无阈值信号'
  if (value === 'no_actionable_anomaly') return '无可行动异常'
  if (value === 'actionable_threshold_signal') return '可行动阈值信号'
  if (value === 'insufficient_window_data') return '样本不足'
  return ''
}

function policyStatusLabelFor(status: unknown) {
  const value = stringValue(status)
  if (value === 'review_required') return '需复核'
  if (value === 'eligible_for_promotion') return '可固化'
  if (value === 'collecting_samples') return '收集样本'
  return statusLabel(value)
}

function policyDecisionLabelFor(decision: unknown) {
  const value = stringValue(decision)
  if (value === 'lower_affected_run_rate_delta_threshold') return '降低异常阈值'
  if (value === 'raise_affected_run_rate_delta_threshold') return '提高异常阈值'
  if (value === 'keep_current_thresholds') return '保留当前阈值'
  if (value === 'collect_more_samples') return '继续收集样本'
  return ''
}

function promotionLabel(value: unknown) {
  if (value === true) return '可固化'
  if (value === false) return '不可固化'
  return ''
}
</script>

<template>
  <section class="agent-run-trace-anomaly-trends-panel" aria-label="Trace anomaly trends projection">
    <h4>Trace 异常趋势</h4>
    <dl class="agent-run-trace-anomaly-trends-panel__facts">
      <div v-if="status">
        <dt>状态</dt>
        <dd>{{ anomalyStatusLabel(status) }}</dd>
      </div>
      <div v-if="chapterLabel">
        <dt>章节</dt>
        <dd>{{ chapterLabel }}</dd>
      </div>
      <div v-if="runCount !== null">
        <dt>运行</dt>
        <dd>运行 {{ runCount }}</dd>
      </div>
      <div v-if="affectedRunCount !== null">
        <dt>受影响</dt>
        <dd>受影响 {{ affectedRunCount }}</dd>
      </div>
      <div v-if="issueCount !== null">
        <dt>问题</dt>
        <dd>问题 {{ issueCount }}</dd>
      </div>
      <div v-if="criticalCount !== null">
        <dt>严重</dt>
        <dd>严重 {{ criticalCount }}</dd>
      </div>
      <div v-if="warningCount !== null">
        <dt>警告</dt>
        <dd>警告 {{ warningCount }}</dd>
      </div>
      <div v-if="infoCount !== null">
        <dt>提示</dt>
        <dd>提示 {{ infoCount }}</dd>
      </div>
      <div v-if="dominantIssueLabel">
        <dt>主要问题</dt>
        <dd>主要问题 {{ dominantIssueLabel }}</dd>
      </div>
      <div v-if="baselineRunCount !== null">
        <dt>基线运行</dt>
        <dd>基线运行 {{ baselineRunCount }}</dd>
      </div>
      <div v-if="baselineAffectedRunCount !== null">
        <dt>基线受影响</dt>
        <dd>基线受影响 {{ baselineAffectedRunCount }}</dd>
      </div>
      <div v-if="affectedRunRateDeltaLabel">
        <dt>异常率</dt>
        <dd>异常率 {{ affectedRunRateDeltaLabel }}</dd>
      </div>
      <div v-if="issueRateDeltaLabel">
        <dt>问题率</dt>
        <dd>问题率 {{ issueRateDeltaLabel }}</dd>
      </div>
      <div v-if="thresholdConfigLabel">
        <dt>阈值来源</dt>
        <dd>{{ thresholdConfigLabel }}</dd>
      </div>
    </dl>
    <ul v-if="thresholdSignalRows.length" class="agent-run-trace-anomaly-trends-panel__signals">
      <li v-for="row in thresholdSignalRows" :key="row.key">
        <strong>{{ row.title }}</strong>
        <span>{{ [row.severityLabel, row.meta].filter(Boolean).join(' · ') }}</span>
      </li>
    </ul>
    <dl
      v-if="calibrationStatusLabel || calibrationCurrentSignalCount !== null"
      class="agent-run-trace-anomaly-trends-panel__facts"
    >
      <div v-if="calibrationStatusLabel">
        <dt>校准</dt>
        <dd>{{ calibrationStatusLabel }}</dd>
      </div>
      <div v-if="calibrationRecentRunCount !== null && calibrationBaselineRunCount !== null">
        <dt>样本</dt>
        <dd>样本 {{ calibrationRecentRunCount }}/{{ calibrationBaselineRunCount }}</dd>
      </div>
      <div v-if="calibrationCurrentSignalCount !== null">
        <dt>当前信号</dt>
        <dd>当前信号 {{ calibrationCurrentSignalCount }}</dd>
      </div>
      <div v-if="suggestedAffectedThresholdLabel">
        <dt>建议异常阈值</dt>
        <dd>建议异常阈值 {{ suggestedAffectedThresholdLabel }}</dd>
      </div>
      <div v-if="suggestedCriticalThresholdLabel">
        <dt>建议严重阈值</dt>
        <dd>建议严重阈值 {{ suggestedCriticalThresholdLabel }}</dd>
      </div>
      <div v-if="policyStatusLabel">
        <dt>固化策略</dt>
        <dd>{{ policyStatusLabel }}</dd>
      </div>
      <div v-if="policyDecisionLabel">
        <dt>策略决策</dt>
        <dd>{{ policyDecisionLabel }}</dd>
      </div>
      <div v-if="policyReviewedRunCount !== null && policyMinimumRunCount !== null">
        <dt>复核样本</dt>
        <dd>复核样本 {{ policyReviewedRunCount }}/{{ policyMinimumRunCount }}</dd>
      </div>
      <div v-if="policyPromotionLabel">
        <dt>固化候选</dt>
        <dd>{{ policyPromotionLabel }}</dd>
      </div>
    </dl>
    <ul v-if="calibrationGuardRows.length" class="agent-run-trace-anomaly-trends-panel__signals">
      <li v-for="row in calibrationGuardRows" :key="row.key">
        <strong>{{ row.title }}</strong>
        <span>{{ [row.statusLabel, row.meta].filter(Boolean).join(' · ') }}</span>
      </li>
    </ul>
    <ul v-if="issueRows.length" class="agent-run-trace-anomaly-trends-panel__issue-counts">
      <li v-for="row in issueRows" :key="row.key">
        <span>{{ row.label }}</span>
        <strong>{{ row.count }}</strong>
      </li>
    </ul>
    <ul v-if="runRows.length" class="agent-run-trace-anomaly-trends-panel__signals">
      <li v-for="row in runRows" :key="row.key">
        <strong>{{ row.title }}</strong>
        <span>{{ [row.statusLabel, row.meta].filter(Boolean).join(' · ') }}</span>
        <span v-if="row.issueLabel">{{ row.issueLabel }}</span>
      </li>
    </ul>
    <ul v-if="recommendedTools.length" class="agent-run-trace-anomaly-trends-panel__tools">
      <li v-for="toolName in recommendedTools" :key="toolName">
        {{ toolName }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-trace-anomaly-trends-panel {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-trace-anomaly-trends-panel h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.agent-run-trace-anomaly-trends-panel__facts {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.agent-run-trace-anomaly-trends-panel__facts div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: var(--space-3);
}

.agent-run-trace-anomaly-trends-panel__facts dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-trace-anomaly-trends-panel__facts dd {
  margin: 0;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-trace-anomaly-trends-panel__signals,
.agent-run-trace-anomaly-trends-panel__tools,
.agent-run-trace-anomaly-trends-panel__issue-counts {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-trace-anomaly-trends-panel__signals li {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-primary);
}

.agent-run-trace-anomaly-trends-panel__signals strong {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.agent-run-trace-anomaly-trends-panel__signals span {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-trace-anomaly-trends-panel__issue-counts li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.agent-run-trace-anomaly-trends-panel__issue-counts strong {
  color: var(--color-text-primary);
  font-weight: var(--font-semibold);
}

.agent-run-trace-anomaly-trends-panel__tools {
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
}

.agent-run-trace-anomaly-trends-panel__tools li {
  min-width: 0;
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}
</style>
