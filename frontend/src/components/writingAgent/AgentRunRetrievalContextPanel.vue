<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const summary = computed(() => recordValue(props.output.summary))
const items = computed(() => recordList(props.output.items))
const filters = computed(() => recordValue(props.output.filters))
const provenance = computed(() => recordValue(props.output.memory_provenance))
const status = computed(() => stringValue(props.output.status))
const query = computed(() => safeText(props.output.query))
const coverageLabel = computed(() => {
  const returned = numberValue(summary.value.returned)
  const total = numberValue(summary.value.total)
  if (returned !== null && total !== null) return `返回 ${returned} / 共 ${total}`
  if (returned !== null) return `返回 ${returned}`
  if (total !== null) return `共 ${total}`
  return ''
})
const limit = computed(() => numberValue(filters.value.limit))
const candidateLimit = computed(() => numberValue(filters.value.candidate_limit))
const maxChapterLabel = computed(() => {
  const chapter = numberValue(filters.value.max_chapter_index)
  return chapter !== null ? `第${chapter}章前` : ''
})
const filterSourceTypeLabel = computed(() => sourceTypeLabel(stringValue(filters.value.source_type)))
const provenanceStatus = computed(() => stringValue(provenance.value.status))
const recommendedTools = computed(() => stringList(props.output.recommended_next_tools))
const rows = computed(() => (
  items.value
    .slice(0, 5)
    .map((item, index) => {
      const score = numberValue(item.score)
      return {
        key: `retrieval-context-item:${index}`,
        title: safeText(item.title) || '检索证据',
        sourceType: sourceTypeLabel(stringValue(item.source_type)),
        chapterLabel: chapterIndexLabel(item.chapter_index),
        scoreLabel: score !== null ? `分数 ${score}` : '',
        snippet: safeText(item.snippet) || safeText(item.content) || safeText(item.summary),
      }
    })
    .filter((item) => Boolean(item.title || item.snippet))
))

function statusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'success' || statusValue === 'completed') return '已完成'
  if (statusValue === 'running') return '进行中'
  if (statusValue === 'failed') return '失败'
  if (statusValue === 'blocked') return '已阻止'
  if (statusValue === 'pending') return '待执行'
  return statusValue || '待执行'
}

function provenanceStatusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'available') return '可用'
  if (statusValue === 'degraded') return '降级'
  if (statusValue === 'truncated') return '截断'
  if (statusValue === 'sparse') return '稀疏'
  if (statusValue === 'blocked') return '已阻塞'
  return statusValue || '未知'
}

function sourceTypeLabel(sourceType: string) {
  if (sourceType === 'knowledge_base_candidate') return '知识库候选'
  if (sourceType === 'longform_memory') return '长篇记忆'
  if (sourceType === 'world_fact') return '世界事实'
  return ''
}

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function safeText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_.:-]+/.test(value)) return ''
  if (/project-secret|candidate-secret|memory-secret|retrieval-secret|source_refs?|source_type|source_id|memory_id|candidate_id|retrieval_internal|retrieval-vector|query_vector_cache_key|memory_provenance|retrieval_items|phase\d+\.agent_retrieval_context/i.test(value)) return ''
  return value.slice(0, 120)
}
</script>

<template>
  <section
    class="agent-run-drawer__retrieval-context"
    aria-label="Agent retrieval context projection"
  >
    <h4>检索证据摘要</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
      </div>
      <div v-if="query">
        <dt>查询</dt>
        <dd>{{ query }}</dd>
      </div>
      <div v-if="coverageLabel">
        <dt>返回</dt>
        <dd>{{ coverageLabel }}</dd>
      </div>
      <div v-if="limit !== null">
        <dt>限制</dt>
        <dd>限制 {{ limit }}</dd>
      </div>
      <div v-if="candidateLimit !== null">
        <dt>候选</dt>
        <dd>候选 {{ candidateLimit }}</dd>
      </div>
      <div v-if="maxChapterLabel">
        <dt>章节窗口</dt>
        <dd>{{ maxChapterLabel }}</dd>
      </div>
      <div v-if="filterSourceTypeLabel">
        <dt>来源类型</dt>
        <dd>{{ filterSourceTypeLabel }}</dd>
      </div>
      <div v-if="provenanceStatus">
        <dt>来源覆盖</dt>
        <dd>{{ provenanceStatusLabel(provenanceStatus) }}</dd>
      </div>
    </dl>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`retrieval-context-next:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
    <ul
      v-if="rows.length"
      class="agent-run-drawer__reference-patterns"
    >
      <li
        v-for="item in rows"
        :key="item.key"
      >
        <div>
          <strong>{{ item.title }}</strong>
          <span v-if="item.sourceType">{{ item.sourceType }}</span>
          <span v-if="item.chapterLabel">{{ item.chapterLabel }}</span>
          <span v-if="item.scoreLabel">{{ item.scoreLabel }}</span>
        </div>
        <p v-if="item.snippet">{{ item.snippet }}</p>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__retrieval-context {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__retrieval-context h4 {
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

.agent-run-drawer__reference-patterns {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__reference-patterns li {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
}

.agent-run-drawer__reference-patterns div {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}

.agent-run-drawer__reference-patterns strong {
  color: var(--color-text-primary);
  font-size: var(--text-xs);
}

.agent-run-drawer__reference-patterns span {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-drawer__reference-patterns p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: 1.5;
  overflow-wrap: anywhere;
}
</style>
