<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const route = computed(() => recordValue(props.output.route))
const factSummary = computed(() => recordValue(props.output.fact_summary))
const proposalPressure = computed(() => recordValue(props.output.proposal_pressure))
const facts = computed(() => recordList(props.output.facts))
const diagnostics = computed(() => recordList(props.output.diagnostics))
const recommendedActions = computed(() => stringList(props.output.recommended_actions))
const chapterLabel = computed(() => chapterIndexLabel(props.output.chapter_index))
const subject = computed(() => safeText(props.output.subject_ref))
const generationLabel = computed(() => (
  route.value.can_use_world_model === true ? '可用于生成' : '不可用于生成'
))
const confirmedFactReturned = computed(() => numberValue(factSummary.value.returned_facts))
const confirmedFactTotal = computed(() => numberValue(factSummary.value.total_confirmed_facts))
const pendingProposalCount = computed(() => (
  numberValue(route.value.pending_proposal_count) ??
  numberValue(proposalPressure.value.total_items)
))
const highRiskCount = computed(() => numberValue(recordValue(proposalPressure.value.risk_counts).high))
const mediumRiskCount = computed(() => numberValue(recordValue(proposalPressure.value.risk_counts).medium))
const factRows = computed(() => (
  facts.value
    .map((fact, index) => {
      const confidence = numberValue(fact.confidence)
      return {
        key: `world-model-fact:${index}`,
        subject: safeText(fact.subject_ref),
        predicate: safeText(fact.predicate),
        object: safeText(fact.object_ref_or_value),
        chapterLabel: chapterIndexLabel(fact.chapter_index),
        confidenceLabel: confidence !== null ? `置信 ${confidence}` : '',
      }
    })
    .filter((row) => Boolean(row.subject || row.predicate || row.object))
))
const proposalClusterRows = computed(() => (
  recordList(proposalPressure.value.clusters)
    .map((cluster, index) => {
      const subjects = stringList(cluster.subject_refs)
        .map((value) => safeText(value))
        .filter(Boolean)
      const candidateCount = numberValue(cluster.candidate_count)
      return {
        key: `world-model-cluster:${index}`,
        title: [subjects.join(', '), safeText(cluster.predicate)].filter(Boolean).join(' · ') || '待审提案',
        meta: [
          riskLabel(cluster.risk_level),
          reviewModeLabel(cluster.review_mode),
          candidateCount !== null ? `${candidateCount} 个候选` : '',
          chapterRangeLabel(cluster.chapter_range),
        ].filter(Boolean).join(' · '),
        reason: safeText(cluster.reason),
      }
    })
    .filter((row) => Boolean(row.title || row.meta || row.reason))
))
const diagnosticRows = computed(() => (
  diagnostics.value
    .map((item, index) => ({
      key: `world-model-diagnostic:${index}`,
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
  if (value === 'missing_profile') return '缺少 Profile'
  return value || '未知'
}

function riskLabel(risk: unknown) {
  const value = stringValue(risk)
  if (value === 'high') return '高风险'
  if (value === 'medium') return '中风险'
  if (value === 'low') return '低风险'
  return value
}

function reviewModeLabel(mode: unknown) {
  const value = stringValue(mode)
  if (value === 'individual') return '逐项审阅'
  if (value === 'batch') return '批量审阅'
  return value
}

function chapterRangeLabel(rangeValue: unknown) {
  const range = recordValue(rangeValue)
  const start = numberValue(range.start)
  const end = numberValue(range.end)
  if (start !== null && end !== null && start !== end) return `第${start}-${end}章`
  if (start !== null) return chapterIndexLabel(start)
  if (end !== null) return chapterIndexLabel(end)
  return ''
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
  if (/(project|profile|fact|cluster|item|bundle)-secret|source_refs?|source_id|evidence_refs?|approval_contract|approval:|world_profile:|phase\d+\.agent_world_model_route/i.test(value)) return ''
  return value.slice(0, 96)
}
</script>

<template>
  <section
    class="agent-run-drawer__world-model-route"
    aria-label="World model route projection"
  >
    <h4>世界模型路由</h4>
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
      <div v-if="subject">
        <dt>主体</dt>
        <dd>{{ subject }}</dd>
      </div>
      <div v-if="countRangeLabel(confirmedFactReturned, confirmedFactTotal)">
        <dt>确认事实</dt>
        <dd>确认事实 {{ countRangeLabel(confirmedFactReturned, confirmedFactTotal) }}</dd>
      </div>
      <div v-if="pendingProposalCount !== null">
        <dt>待审提案</dt>
        <dd>待审提案 {{ pendingProposalCount }}</dd>
      </div>
      <div v-if="highRiskCount !== null && highRiskCount > 0">
        <dt>高风险</dt>
        <dd>高风险 {{ highRiskCount }}</dd>
      </div>
      <div v-if="mediumRiskCount !== null && mediumRiskCount > 0">
        <dt>中风险</dt>
        <dd>中风险 {{ mediumRiskCount }}</dd>
      </div>
    </dl>
    <ul
      v-if="recommendedActions.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="action in recommendedActions"
        :key="`world-model-action:${action}`"
      >
        {{ action }}
      </li>
    </ul>
    <ul
      v-if="factRows.length"
      class="agent-run-drawer__reference-patterns"
    >
      <li
        v-for="row in factRows"
        :key="row.key"
      >
        <div>
          <strong>{{ [row.subject, row.predicate].filter(Boolean).join(' · ') || '世界事实' }}</strong>
          <span>{{ [row.chapterLabel, row.confidenceLabel].filter(Boolean).join(' · ') }}</span>
        </div>
        <p v-if="row.object">{{ row.object }}</p>
      </li>
    </ul>
    <ul
      v-if="proposalClusterRows.length"
      class="agent-run-drawer__planner-signals"
    >
      <li
        v-for="row in proposalClusterRows"
        :key="row.key"
      >
        <strong>{{ row.title }}</strong>
        <span v-if="row.meta">{{ row.meta }}</span>
        <span v-if="row.reason">{{ row.reason }}</span>
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
.agent-run-drawer__world-model-route {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__world-model-route h4 {
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
.agent-run-drawer__reference-patterns li,
.agent-run-drawer__planner-signals li {
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__reference-patterns li,
.agent-run-drawer__planner-signals li {
  display: grid;
  gap: var(--space-1);
}

.agent-run-drawer__reference-patterns div {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
}

.agent-run-drawer__reference-patterns strong,
.agent-run-drawer__planner-signals strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__reference-patterns span,
.agent-run-drawer__reference-patterns p,
.agent-run-drawer__planner-signals span {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
}
</style>
