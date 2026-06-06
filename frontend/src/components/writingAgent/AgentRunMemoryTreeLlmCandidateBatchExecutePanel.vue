<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const summary = computed(() => recordValue(props.output.summary))
const rows = computed(() => (
  recordList(props.output.candidate_results)
    .map((result, index) => {
      const materialization = recordValue(result.materialization)
      const materializationSummary = recordValue(materialization.summary)
      const nodes = recordList(materialization.nodes)
      const firstNode = recordValue(nodes[0])
      const quality = recordValue(result.post_materialization_quality)
      const createdNodes = numberValue(materializationSummary.created_nodes)
      const updatedNodes = numberValue(materializationSummary.updated_nodes)
      const chapterLabel = chapterIndexLabel(firstNode.chapter_index)
      const qualityLabel = qualityStatusLabel(quality.status)
      return {
        key: `memory-tree-llm-candidate-batch-execute:${index}`,
        label: chapterLabel || `候选 ${index + 1}`,
        statusLabel: statusLabel(result.status),
        writeLabel: `创建 ${createdNodes ?? 0} / 更新 ${updatedNodes ?? 0}`,
        qualityLabel: qualityLabel ? `质量：${qualityLabel}` : '',
      }
    })
))

const summaryLabel = computed(() => {
  const candidateExecutions = numberValue(summary.value.candidate_executions)
  const succeededCandidates = numberValue(summary.value.succeeded_candidates)
  const blockedCandidates = numberValue(summary.value.blocked_candidates)
  return [
    `成功 ${succeededCandidates ?? 0}`,
    `阻塞 ${blockedCandidates ?? 0}`,
    `候选 ${candidateExecutions ?? rows.value.length}`,
  ].join(' / ')
})

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function statusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'success' || value === 'completed' || value === 'ready') return '已完成'
  if (value === 'failed') return '失败'
  if (value === 'blocked') return '阻塞'
  if (value === 'skipped') return '跳过'
  return value || '未知'
}

function qualityStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '通过'
  if (value === 'degraded') return '降级'
  if (value === 'blocked') return '已阻止'
  return value
}
</script>

<template>
  <section class="agent-run-memory-tree-llm-batch-execute-panel" aria-label="Memory Tree LLM candidate batch execution">
    <h4>Memory Tree 批量候选写入</h4>
    <dl class="agent-run-memory-tree-llm-batch-execute-panel__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(output.status) }}</dd>
      </div>
      <div>
        <dt>候选</dt>
        <dd>{{ summaryLabel }}</dd>
      </div>
    </dl>
    <ol v-if="rows.length" class="agent-run-memory-tree-llm-batch-execute-panel__nodes">
      <li
        v-for="row in rows"
        :key="row.key"
        data-testid="memory-tree-llm-candidate-batch-execute-result"
      >
        <span class="agent-run-memory-tree-llm-batch-execute-panel__level">写入</span>
        <div class="agent-run-memory-tree-llm-batch-execute-panel__content">
          <div class="agent-run-memory-tree-llm-batch-execute-panel__title">
            <strong>{{ row.label }}</strong>
            <span>{{ row.statusLabel }}</span>
            <span>{{ row.writeLabel }}</span>
            <span v-if="row.qualityLabel">{{ row.qualityLabel }}</span>
          </div>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.agent-run-memory-tree-llm-batch-execute-panel {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-memory-tree-llm-batch-execute-panel h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.agent-run-memory-tree-llm-batch-execute-panel__facts {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.agent-run-memory-tree-llm-batch-execute-panel__facts div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: var(--space-3);
}

.agent-run-memory-tree-llm-batch-execute-panel__facts dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-memory-tree-llm-batch-execute-panel__facts dd {
  margin: 0;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-memory-tree-llm-batch-execute-panel__nodes {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-memory-tree-llm-batch-execute-panel__nodes li {
  display: grid;
  grid-template-columns: 3.5rem minmax(0, 1fr);
  gap: var(--space-2);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-primary);
}

.agent-run-memory-tree-llm-batch-execute-panel__level {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-memory-tree-llm-batch-execute-panel__content,
.agent-run-memory-tree-llm-batch-execute-panel__title {
  min-width: 0;
}

.agent-run-memory-tree-llm-batch-execute-panel__title {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}

.agent-run-memory-tree-llm-batch-execute-panel__title strong {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.agent-run-memory-tree-llm-batch-execute-panel__title span {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}
</style>
