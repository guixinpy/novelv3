<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const route = computed(() => recordValue(props.output.route))
const authorPreferences = computed(() => recordValue(props.output.author_preferences))
const learnedRules = computed(() => recordValue(props.output.learned_rules))
const knowledgeCandidates = computed(() => recordValue(props.output.knowledge_candidates))
const referencePatterns = computed(() => recordValue(props.output.reference_patterns))
const diagnostics = computed(() => recordList(props.output.diagnostics))
const recommendedTools = computed(() => (
  stringList(props.output.recommended_next_tools).length
    ? stringList(props.output.recommended_next_tools)
    : stringList(route.value.recommended_tools)
))
const chapterLabel = computed(() => chapterIndexLabel(props.output.chapter_index))
const query = computed(() => safeText(props.output.query))
const authorFacetCount = computed(() => recordList(authorPreferences.value.facets).length)
const learnedRuleReturned = computed(() => numberValue(learnedRules.value.returned))
const learnedRuleTotal = computed(() => numberValue(learnedRules.value.total))
const candidateReturned = computed(() => numberValue(knowledgeCandidates.value.returned))
const candidateTotal = computed(() => numberValue(knowledgeCandidates.value.total))
const referencePatternReturned = computed(() => numberValue(referencePatterns.value.returned))
const generationLabel = computed(() => (
  route.value.can_inform_generation === true ? '可用于生成' : '仅供诊断'
))
const candidateRows = computed(() => (
  recordList(knowledgeCandidates.value.items)
    .map((item, index) => ({
      key: `knowledge-route-candidate:${index}`,
      title: safeText(item.title) || '知识库候选',
      type: candidateTypeLabel(item.memory_type),
      summary: safeText(item.summary),
    }))
    .filter((item) => Boolean(item.title || item.summary))
))
const learnedRuleRows = computed(() => (
  recordList(learnedRules.value.items)
    .map((item, index) => ({
      key: `knowledge-route-rule:${index}`,
      condition: safeText(item.condition),
      action: safeText(item.action),
    }))
    .filter((item) => Boolean(item.condition || item.action))
))
const diagnosticRows = computed(() => (
  diagnostics.value
    .map((item, index) => ({
      key: `knowledge-route-diagnostic:${index}`,
      message: safeText(item.message),
    }))
    .filter((item) => Boolean(item.message))
))

function statusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可用'
  if (value === 'sparse') return '稀疏'
  if (value === 'completed') return '已完成'
  return value || '未知'
}

function candidateTypeLabel(memoryType: unknown) {
  const value = stringValue(memoryType)
  if (value === 'writing_pattern') return '写法模式'
  if (value === 'self_optimization_lesson') return '自优化经验'
  if (value === 'author_preference') return '作者偏好'
  if (value === 'project_policy') return '项目策略'
  if (value === 'learned_rule') return '学习规则'
  return value || '知识库候选'
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
  if (/[A-Za-z_]+:[A-Za-z0-9_-]+/.test(value)) return ''
  if (/source_refs?|source_id|approval_contract|approval:|chapter-content-\d+|PromptRule:|Project\.style_config|FewShotExampleLibrary/i.test(value)) return ''
  return value.slice(0, 96)
}
</script>

<template>
  <section
    class="agent-run-drawer__knowledge-route"
    aria-label="Knowledge base route projection"
  >
    <h4>知识库路由</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(route.status) }}</dd>
      </div>
      <div>
        <dt>生成</dt>
        <dd>{{ generationLabel }}</dd>
      </div>
      <div v-if="chapterLabel">
        <dt>章节</dt>
        <dd>{{ chapterLabel }}</dd>
      </div>
      <div v-if="query">
        <dt>查询</dt>
        <dd>{{ query }}</dd>
      </div>
      <div>
        <dt>作者偏好</dt>
        <dd>作者偏好 {{ authorFacetCount }}</dd>
      </div>
      <div v-if="countRangeLabel(learnedRuleReturned, learnedRuleTotal)">
        <dt>学习规则</dt>
        <dd>学习规则 {{ countRangeLabel(learnedRuleReturned, learnedRuleTotal) }}</dd>
      </div>
      <div v-if="countRangeLabel(candidateReturned, candidateTotal)">
        <dt>知识库候选</dt>
        <dd>知识库候选 {{ countRangeLabel(candidateReturned, candidateTotal) }}</dd>
      </div>
      <div v-if="referencePatternReturned !== null">
        <dt>写法参考</dt>
        <dd>写法参考 {{ referencePatternReturned }}</dd>
      </div>
    </dl>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`knowledge-route-next:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
    <ul
      v-if="learnedRuleRows.length"
      class="agent-run-drawer__reference-patterns"
    >
      <li
        v-for="row in learnedRuleRows"
        :key="row.key"
      >
        <div>
          <strong>{{ row.condition || '学习规则' }}</strong>
        </div>
        <p v-if="row.action">{{ row.action }}</p>
      </li>
    </ul>
    <ul
      v-if="candidateRows.length"
      class="agent-run-drawer__reference-patterns"
    >
      <li
        v-for="row in candidateRows"
        :key="row.key"
      >
        <div>
          <strong>{{ row.title }}</strong>
          <span>{{ row.type }}</span>
        </div>
        <p v-if="row.summary">{{ row.summary }}</p>
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
        {{ row.message }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__knowledge-route {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__knowledge-route h4 {
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
.agent-run-drawer__reference-patterns,
.agent-run-drawer__planner-signals {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__tools li,
.agent-run-drawer__planner-signals li,
.agent-run-drawer__reference-patterns li {
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__reference-patterns li {
  display: grid;
  gap: var(--space-1);
}

.agent-run-drawer__reference-patterns div {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
}

.agent-run-drawer__reference-patterns strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__reference-patterns span,
.agent-run-drawer__reference-patterns p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
}
</style>
