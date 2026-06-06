<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const strategy = computed(() => recordValue(props.output.strategy))
const filters = computed(() => recordValue(strategy.value.filters))
const inputs = computed(() => recordValue(props.output.inputs))
const status = computed(() => stringValue(props.output.status))
const strategyName = computed(() => strategyNameLabel(stringValue(strategy.value.name)))
const query = computed(() => safeText(filters.value.query) || safeText(inputs.value.query))
const limit = computed(() => numberValue(filters.value.limit) ?? numberValue(inputs.value.limit))
const candidateLimit = computed(() => (
  numberValue(filters.value.candidate_limit) ?? numberValue(inputs.value.candidate_limit)
))
const maxChapterLabel = computed(() => {
  const chapter = numberValue(filters.value.max_chapter_index)
  return chapter !== null ? `第${chapter}章前` : ''
})
const recommendedTools = computed(() => stringList(props.output.recommended_next_tools))

function statusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'success' || statusValue === 'completed') return '已完成'
  if (statusValue === 'running') return '进行中'
  if (statusValue === 'failed') return '失败'
  if (statusValue === 'blocked') return '已阻止'
  if (statusValue === 'pending') return '待执行'
  return statusValue || '待执行'
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
  if (/project-secret|candidate-secret|memory-secret|retrieval-secret|source_refs?|source_type|source_id|memory_id|candidate_id|recommended_next_tool_calls|approval_contract|phase\d+\.agent_retrieval_strategy/i.test(value)) return ''
  return value.slice(0, 120)
}
</script>

<template>
  <section
    class="agent-run-drawer__retrieval-strategy"
    aria-label="Agent retrieval strategy projection"
  >
    <h4>检索策略摘要</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
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
      <div v-if="limit !== null">
        <dt>限制</dt>
        <dd>限制 {{ limit }}</dd>
      </div>
      <div v-if="candidateLimit !== null">
        <dt>候选</dt>
        <dd>候选 {{ candidateLimit }}</dd>
      </div>
    </dl>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`retrieval-strategy-next:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__retrieval-strategy {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__retrieval-strategy h4 {
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
