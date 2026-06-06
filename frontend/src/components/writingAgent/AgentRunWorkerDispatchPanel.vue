<script setup lang="ts">
import { computed } from 'vue'
import {
  numberValue,
  recordList,
  recordValue,
  stringList,
  stringValue,
} from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const summary = computed(() => recordValue(props.output.summary))
const status = computed(() => stringValue(props.output.status))
const workerCount = computed(() => numberValue(summary.value.workers))
const plannedTaskCount = computed(() => numberValue(summary.value.planned_tasks))
const blockedTaskCount = computed(() => numberValue(summary.value.blocked_tasks))
const issueCount = computed(() => numberValue(summary.value.issues))
const routeRegistry = computed(() => recordValue(props.output.route_registry))
const routeRegistrySummary = computed(() => recordValue(routeRegistry.value.summary))
const routeRegistryStatus = computed(() => stringValue(routeRegistry.value.status))
const unroutedToolCount = computed(() => numberValue(routeRegistrySummary.value.unrouted_allowed_tools))
const orphanRecovery = computed(() => recordValue(props.output.orphan_recovery))
const orphanSummary = computed(() => recordValue(orphanRecovery.value.summary))
const orphanStatus = computed(() => stringValue(orphanRecovery.value.status))
const activeWorkerRunCount = computed(() => numberValue(orphanSummary.value.active_worker_runs))
const orphanWorkerRunCount = computed(() => numberValue(orphanSummary.value.orphan_worker_runs))
const recoveryActionCount = computed(() => numberValue(orphanSummary.value.recovery_actions))
const rows = computed(() => {
  const dispatches = recordList(props.output.worker_dispatches)
  const singleDispatch = Object.keys(recordValue(props.output.worker)).length ? [props.output] : []
  return (dispatches.length ? dispatches : singleDispatch)
    .slice(0, 5)
    .map((dispatch, index) => ({
      key: `worker-dispatch-audit:${workerName(dispatch)}:${index}`,
      name: workerName(dispatch),
      meta: workerTaskLabel(dispatch),
    }))
    .filter((dispatch) => dispatch.name || dispatch.meta)
})
const issueRows = computed(() => (
  recordList(props.output.issues)
    .slice(0, 5)
    .map((issue, index) => ({
      key: `worker-dispatch-issue:${stringValue(issue.code) || index}`,
      code: stringValue(issue.code) || 'worker_dispatch_issue',
    }))
))
const recommendedTools = computed(() => uniqueStrings([
  ...stringList(orphanRecovery.value.recommended_tools),
  ...stringList(props.output.recommended_next_tools),
]).slice(0, 5))

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values))
}

function statusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'ready') return '就绪'
  if (statusValue === 'blocked') return '已阻塞'
  if (statusValue === 'running') return '进行中'
  if (statusValue === 'failed') return '失败'
  if (statusValue === 'success' || statusValue === 'completed') return '已完成'
  return statusValue || '未知'
}

function routeRegistryStatusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'passed') return '通过'
  if (statusValue === 'needs_attention') return '需处理'
  return statusValue || '未知'
}

function orphanRecoveryStatusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'clear') return '无孤儿'
  if (statusValue === 'needs_attention') return '需处理'
  return statusValue || '未知'
}

function workerName(dispatch: Record<string, unknown>) {
  return workerNameLabel(recordValue(dispatch.worker).name)
}

function workerNameLabel(value: unknown) {
  const profile = stringValue(value)
  if (profile === 'orchestrator') return '编排主控'
  if (profile === 'drafting_worker') return '创作执行者'
  if (profile === 'reviewer_worker') return '审稿执行者'
  if (profile === 'memory_worker') return '记忆维护者'
  if (profile === 'retrieval_worker') return '检索取证者'
  if (profile === 'world_model_worker') return '世界模型执行者'
  if (profile === 'revision_worker') return '修订执行者'
  if (profile === 'recovery_worker') return '恢复维护者'
  return profile || '未标注'
}

function workerTaskLabel(dispatch: Record<string, unknown>) {
  const taskSummary = recordValue(dispatch.summary)
  const planned = numberValue(taskSummary.planned_tasks)
  const blocked = numberValue(taskSummary.blocked_tasks)
  const issues = numberValue(taskSummary.issues)
  const parts = []
  if (planned !== null) parts.push(`${planned} 个任务`)
  if (blocked !== null && blocked > 0) parts.push(`${blocked} 个阻塞`)
  if (issues !== null && issues > 0) parts.push(`${issues} 个问题`)
  return parts.join(' · ')
}
</script>

<template>
  <section
    class="agent-run-drawer__worker-dispatch"
    aria-label="Worker dispatch projection"
  >
    <h4>Worker 分派审计</h4>
    <dl class="agent-run-drawer__facts">
      <div v-if="status">
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
      </div>
      <div v-if="workerCount !== null">
        <dt>Worker</dt>
        <dd>{{ workerCount }}</dd>
      </div>
      <div v-if="plannedTaskCount !== null">
        <dt>计划任务</dt>
        <dd>{{ plannedTaskCount }}</dd>
      </div>
      <div v-if="blockedTaskCount !== null">
        <dt>阻塞任务</dt>
        <dd>{{ blockedTaskCount }}</dd>
      </div>
      <div v-if="issueCount !== null">
        <dt>问题</dt>
        <dd>{{ issueCount }}</dd>
      </div>
      <div v-if="routeRegistryStatus">
        <dt>路由审计</dt>
        <dd>{{ routeRegistryStatusLabel(routeRegistryStatus) }}</dd>
      </div>
      <div v-if="unroutedToolCount !== null">
        <dt>未路由工具</dt>
        <dd>{{ unroutedToolCount }}</dd>
      </div>
      <div v-if="orphanStatus">
        <dt>孤儿恢复</dt>
        <dd>{{ orphanRecoveryStatusLabel(orphanStatus) }}</dd>
      </div>
    </dl>
    <ul
      v-if="activeWorkerRunCount !== null || orphanWorkerRunCount !== null || recoveryActionCount !== null"
      class="agent-run-drawer__worker-dispatches"
    >
      <li v-if="activeWorkerRunCount !== null">
        <strong>活跃 worker {{ activeWorkerRunCount }}</strong>
      </li>
      <li v-if="orphanWorkerRunCount !== null">
        <strong>孤儿 worker {{ orphanWorkerRunCount }}</strong>
      </li>
      <li v-if="recoveryActionCount !== null">
        <strong>恢复动作 {{ recoveryActionCount }}</strong>
      </li>
    </ul>
    <ul
      v-if="rows.length"
      class="agent-run-drawer__worker-dispatches"
    >
      <li
        v-for="dispatch in rows"
        :key="dispatch.key"
      >
        <strong>{{ dispatch.name }}</strong>
        <span v-if="dispatch.meta">{{ dispatch.meta }}</span>
      </li>
    </ul>
    <ul
      v-if="issueRows.length"
      class="agent-run-drawer__planner-signals"
    >
      <li
        v-for="issue in issueRows"
        :key="issue.key"
      >
        <strong>{{ issue.code }}</strong>
      </li>
    </ul>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`worker-dispatch-next:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__worker-dispatch {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__worker-dispatch h4 {
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

.agent-run-drawer__worker-dispatches,
.agent-run-drawer__planner-signals,
.agent-run-drawer__tools {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__worker-dispatches li {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__worker-dispatches strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__worker-dispatches span {
  color: var(--color-text-secondary);
}

.agent-run-drawer__planner-signals li {
  display: grid;
  gap: 2px;
  padding: var(--space-2);
  border-left: 3px solid var(--color-warning);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
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
