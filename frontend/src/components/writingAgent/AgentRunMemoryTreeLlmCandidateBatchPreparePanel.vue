<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringValue } from './agentRunProjection/safeProjection'

type PlannerPlanExecutePayload = {
  sourceRunId: string
  sourcePlanId: string
  goal: string
  tools: Array<Record<string, unknown>>
  planner: Record<string, unknown>
  approvalContractHash?: string
  approvalContract?: Record<string, unknown>
}

type BatchExecuteAction = {
  key: string
  label: string
  payload: PlannerPlanExecutePayload
}

const props = defineProps<{
  output: Record<string, unknown>
  executeActions: BatchExecuteAction[]
}>()

const emit = defineEmits<{
  execute: [action: BatchExecuteAction]
}>()

const summary = computed(() => recordValue(props.output.summary))
const preparations = computed(() => recordList(props.output.candidate_preparations))
const rows = computed(() => (
  preparations.value
    .map((preparation, index) => {
      const summaryPlan = recordValue(preparation.summary_plan)
      const chapterLabel = chapterIndexLabel(summaryPlan.chapter_index)
      const qualityQuery = stringValue(summaryPlan.quality_query)
      const executeCall = recordValue(preparation.recommended_next_tool_call)
      const executeToolLabel = executeToolLabelFor(stringValue(executeCall.tool_name))
      return {
        key: `memory-tree-llm-candidate-batch:${index}`,
        label: [chapterLabel, qualityQuery].filter(Boolean).join(' ') || `候选 ${index + 1}`,
        qualityQuery,
        executeToolLabel,
      }
    })
    .filter((row) => Boolean(row.label || row.executeToolLabel))
))
const summaryLabel = computed(() => {
  const candidateTraces = numberValue(summary.value.candidate_traces)
  const preparedCandidates = numberValue(summary.value.prepared_candidates)
  const skippedCandidates = numberValue(summary.value.skipped_candidates)
  return [
    `已准备 ${preparedCandidates ?? rows.value.length}`,
    `候选 ${candidateTraces ?? rows.value.length}`,
    `跳过 ${skippedCandidates ?? 0}`,
  ].join(' / ')
})

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

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function executeToolLabelFor(toolName: string) {
  if (toolName === 'execute_record_agent_memory_tree_llm_candidate_summary_with_approval') {
    return '写入 Memory Tree 候选摘要'
  }
  return toolName || '写入工具'
}
</script>

<template>
  <section
    class="agent-run-memory-tree-llm-batch-prepare-panel"
    aria-label="Memory Tree LLM candidate batch approval"
  >
    <h4>Memory Tree 批量候选准备</h4>
    <dl class="agent-run-memory-tree-llm-batch-prepare-panel__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(output.status) }}</dd>
      </div>
      <div>
        <dt>候选</dt>
        <dd>{{ summaryLabel }}</dd>
      </div>
      <div>
        <dt>确认要求</dt>
        <dd>逐条确认</dd>
      </div>
    </dl>
    <ol v-if="rows.length" class="agent-run-memory-tree-llm-batch-prepare-panel__nodes">
      <li
        v-for="row in rows"
        :key="row.key"
        data-testid="memory-tree-llm-candidate-batch"
      >
        <span class="agent-run-memory-tree-llm-batch-prepare-panel__level">准备</span>
        <div class="agent-run-memory-tree-llm-batch-prepare-panel__content">
          <div class="agent-run-memory-tree-llm-batch-prepare-panel__title">
            <strong>{{ row.label }}</strong>
            <span v-if="row.executeToolLabel">{{ row.executeToolLabel }}</span>
          </div>
          <p v-if="row.qualityQuery">质量查询：{{ row.qualityQuery }}</p>
        </div>
      </li>
    </ol>
    <div
      v-if="executeActions.length"
      class="agent-run-memory-tree-llm-batch-prepare-panel__actions"
    >
      <button
        v-for="action in executeActions"
        :key="action.key"
        type="button"
        class="agent-run-memory-tree-llm-batch-prepare-panel__execute"
        data-testid="memory-tree-llm-candidate-batch-execute"
        @click="emit('execute', action)"
      >
        {{ action.label }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.agent-run-memory-tree-llm-batch-prepare-panel {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-memory-tree-llm-batch-prepare-panel h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.agent-run-memory-tree-llm-batch-prepare-panel__facts {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.agent-run-memory-tree-llm-batch-prepare-panel__facts div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: var(--space-3);
}

.agent-run-memory-tree-llm-batch-prepare-panel__facts dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-memory-tree-llm-batch-prepare-panel__facts dd {
  margin: 0;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-memory-tree-llm-batch-prepare-panel__nodes {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-memory-tree-llm-batch-prepare-panel__nodes li {
  display: grid;
  grid-template-columns: 3.5rem minmax(0, 1fr);
  gap: var(--space-2);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-primary);
}

.agent-run-memory-tree-llm-batch-prepare-panel__level {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-memory-tree-llm-batch-prepare-panel__content,
.agent-run-memory-tree-llm-batch-prepare-panel__title {
  min-width: 0;
}

.agent-run-memory-tree-llm-batch-prepare-panel__title {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}

.agent-run-memory-tree-llm-batch-prepare-panel__title strong {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.agent-run-memory-tree-llm-batch-prepare-panel__title span,
.agent-run-memory-tree-llm-batch-prepare-panel__content p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}

.agent-run-memory-tree-llm-batch-prepare-panel__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.agent-run-memory-tree-llm-batch-prepare-panel__execute {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: var(--color-text-inverse);
  font-size: var(--text-xs);
  cursor: pointer;
}

.agent-run-memory-tree-llm-batch-prepare-panel__execute:hover:not(:disabled) {
  background: var(--color-primary-hover);
}
</style>
