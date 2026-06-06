<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

type PlannerPlanExecutePayload = {
  sourceRunId: string
  sourcePlanId: string
  goal: string
  tools: Array<Record<string, unknown>>
  planner: Record<string, unknown>
  approvalContractHash?: string
  approvalContract?: Record<string, unknown>
}

type PrepareAction = {
  key: string
  label: string
  payload: PlannerPlanExecutePayload
}

const props = defineProps<{
  output: Record<string, unknown>
  prepareActions: PrepareAction[]
}>()

const emit = defineEmits<{
  prepare: [action: PrepareAction]
}>()

const filters = computed(() => recordValue(props.output.filters))
const summary = computed(() => recordValue(props.output.summary))
const rows = computed(() => (
  recordList(props.output.candidates)
    .map((candidateTrace, index) => {
      const candidate = recordValue(candidateTrace.candidate)
      const summaryTarget = recordValue(candidateTrace.summary_target)
      const chapterIndex = (
        numberValue(candidateTrace.chapter_index) ??
        numberValue(summaryTarget.chapter_index)
      )
      const salientTerms = stringList(candidate.salient_terms)
      const primaryTerm = salientTerms[0] || ''
      const sourceCount = numberValue(candidateTrace.source_count)
      const sourceChars = numberValue(candidateTrace.source_chars)
      const sourceLabel = sourceCount !== null || sourceChars !== null
        ? `来源 ${sourceCount ?? 0} / ${sourceChars ?? 0} 字`
        : ''
      const qualityLabel = qualityStatusLabel(candidateTrace.quality_precheck_status)
      const materialization = recordValue(candidateTrace.materialization)
      const materializationLabel = materializationStatusLabel(materialization.status)
      return {
        key: `memory-tree-llm-candidate:${index}`,
        label: [chapterIndexLabel(chapterIndex), primaryTerm].filter(Boolean).join(' ') || `候选 ${index + 1}`,
        summary: stringValue(candidate.summary),
        termsLabel: salientTerms.slice(0, 3).join(' / '),
        sourceLabel,
        qualityLabel: qualityLabel ? `质量预检：${qualityLabel}` : '',
        materializationLabel,
      }
    })
    .filter((row) => Boolean(row.summary || row.termsLabel))
))
const summaryLabel = computed(() => {
  const traceCount = numberValue(summary.value.candidate_traces)
  const readyCount = numberValue(summary.value.ready_candidates)
  const pendingCount = numberValue(summary.value.pending_candidates)
  const materializedCount = numberValue(summary.value.materialized_candidates)
  const parts = [
    `候选 ${traceCount ?? rows.value.length}`,
    `可准备 ${pendingCount ?? readyCount ?? rows.value.length}`,
  ]
  if (materializedCount !== null) parts.push(`已物化 ${materializedCount}`)
  return parts.join(' / ')
})
const chapterLabel = computed(() => chapterIndexLabel(filters.value.chapter_index))

function statusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可用'
  if (value === 'success' || value === 'completed') return '已完成'
  if (value === 'running') return '生成中'
  if (value === 'failed') return '失败'
  if (value === 'blocked') return '已阻止'
  if (value === 'approval_required') return '等待确认'
  return value || '未知'
}

function qualityStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '通过'
  if (value === 'degraded') return '降级'
  if (value === 'blocked') return '已阻止'
  return value
}

function materializationStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'pending') return '待物化'
  if (value === 'materialized') return '已物化'
  if (value === 'hash_mismatch') return '摘要冲突'
  if (value === 'not_ready') return '未就绪'
  return value
}

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}
</script>

<template>
  <section
    class="agent-run-memory-tree-llm-candidate-panel"
    aria-label="Memory Tree LLM candidates"
  >
    <h4>Memory Tree 候选摘要</h4>
    <dl class="agent-run-memory-tree-llm-candidate-panel__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(output.status) }}</dd>
      </div>
      <div>
        <dt>候选</dt>
        <dd>{{ summaryLabel }}</dd>
      </div>
      <div v-if="chapterLabel">
        <dt>章节</dt>
        <dd>{{ chapterLabel }}</dd>
      </div>
    </dl>
    <ol v-if="rows.length" class="agent-run-memory-tree-llm-candidate-panel__nodes">
      <li
        v-for="row in rows"
        :key="row.key"
        data-testid="memory-tree-llm-candidate"
      >
        <span class="agent-run-memory-tree-llm-candidate-panel__level">候选</span>
        <div class="agent-run-memory-tree-llm-candidate-panel__content">
          <div class="agent-run-memory-tree-llm-candidate-panel__title">
            <strong>{{ row.label }}</strong>
            <span v-if="row.sourceLabel">{{ row.sourceLabel }}</span>
            <span v-if="row.qualityLabel">{{ row.qualityLabel }}</span>
            <span v-if="row.materializationLabel">{{ row.materializationLabel }}</span>
          </div>
          <p v-if="row.summary">{{ row.summary }}</p>
          <p v-if="row.termsLabel">{{ row.termsLabel }}</p>
        </div>
      </li>
    </ol>
    <div
      v-if="prepareActions.length"
      class="agent-run-memory-tree-llm-candidate-panel__actions"
    >
      <button
        v-for="action in prepareActions"
        :key="action.key"
        type="button"
        class="agent-run-memory-tree-llm-candidate-panel__ghost"
        data-testid="memory-tree-llm-candidate-prepare"
        @click="emit('prepare', action)"
      >
        {{ action.label }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.agent-run-memory-tree-llm-candidate-panel {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-memory-tree-llm-candidate-panel h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.agent-run-memory-tree-llm-candidate-panel__facts {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.agent-run-memory-tree-llm-candidate-panel__facts div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: var(--space-3);
}

.agent-run-memory-tree-llm-candidate-panel__facts dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-memory-tree-llm-candidate-panel__facts dd {
  margin: 0;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-memory-tree-llm-candidate-panel__nodes {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-memory-tree-llm-candidate-panel__nodes li {
  display: grid;
  grid-template-columns: 3.5rem minmax(0, 1fr);
  gap: var(--space-2);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-primary);
}

.agent-run-memory-tree-llm-candidate-panel__level {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-memory-tree-llm-candidate-panel__content,
.agent-run-memory-tree-llm-candidate-panel__title {
  min-width: 0;
}

.agent-run-memory-tree-llm-candidate-panel__title {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}

.agent-run-memory-tree-llm-candidate-panel__title strong {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.agent-run-memory-tree-llm-candidate-panel__title span,
.agent-run-memory-tree-llm-candidate-panel__content p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}

.agent-run-memory-tree-llm-candidate-panel__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.agent-run-memory-tree-llm-candidate-panel__ghost {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  cursor: pointer;
}

.agent-run-memory-tree-llm-candidate-panel__ghost:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-primary);
}
</style>
