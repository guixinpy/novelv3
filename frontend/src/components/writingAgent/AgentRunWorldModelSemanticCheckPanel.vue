<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const semanticCheck = computed(() => recordValue(props.output.semantic_check))
const factWindow = computed(() => recordValue(props.output.fact_window))
const recommendedTools = computed(() => stringList(props.output.recommended_next_tools))
const chapterLabel = computed(() => chapterIndexLabel(props.output.chapter_index))
const subject = computed(() => safeText(props.output.subject_ref))
const summary = computed(() => safeText(semanticCheck.value.summary))
const returnedFacts = computed(() => numberValue(factWindow.value.returned_facts))
const totalFacts = computed(() => numberValue(factWindow.value.total_confirmed_facts))
const factLimit = computed(() => numberValue(factWindow.value.limit))
const issueCount = computed(() => (
  numberValue(semanticCheck.value.issue_count) ?? recordList(props.output.issues).length
))
const issueRows = computed(() => (
  recordList(props.output.issues)
    .slice(0, 5)
    .map((issue, index) => ({
      key: `world-model-semantic-issue:${index}`,
      code: safeText(issue.code),
      severity: severityLabel(issue.severity),
      subject: safeText(issue.subject_ref),
      predicate: safeText(issue.predicate),
      message: safeText(issue.message),
      evidence: safeText(issue.evidence_excerpt),
    }))
    .filter((row) => Boolean(row.code || row.message || row.evidence))
))

function statusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'passed') return '通过'
  if (value === 'issues_found') return '已发现问题'
  if (value === 'blocked') return '已阻塞'
  if (value === 'failed') return '失败'
  if (value === 'completed' || value === 'success' || value === 'ready') return '已完成'
  return value || '未知'
}

function severityLabel(severity: unknown) {
  const value = stringValue(severity)
  if (value === 'error') return '错误'
  if (value === 'warning') return '警告'
  if (value === 'info') return '提示'
  return safeText(value)
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
  if (/[A-Za-z_]+:[A-Za-z0-9_.-]+/.test(value)) return ''
  if (/(project|profile|fact|claim|trace|prompt)-secret|source_refs?|source_id|evidence_refs?|claim_id|llm_prompt_contract|prompt_contract|template_hash|raw prompt|phase\d+\.world_model_semantic_check|world_profile:/i.test(value)) return ''
  return value.slice(0, 120)
}
</script>

<template>
  <section
    class="agent-run-drawer__world-semantic-check"
    aria-label="World model semantic check projection"
  >
    <h4>世界模型语义检查</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(semanticCheck.status) }}</dd>
      </div>
      <div v-if="issueCount !== null">
        <dt>问题</dt>
        <dd>问题 {{ issueCount }}</dd>
      </div>
      <div v-if="chapterLabel">
        <dt>章节</dt>
        <dd>{{ chapterLabel }}</dd>
      </div>
      <div v-if="subject">
        <dt>主体</dt>
        <dd>{{ subject }}</dd>
      </div>
      <div v-if="countRangeLabel(returnedFacts, totalFacts)">
        <dt>确认事实</dt>
        <dd>确认事实 {{ countRangeLabel(returnedFacts, totalFacts) }}</dd>
      </div>
      <div v-if="factLimit !== null">
        <dt>事实上限</dt>
        <dd>检查事实上限 {{ factLimit }}</dd>
      </div>
    </dl>
    <p v-if="summary">{{ summary }}</p>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`world-semantic-tool:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
    <ul
      v-if="issueRows.length"
      class="agent-run-drawer__planner-signals"
    >
      <li
        v-for="row in issueRows"
        :key="row.key"
      >
        <strong>{{ [row.code, row.severity].filter(Boolean).join(' · ') || '语义问题' }}</strong>
        <span v-if="[row.subject, row.predicate].filter(Boolean).length">
          {{ [row.subject, row.predicate].filter(Boolean).join(' · ') }}
        </span>
        <span v-if="row.message">{{ row.message }}</span>
        <span v-if="row.evidence">{{ row.evidence }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__world-semantic-check {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__world-semantic-check h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.agent-run-drawer__world-semantic-check p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
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
  line-height: var(--leading-normal);
}
</style>
