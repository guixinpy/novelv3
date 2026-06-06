<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const review = computed(() => recordValue(props.output.review))
const sample = computed(() => recordValue(review.value.sample))
const thresholdCandidate = computed(() => recordValue(props.output.threshold_candidate))
const sideEffects = computed(() => recordValue(props.output.side_effects))
const status = computed(() => stringValue(props.output.status))
const reviewStateLabel = computed(() => thresholdReviewStatusLabel(review.value.status))
const policyDecisionLabel = computed(() => thresholdReviewDecisionLabel(review.value.policy_decision))
const recentRunCount = computed(() => numberValue(sample.value.recent_run_count))
const baselineRunCount = computed(() => numberValue(sample.value.baseline_run_count))
const reviewedRunCount = computed(() => numberValue(sample.value.reviewed_run_count))
const minimumRunCount = computed(() => numberValue(sample.value.minimum_review_run_count))
const signalCount = computed(() => numberValue(review.value.signal_count))
const affectedThresholdLabel = computed(() => percentLabel(thresholdCandidate.value.affected_run_rate_delta))
const criticalThresholdLabel = computed(() => percentLabel(thresholdCandidate.value.critical_issue_rate_delta))
const skippedDirectWrite = computed(() => (
  stringList(sideEffects.value.skipped).includes('record_agent_trace_anomaly_threshold_config')
))
const recommendedTools = computed(() => stringList(props.output.recommended_next_tools))

function percentLabel(value: unknown) {
  const numericValue = numberValue(value)
  if (numericValue === null) return ''
  return `${Math.round(numericValue * 100)}%`
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

function thresholdReviewStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready_for_manual_review') return '可人工复核'
  if (value === 'collecting_samples') return '收集样本'
  return statusLabel(value)
}

function thresholdReviewDecisionLabel(decision: unknown) {
  const value = stringValue(decision)
  if (value === 'keep_current_thresholds') return '保持当前阈值'
  if (value === 'collect_more_samples') return '继续收集样本'
  if (value === 'raise_affected_run_rate_delta_threshold') return '提高异常阈值'
  if (value === 'lower_affected_run_rate_delta_threshold') return '降低异常阈值'
  return ''
}
</script>

<template>
  <section class="agent-run-trace-anomaly-threshold-review-panel" aria-label="Trace anomaly threshold review projection">
    <h4>Trace 阈值复核</h4>
    <dl class="agent-run-trace-anomaly-threshold-review-panel__facts">
      <div v-if="status">
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
      </div>
      <div v-if="reviewStateLabel">
        <dt>复核状态</dt>
        <dd>{{ reviewStateLabel }}</dd>
      </div>
      <div v-if="policyDecisionLabel">
        <dt>策略决策</dt>
        <dd>{{ policyDecisionLabel }}</dd>
      </div>
      <div v-if="recentRunCount !== null && baselineRunCount !== null">
        <dt>样本</dt>
        <dd>样本 {{ recentRunCount }}/{{ baselineRunCount }}</dd>
      </div>
      <div v-if="reviewedRunCount !== null && minimumRunCount !== null">
        <dt>已复核</dt>
        <dd>已复核 {{ reviewedRunCount }}/{{ minimumRunCount }}</dd>
      </div>
      <div v-if="signalCount !== null">
        <dt>阈值信号</dt>
        <dd>阈值信号 {{ signalCount }}</dd>
      </div>
      <div v-if="affectedThresholdLabel">
        <dt>异常阈值</dt>
        <dd>异常阈值 {{ affectedThresholdLabel }}</dd>
      </div>
      <div v-if="criticalThresholdLabel">
        <dt>严重阈值</dt>
        <dd>严重阈值 {{ criticalThresholdLabel }}</dd>
      </div>
      <div v-if="recommendedTools.includes('prepare_record_agent_trace_anomaly_threshold_config')">
        <dt>配置准备</dt>
        <dd>配置准备</dd>
      </div>
      <div v-if="skippedDirectWrite">
        <dt>直接写入</dt>
        <dd>已跳过直接写入</dd>
      </div>
    </dl>
    <ul v-if="recommendedTools.length" class="agent-run-trace-anomaly-threshold-review-panel__tools">
      <li v-for="toolName in recommendedTools" :key="`trace-threshold-review-next:${toolName}`">
        {{ toolName }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-trace-anomaly-threshold-review-panel {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-trace-anomaly-threshold-review-panel h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.agent-run-trace-anomaly-threshold-review-panel__facts {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.agent-run-trace-anomaly-threshold-review-panel__facts div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: var(--space-3);
}

.agent-run-trace-anomaly-threshold-review-panel__facts dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-trace-anomaly-threshold-review-panel__facts dd {
  margin: 0;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-trace-anomaly-threshold-review-panel__tools {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-trace-anomaly-threshold-review-panel__tools li {
  min-width: 0;
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}
</style>
