<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const sampleCollection = computed(() => recordValue(props.output.sample_collection))
const reviewWindow = computed(() => recordValue(props.output.review_window))
const status = computed(() => stringValue(props.output.status))
const collectionStatusLabel = computed(() => longRunSampleStatusLabel(sampleCollection.value.status))
const candidateCount = computed(() => numberValue(sampleCollection.value.candidate_run_count))
const minimumReviewCount = computed(() => numberValue(sampleCollection.value.minimum_review_run_count))
const missingCount = computed(() => numberValue(sampleCollection.value.missing_run_count))
const stepCount = computed(() => numberValue(sampleCollection.value.step_count))
const chapterLabels = computed(() => (
  Array.isArray(sampleCollection.value.chapter_indexes)
    ? sampleCollection.value.chapter_indexes
      .map((value) => chapterIndexLabel(value))
      .filter(Boolean)
    : []
))
const reviewLimit = computed(() => numberValue(reviewWindow.value.limit))
const reviewBaselineLimit = computed(() => numberValue(reviewWindow.value.baseline_limit))
const reviewChapterLabel = computed(() => chapterIndexLabel(reviewWindow.value.chapter_index))
const statusRows = computed(() => (
  Object.entries(recordValue(sampleCollection.value.status_counts))
    .map(([status, count]) => ({
      key: `trace-anomaly-long-run-status:${status}`,
      label: runStatusCountLabel(status),
      count: numberValue(count),
    }))
    .filter((row) => Boolean(row.label && row.count !== null))
    .sort((left, right) => left.label.localeCompare(right.label))
))
const recommendedTools = computed(() => stringList(props.output.recommended_next_tools))

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

function longRunSampleStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready_for_threshold_review') return '可复核'
  if (value === 'collecting_samples') return '收集样本'
  return statusLabel(value)
}

function runStatusCountLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'success') return '成功'
  if (value === 'blocked') return '已阻塞'
  if (value === 'failed') return '失败'
  if (value === 'running') return '运行中'
  if (value === 'pending') return '等待中'
  if (value === 'cancelled') return '已取消'
  return value
}
</script>

<template>
  <section class="agent-run-trace-anomaly-long-run-panel" aria-label="Trace anomaly long run samples projection">
    <h4>Trace 长跑样本</h4>
    <dl class="agent-run-trace-anomaly-long-run-panel__facts">
      <div v-if="status">
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
      </div>
      <div v-if="collectionStatusLabel">
        <dt>采样状态</dt>
        <dd>{{ collectionStatusLabel }}</dd>
      </div>
      <div v-if="candidateCount !== null">
        <dt>候选运行</dt>
        <dd>{{ candidateCount }}</dd>
      </div>
      <div v-if="minimumReviewCount !== null">
        <dt>最低样本</dt>
        <dd>{{ minimumReviewCount }}</dd>
      </div>
      <div v-if="missingCount !== null">
        <dt>缺失样本</dt>
        <dd>{{ missingCount }}</dd>
      </div>
      <div v-if="stepCount !== null">
        <dt>工具步骤</dt>
        <dd>{{ stepCount }}</dd>
      </div>
      <div v-if="chapterLabels.length">
        <dt>章节</dt>
        <dd>{{ chapterLabels.join(' / ') }}</dd>
      </div>
      <div v-if="reviewLimit !== null && reviewBaselineLimit !== null">
        <dt>复核窗口</dt>
        <dd>
          {{ ['最近 ' + reviewLimit + ' / 基线 ' + reviewBaselineLimit, reviewChapterLabel].filter(Boolean).join(' · ') }}
        </dd>
      </div>
    </dl>
    <ul v-if="statusRows.length" class="agent-run-trace-anomaly-long-run-panel__status-counts">
      <li v-for="row in statusRows" :key="row.key">
        <span>{{ row.label }} {{ row.count }}</span>
      </li>
    </ul>
    <ul v-if="recommendedTools.length" class="agent-run-trace-anomaly-long-run-panel__tools">
      <li v-for="toolName in recommendedTools" :key="`trace-long-run-next:${toolName}`">
        {{ toolName }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-trace-anomaly-long-run-panel {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-trace-anomaly-long-run-panel h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.agent-run-trace-anomaly-long-run-panel__facts {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.agent-run-trace-anomaly-long-run-panel__facts div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: var(--space-3);
}

.agent-run-trace-anomaly-long-run-panel__facts dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-trace-anomaly-long-run-panel__facts dd {
  margin: 0;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-trace-anomaly-long-run-panel__status-counts,
.agent-run-trace-anomaly-long-run-panel__tools {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-trace-anomaly-long-run-panel__status-counts li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.agent-run-trace-anomaly-long-run-panel__tools {
  grid-template-columns: repeat(auto-fit, minmax(10rem, 1fr));
}

.agent-run-trace-anomaly-long-run-panel__tools li {
  min-width: 0;
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}
</style>
