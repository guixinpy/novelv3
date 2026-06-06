<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const prefetchPlan = computed(() => recordValue(props.output.prefetch_plan))
const coverage = computed(() => recordValue(prefetchPlan.value.coverage))
const strategy = computed(() => recordValue(props.output.strategy))
const strategyFilters = computed(() => recordValue(strategy.value.filters))
const inputs = computed(() => recordValue(props.output.inputs))
const status = computed(() => stringValue(prefetchPlan.value.status) || stringValue(props.output.status))
const statusText = computed(() => statusLabel(status.value))
const mode = computed(() => modeLabel(stringValue(prefetchPlan.value.mode)))
const strategyName = computed(() => strategyNameLabel(
  stringValue(coverage.value.strategy_name) || stringValue(strategy.value.name),
))
const query = computed(() => (
  safeText(prefetchPlan.value.query) ||
  safeText(strategyFilters.value.query) ||
  safeText(inputs.value.query)
))
const targetChapterLabel = computed(() => {
  const chapter = numberValue(prefetchPlan.value.target_chapter_index)
  return chapter !== null ? `第${chapter}章` : ''
})
const maxChapterLabel = computed(() => {
  const chapter = numberValue(prefetchPlan.value.max_chapter_index)
  return chapter !== null ? `第${chapter}章前` : ''
})
const readToolCount = computed(() => (
  Array.isArray(prefetchPlan.value.read_tools) ? prefetchPlan.value.read_tools.length : 0
))
const retrievalDocuments = computed(() => numberValue(coverage.value.retrieval_documents))
const recommendedTools = computed(() => stringList(props.output.recommended_next_tools))

function statusLabel(value: string) {
  if (value === 'ready') return '预取就绪'
  if (value === 'blocked') return '已阻止'
  if (value === 'completed' || value === 'success') return '已完成'
  if (value === 'failed') return '失败'
  if (value === 'running') return '进行中'
  return safeText(value) || '未知'
}

function modeLabel(value: string) {
  if (value === 'query_aware_prefetch') return '查询感知预取'
  if (value === 'chapter_window_prefetch') return '章节窗口预取'
  if (value === 'maintenance_blocked') return '维护阻塞'
  if (value === 'diagnostic_prefetch') return '诊断预取'
  return safeText(value)
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
  if (/project-secret|candidate-secret|memory-secret|retrieval-secret|prefetch-secret|strategy-secret|recommended-secret|source_refs?|source_type|source_id|memory_id|candidate_id|recommended_next_tool_calls|tool_calls|approval_contract|phase\d+\.(agent_retrieval_prefetch_plan|agent_retrieval_strategy)/i.test(value)) return ''
  return value.slice(0, 120)
}
</script>

<template>
  <section
    class="agent-run-drawer__retrieval-prefetch"
    aria-label="Agent retrieval prefetch plan projection"
  >
    <h4>检索预取计划</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusText }}</dd>
      </div>
      <div v-if="mode">
        <dt>预取</dt>
        <dd>{{ mode }}</dd>
      </div>
      <div v-if="strategyName">
        <dt>策略</dt>
        <dd>{{ strategyName }}</dd>
      </div>
      <div v-if="query">
        <dt>查询</dt>
        <dd>{{ query }}</dd>
      </div>
      <div v-if="targetChapterLabel">
        <dt>目标章节</dt>
        <dd>{{ targetChapterLabel }}</dd>
      </div>
      <div v-if="maxChapterLabel">
        <dt>章节窗口</dt>
        <dd>{{ maxChapterLabel }}</dd>
      </div>
      <div v-if="readToolCount">
        <dt>只读工具</dt>
        <dd>只读工具 {{ readToolCount }}</dd>
      </div>
      <div v-if="retrievalDocuments !== null">
        <dt>检索</dt>
        <dd>检索文档 {{ retrievalDocuments }}</dd>
      </div>
    </dl>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`retrieval-prefetch-next:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__retrieval-prefetch {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__retrieval-prefetch h4 {
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
