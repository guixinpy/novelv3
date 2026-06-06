<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const status = computed(() => stringValue(props.output.status))
const counts = computed(() => {
  const coverage = recordValue(props.output.coverage)
  const coveredCounts = recordValue(coverage.activated_counts)
  if (Object.keys(coveredCounts).length) return coveredCounts
  return recordValue(props.output.activated_counts)
})
const longformCount = computed(() => numberValue(counts.value.longform))
const knowledgeBaseCount = computed(() => numberValue(counts.value.knowledge_base))
const foreshadowingCount = computed(() => numberValue(counts.value.foreshadowing))
const memoryTreeCount = computed(() => numberValue(counts.value.memory_tree))
const worldModelCount = computed(() => numberValue(counts.value.world_model))
const styleCount = computed(() => numberValue(counts.value.style))
const coverage = computed(() => recordValue(props.output.coverage))
const coverageDebt = computed(() => recordValue(coverage.value.memory_coverage_debt))
const provenance = computed(() => recordValue(props.output.memory_provenance))
const provenanceStatus = computed(() => stringValue(provenance.value.status))
const chapterLabel = computed(() => chapterIndexLabel(props.output.chapter_index))
const query = computed(() => safeText(props.output.query))
const recommendedTools = computed(() => stringList(props.output.recommended_next_tools))
const coverageIssueCount = computed(() => numberValue(coverageDebt.value.issue_count))
const missingMemoryCount = computed(() => numberValue(coverageDebt.value.missing_memory_count))
const staleRetrievalCount = computed(() => numberValue(coverageDebt.value.stale_retrieval_count))
const riskRows = computed(() => (
  recordList(props.output.risks)
    .map((item, index) => ({
      key: `memory-activation-risk:${index}`,
      code: safeText(item.code),
      message: safeText(item.message),
    }))
    .filter((item) => Boolean(item.code || item.message))
))
const activationRows = computed(() => {
  const activation = recordValue(props.output.activation)
  const buckets = [
    { key: 'longform', label: '长篇记忆' },
    { key: 'foreshadowing', label: '伏笔' },
    { key: 'memory_tree', label: 'Memory Tree' },
    { key: 'world_model', label: '世界模型' },
    { key: 'knowledge_base', label: '知识库经验' },
    { key: 'style', label: '风格' },
  ]
  return buckets.flatMap((bucket) => (
    recordList(activation[bucket.key])
      .slice(0, 2)
      .map((item, index) => {
        const title = itemTitle(item, bucket.label)
        const summary = safeText(item.summary)
        return {
          key: `memory-activation:${bucket.key}:${index}`,
          bucket: bucket.label,
          title,
          summary,
        }
      })
      .filter((item) => Boolean(item.title || item.summary))
  ))
})

function statusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'ready') return '已激活'
  if (statusValue === 'degraded') return '降级激活'
  if (statusValue === 'blocked') return '已阻止'
  return statusValue || '未知'
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

function itemTitle(item: Record<string, unknown>, fallback: string) {
  const title = safeText(item.title)
  if (title) return title
  const summary = safeText(item.summary)
  if (summary && (fallback === '世界模型' || fallback === '风格')) return summary
  return safeText(item.predicate) || summary || fallback
}

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function safeText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_.:-]+/.test(value)) return ''
  if (/project-secret|memory-secret|candidate-secret|world-secret|source_refs?|source_type|source_id|memory_id|candidate_id|proposal_item_id|node_id|approval_contract|char\.[A-Za-z0-9_.-]+|style_config\.|phase\d+\.memory_activation|build_memory_activation_plan|future_leak_guard|end_chapter_index_before_target|Writing Agent 长记忆激活|prompt-only raw context/i.test(value)) return ''
  return value.slice(0, 96)
}
</script>

<template>
  <section
    class="agent-run-drawer__memory-activation"
    aria-label="Agent memory activation projection"
  >
    <h4>记忆激活计划</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
      </div>
      <div v-if="chapterLabel">
        <dt>章节</dt>
        <dd>{{ chapterLabel }}</dd>
      </div>
      <div v-if="query">
        <dt>查询</dt>
        <dd>{{ query }}</dd>
      </div>
      <div v-if="longformCount !== null">
        <dt>长篇记忆</dt>
        <dd>长篇记忆 {{ longformCount }}</dd>
      </div>
      <div v-if="foreshadowingCount !== null">
        <dt>伏笔</dt>
        <dd>伏笔 {{ foreshadowingCount }}</dd>
      </div>
      <div v-if="memoryTreeCount !== null">
        <dt>记忆树</dt>
        <dd>Memory Tree {{ memoryTreeCount }}</dd>
      </div>
      <div v-if="worldModelCount !== null">
        <dt>世界模型</dt>
        <dd>世界模型 {{ worldModelCount }}</dd>
      </div>
      <div v-if="knowledgeBaseCount !== null">
        <dt>知识库</dt>
        <dd>知识库经验 {{ knowledgeBaseCount }}</dd>
      </div>
      <div v-if="styleCount !== null">
        <dt>风格</dt>
        <dd>风格 {{ styleCount }}</dd>
      </div>
      <div v-if="provenanceStatus">
        <dt>来源覆盖</dt>
        <dd>{{ provenanceStatusLabel(provenanceStatus) }}</dd>
      </div>
      <div v-if="coverageIssueCount !== null">
        <dt>覆盖问题</dt>
        <dd>覆盖问题 {{ coverageIssueCount }}</dd>
      </div>
      <div v-if="missingMemoryCount !== null">
        <dt>缺失记忆</dt>
        <dd>缺失记忆 {{ missingMemoryCount }}</dd>
      </div>
      <div v-if="staleRetrievalCount !== null">
        <dt>检索陈旧</dt>
        <dd>检索陈旧 {{ staleRetrievalCount }}</dd>
      </div>
    </dl>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`memory-activation-next:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
    <ul
      v-if="activationRows.length"
      class="agent-run-drawer__reference-patterns"
    >
      <li
        v-for="row in activationRows"
        :key="row.key"
      >
        <div>
          <strong>{{ row.bucket }}</strong>
          <span v-if="row.title">{{ row.title }}</span>
        </div>
        <p v-if="row.summary && row.summary !== row.title">{{ row.summary }}</p>
      </li>
    </ul>
    <ul
      v-if="riskRows.length"
      class="agent-run-drawer__planner-signals"
    >
      <li
        v-for="risk in riskRows"
        :key="risk.key"
      >
        <strong v-if="risk.code">{{ risk.code }}</strong>
        <span v-if="risk.message">{{ risk.message }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__memory-activation {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__memory-activation h4 {
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

.agent-run-drawer__reference-patterns,
.agent-run-drawer__planner-signals {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__reference-patterns li,
.agent-run-drawer__planner-signals li {
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

.agent-run-drawer__reference-patterns strong,
.agent-run-drawer__planner-signals strong {
  color: var(--color-text-primary);
  font-size: var(--text-xs);
}

.agent-run-drawer__planner-signals span,
.agent-run-drawer__reference-patterns span {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__reference-patterns p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: 1.5;
  overflow-wrap: anywhere;
}
</style>
