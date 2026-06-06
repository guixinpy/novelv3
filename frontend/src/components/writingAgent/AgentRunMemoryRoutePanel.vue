<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const route = computed(() => recordValue(props.output.route))
const longformMemory = computed(() => recordValue(props.output.longform_memory))
const maintenance = computed(() => recordValue(props.output.longform_maintenance))
const retrieval = computed(() => recordValue(props.output.retrieval))
const provenance = computed(() => recordValue(props.output.memory_provenance))
const coverage = computed(() => recordValue(provenance.value.coverage))
const diagnostics = computed(() => recordList(props.output.diagnostics))
const recommendedTools = computed(() => (
  stringList(props.output.recommended_next_tools).length
    ? stringList(props.output.recommended_next_tools)
    : stringList(route.value.recommended_tools)
))
const chapterLabel = computed(() => chapterIndexLabel(props.output.chapter_index))
const query = computed(() => safeText(props.output.query))
const contextLabel = computed(() => (
  route.value.can_use_longform_context === true ? '可用于长篇上下文' : '不可用于长篇上下文'
))
const chapterCount = computed(() => (
  numberValue(coverage.value.chapter_count) ??
  numberValue(longformMemory.value.chapter_count)
))
const memoryCount = computed(() => (
  numberValue(coverage.value.longform_memory_count) ??
  numberValue(longformMemory.value.total_memories)
))
const wordCount = computed(() => numberValue(longformMemory.value.current_word_count))
const retrievalDocumentCount = computed(() => (
  numberValue(coverage.value.retrieval_document_count) ??
  numberValue(retrieval.value.total_documents) ??
  numberValue(route.value.retrieval_document_count)
))
const retrievalChunkCount = computed(() => numberValue(retrieval.value.total_chunks))
const maintenanceIssueCount = computed(() => numberValue(maintenance.value.issue_count))
const maintenanceReady = computed(() => (
  typeof maintenance.value.ready_for_writing === 'boolean'
    ? maintenance.value.ready_for_writing
    : null
))
const provenanceStatus = computed(() => stringValue(provenance.value.status))
const diagnosticRows = computed(() => (
  diagnostics.value
    .map((item, index) => ({
      key: `memory-route-diagnostic:${index}`,
      code: safeText(item.code),
      message: safeText(item.message),
    }))
    .filter((item) => Boolean(item.code || item.message))
))

function statusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可用'
  if (value === 'blocked') return '已阻塞'
  if (value === 'completed' || value === 'success') return '已完成'
  return value || '未知'
}

function provenanceStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'available') return '可用'
  if (value === 'degraded') return '降级'
  if (value === 'truncated') return '截断'
  if (value === 'sparse') return '稀疏'
  if (value === 'blocked') return '已阻塞'
  return value || '未知'
}

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function safeText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_.-]+/.test(value)) return ''
  if (/project-secret|source_refs?|source_type|source_id|LongformMemory|RetrievalDocument|Athena\/world_model|phase\d+\.agent_memory_route|longform_memory_retrieval_and_maintenance_diagnostics/i.test(value)) return ''
  return value.slice(0, 96)
}
</script>

<template>
  <section
    class="agent-run-drawer__memory-route"
    aria-label="Agent memory route projection"
  >
    <h4>记忆路由</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(route.status) }}</dd>
      </div>
      <div>
        <dt>上下文</dt>
        <dd>{{ contextLabel }}</dd>
      </div>
      <div v-if="chapterLabel">
        <dt>章节</dt>
        <dd>{{ chapterLabel }}</dd>
      </div>
      <div v-if="query">
        <dt>查询</dt>
        <dd>{{ query }}</dd>
      </div>
      <div v-if="chapterCount !== null">
        <dt>章节覆盖</dt>
        <dd>章节 {{ chapterCount }}</dd>
      </div>
      <div v-if="memoryCount !== null">
        <dt>记忆覆盖</dt>
        <dd>记忆 {{ memoryCount }}</dd>
      </div>
      <div v-if="wordCount !== null">
        <dt>正文规模</dt>
        <dd>字数 {{ wordCount }}</dd>
      </div>
      <div v-if="retrievalDocumentCount !== null">
        <dt>检索文档</dt>
        <dd>检索文档 {{ retrievalDocumentCount }}</dd>
      </div>
      <div v-if="retrievalChunkCount !== null">
        <dt>检索分片</dt>
        <dd>检索分片 {{ retrievalChunkCount }}</dd>
      </div>
      <div v-if="maintenanceReady !== null">
        <dt>维护</dt>
        <dd>{{ maintenanceReady ? '维护可写' : '维护阻塞' }}</dd>
      </div>
      <div v-if="maintenanceIssueCount !== null">
        <dt>维护问题</dt>
        <dd>问题 {{ maintenanceIssueCount }}</dd>
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
        :key="`memory-route-next:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
    <ul
      v-if="diagnosticRows.length"
      class="agent-run-drawer__planner-signals"
    >
      <li
        v-for="row in diagnosticRows"
        :key="row.key"
      >
        <strong v-if="row.code">{{ row.code }}</strong>
        <span v-if="row.message">{{ row.message }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__memory-route {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__memory-route h4 {
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
}
</style>
