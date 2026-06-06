<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const riskCounts = computed(() => recordValue(props.output.risk_counts))
const modeCounts = computed(() => recordValue(props.output.review_mode_counts))
const returnedItems = computed(() => numberValue(props.output.returned_items))
const totalItems = computed(() => numberValue(props.output.total_items))
const highRiskCount = computed(() => numberValue(riskCounts.value.high))
const mediumRiskCount = computed(() => numberValue(riskCounts.value.medium))
const lowRiskCount = computed(() => numberValue(riskCounts.value.low))
const individualCount = computed(() => numberValue(modeCounts.value.individual))
const batchCount = computed(() => numberValue(modeCounts.value.batch))
const highPriorityStepCount = computed(() => numberValue(props.output.high_priority_step_count))
const batchStepCount = computed(() => numberValue(props.output.batch_step_count))
const confirmationLabel = computed(() => (
  props.output.requires_human_confirmation === true ? '需要人工确认' : '无需人工确认'
))
const autoApplyLabel = computed(() => (
  props.output.can_auto_apply === true ? '可自动应用' : '不可自动应用'
))
const generationLabel = computed(() => (
  props.output.should_generate_next_chapter === true ? '可继续生成' : '不可继续生成'
))
const recommendedItems = computed(() => [
  ...stringList(props.output.recommended_actions),
  ...stringList(props.output.recommended_next_tools),
])
const stepRows = computed(() => (
  recordList(props.output.resolution_steps)
    .slice(0, 5)
    .map((step, index) => {
      const stepIndex = numberValue(step.step_index)
      const subjects = stringList(step.subject_refs)
        .map((subject) => safeText(subject))
        .filter(Boolean)
      const candidateCount = numberValue(step.candidate_count)
      return {
        key: `world-model-resolution-step:${stepIndex ?? index}`,
        title: [
          stepIndex !== null ? `#${stepIndex}` : '',
          [subjects.join(', '), safeText(step.predicate)].filter(Boolean).join(' · '),
        ].filter(Boolean).join(' ') || '解决步骤',
        meta: [
          actionTypeLabel(step.action_type),
          recommendedResolutionLabel(step.recommended_resolution),
          riskLabel(step.risk_level),
          candidateCount !== null ? `${candidateCount} 个候选` : '',
          chapterRangeLabel(step.chapter_range),
        ].filter(Boolean).join(' · '),
        reason: safeText(step.reason),
      }
    })
    .filter((row) => Boolean(row.title || row.meta || row.reason))
))

function statusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可用'
  if (value === 'blocked') return '已阻塞'
  if (value === 'completed' || value === 'success') return '已完成'
  if (value === 'missing_profile') return '缺少 Profile'
  return value || '未知'
}

function riskLabel(risk: unknown) {
  const value = stringValue(risk)
  if (value === 'high') return '高风险'
  if (value === 'medium') return '中风险'
  if (value === 'low') return '低风险'
  return value
}

function actionTypeLabel(actionType: unknown) {
  const value = stringValue(actionType)
  if (value === 'review_individual') return '逐项审阅'
  if (value === 'review_batch') return '批量审阅'
  return value
}

function recommendedResolutionLabel(resolution: unknown) {
  const value = stringValue(resolution)
  if (value === 'manual_individual_review') return '手动逐项审阅'
  if (value === 'batch_review') return '批量审阅'
  return value
}

function chapterRangeLabel(rangeValue: unknown) {
  const range = recordValue(rangeValue)
  const start = numberValue(range.start)
  const end = numberValue(range.end)
  if (start !== null && end !== null && start !== end) return `第${start}-${end}章`
  if (start !== null) return chapterIndexLabel(start)
  if (end !== null) return chapterIndexLabel(end)
  return ''
}

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function countRangeLabel(returned: number | null, total: number | null) {
  if (returned !== null && total !== null) return `${returned} / ${total}`
  if (returned !== null) return `${returned}`
  if (total !== null) return `${total}`
  return ''
}

function safeText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_.-]+/.test(value)) return ''
  if (/(project|profile|fact|cluster|item|bundle)-secret|source_refs?|source_id|evidence_refs?|approval_contract|approval:|world_profile:|profile_version|item_ids|bundle_ids|allowed_actions|plan_only|report_only/i.test(value)) return ''
  return value.slice(0, 96)
}
</script>

<template>
  <section
    class="agent-run-drawer__world-proposal-resolution"
    aria-label="World model proposal resolution plan projection"
  >
    <h4>世界模型提案解决计划</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(output.status) }}</dd>
      </div>
      <div>
        <dt>确认</dt>
        <dd>{{ confirmationLabel }}</dd>
      </div>
      <div>
        <dt>应用</dt>
        <dd>{{ autoApplyLabel }}</dd>
      </div>
      <div>
        <dt>生成</dt>
        <dd>{{ generationLabel }}</dd>
      </div>
      <div v-if="countRangeLabel(returnedItems, totalItems)">
        <dt>返回</dt>
        <dd>返回 {{ countRangeLabel(returnedItems, totalItems) }}</dd>
      </div>
      <div v-if="highPriorityStepCount !== null">
        <dt>高优先级</dt>
        <dd>高优先级步骤 {{ highPriorityStepCount }}</dd>
      </div>
      <div v-if="batchStepCount !== null">
        <dt>批量步骤</dt>
        <dd>批量步骤 {{ batchStepCount }}</dd>
      </div>
      <div v-if="highRiskCount !== null && highRiskCount > 0">
        <dt>高风险</dt>
        <dd>高风险 {{ highRiskCount }}</dd>
      </div>
      <div v-if="mediumRiskCount !== null && mediumRiskCount > 0">
        <dt>中风险</dt>
        <dd>中风险 {{ mediumRiskCount }}</dd>
      </div>
      <div v-if="lowRiskCount !== null && lowRiskCount > 0">
        <dt>低风险</dt>
        <dd>低风险 {{ lowRiskCount }}</dd>
      </div>
      <div v-if="individualCount !== null && individualCount > 0">
        <dt>逐项</dt>
        <dd>逐项审阅 {{ individualCount }}</dd>
      </div>
      <div v-if="batchCount !== null && batchCount > 0">
        <dt>批量</dt>
        <dd>批量审阅 {{ batchCount }}</dd>
      </div>
    </dl>
    <ul
      v-if="recommendedItems.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="item in recommendedItems"
        :key="`world-proposal-resolution-action:${item}`"
      >
        {{ item }}
      </li>
    </ul>
    <ul
      v-if="stepRows.length"
      class="agent-run-drawer__planner-signals"
    >
      <li
        v-for="row in stepRows"
        :key="row.key"
      >
        <strong>{{ row.title }}</strong>
        <span v-if="row.meta">{{ row.meta }}</span>
        <span v-if="row.reason">{{ row.reason }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__world-proposal-resolution {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__world-proposal-resolution h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.agent-run-drawer__facts {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.agent-run-drawer__facts div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: var(--space-3);
}

.agent-run-drawer__facts dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-drawer__facts dd {
  margin: 0;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__tools,
.agent-run-drawer__planner-signals {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__tools li,
.agent-run-drawer__planner-signals li {
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__planner-signals li {
  display: grid;
  gap: var(--space-1);
}

.agent-run-drawer__planner-signals strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__planner-signals span {
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
}
</style>
