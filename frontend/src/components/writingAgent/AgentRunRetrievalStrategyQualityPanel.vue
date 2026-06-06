<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const quality = computed(() => recordValue(props.output.quality))
const strategy = computed(() => recordValue(props.output.strategy))
const filters = computed(() => recordValue(strategy.value.filters))
const inputs = computed(() => recordValue(props.output.inputs))
const status = computed(() => stringValue(quality.value.status) || stringValue(props.output.status))
const statusText = computed(() => statusLabel(status.value))
const strategyName = computed(() => strategyNameLabel(
  stringValue(quality.value.strategy_name) || stringValue(strategy.value.name),
))
const query = computed(() => safeText(filters.value.query) || safeText(inputs.value.query))
const maxChapterLabel = computed(() => {
  const chapter = numberValue(filters.value.max_chapter_index)
  return chapter !== null ? `第${chapter}章前` : ''
})
const retrievalDocuments = computed(() => numberValue(quality.value.retrieval_documents))
const dogfoodOpenFindings = computed(() => numberValue(quality.value.dogfood_open_findings))
const dogfoodLabel = computed(() => {
  const evidenceCount = numberValue(quality.value.dogfood_evidence_count)
  const readyEvidenceCount = numberValue(quality.value.dogfood_ready_evidence_count)
  if (evidenceCount !== null && readyEvidenceCount !== null) return `Dogfood ${readyEvidenceCount} / ${evidenceCount}`
  if (evidenceCount !== null) return `Dogfood ${evidenceCount}`
  return ''
})
const recommendedTools = computed(() => stringList(props.output.recommended_next_tools))

function statusLabel(value: string) {
  if (value === 'needs_dogfood_review') return '需要自吃复核'
  if (value === 'needs_retrieval_review') return '需要检索复核'
  if (value === 'ready') return '复核通过'
  if (value === 'blocked') return '已阻止'
  if (value === 'completed' || value === 'success') return '完成'
  if (value === 'failed') return '失败'
  if (value === 'running') return '进行中'
  return safeText(value) || '未知'
}

function strategyNameLabel(name: string) {
  if (name === 'query_aware_retrieval') return '查询感知检索'
  if (name === 'chapter_context_summary') return '章节上下文摘要'
  if (name === 'repair_retrieval_maintenance') return '维护诊断优先'
  if (name === 'memory_route_diagnostics') return '记忆路由诊断'
  return safeText(name)
}

function safeText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_.:-]+/.test(value)) return ''
  if (/project-secret|candidate-secret|memory-secret|retrieval-secret|dogfood-secret|source_refs?|source_type|source_id|memory_id|candidate_id|recommended_next_tool_calls|approval_contract|phase\d+\.(agent_retrieval_strategy|agent_dogfood_evidence)|retrieval-secret-internal/i.test(value)) return ''
  return value.slice(0, 120)
}
</script>

<template>
  <section
    class="agent-run-drawer__retrieval-strategy-quality"
    aria-label="Agent retrieval strategy quality projection"
  >
    <h4>检索策略质量复核</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusText }}</dd>
      </div>
      <div v-if="strategyName">
        <dt>策略</dt>
        <dd>{{ strategyName }}</dd>
      </div>
      <div v-if="query">
        <dt>查询</dt>
        <dd>{{ query }}</dd>
      </div>
      <div v-if="maxChapterLabel">
        <dt>章节窗口</dt>
        <dd>{{ maxChapterLabel }}</dd>
      </div>
      <div v-if="retrievalDocuments !== null">
        <dt>检索</dt>
        <dd>检索文档 {{ retrievalDocuments }}</dd>
      </div>
      <div v-if="dogfoodLabel">
        <dt>Dogfood</dt>
        <dd>{{ dogfoodLabel }}</dd>
      </div>
      <div v-if="dogfoodOpenFindings !== null">
        <dt>开放问题</dt>
        <dd>开放问题 {{ dogfoodOpenFindings }}</dd>
      </div>
    </dl>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`retrieval-strategy-quality-next:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__retrieval-strategy-quality {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__retrieval-strategy-quality h4 {
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

.agent-run-drawer__tools {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__tools li {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}
</style>
