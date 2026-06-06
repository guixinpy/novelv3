<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const summary = computed(() => recordValue(props.output.summary))
const status = computed(() => stringValue(props.output.status))
const writeToolCount = computed(() => numberValue(summary.value.write_tool_count))
const enforcedCount = computed(() => numberValue(summary.value.agent_plan_gate_enforced_count))
const confirmationGuardCount = computed(() => numberValue(summary.value.direct_confirmation_guard_count))
const missingGateCount = computed(() => numberValue(summary.value.missing_agent_plan_gate_count))
const highRiskCount = computed(() => numberValue(summary.value.high_risk_direct_write_count))
const targetRows = computed(() => (
  recordList(props.output.recommended_next_targets)
    .slice(0, 6)
    .map((target, index) => ({
      key: `write-gate-target:${stringValue(target.tool_name) || index}`,
      toolName: stringValue(target.tool_name),
      riskLabel: riskLabel(target.risk_level),
      gateStatusLabel: gateStatusLabel(target.agent_plan_gate_status),
      actionLabel: recommendedActionLabel(target.recommended_action),
    }))
    .filter((row) => row.toolName || row.riskLabel || row.gateStatusLabel || row.actionLabel)
))

function statusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'completed' || statusValue === 'success') return '已完成'
  if (statusValue === 'running') return '进行中'
  if (statusValue === 'failed') return '失败'
  if (statusValue === 'blocked') return '已阻塞'
  return statusValue || '未知'
}

function riskLabel(value: unknown) {
  const riskValue = stringValue(value)
  if (riskValue === 'high') return '高风险'
  if (riskValue === 'medium') return '中风险'
  if (riskValue === 'low') return '低风险'
  return riskValue || ''
}

function gateStatusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'enforced') return 'Agent 审批已强制'
  if (statusValue === 'indirect_agent_gate_available') return '间接审批可用'
  if (statusValue === 'missing_agent_plan_gate') return '缺少 Agent 计划门禁'
  return statusValue || ''
}

function recommendedActionLabel(value: unknown) {
  const actionValue = stringValue(value)
  if (actionValue === 'monitor_gate_drift') return '持续监控门禁漂移'
  if (actionValue === 'route_direct_calls_to_approval_executor') return '转到审批执行器'
  if (actionValue === 'promote_confirm_guard_to_agent_plan_approval') return '升级确认守卫为 Agent 审批'
  if (actionValue === 'add_direct_agent_plan_approval_gate') return '补齐 Agent 计划审批门禁'
  return actionValue || ''
}
</script>

<template>
  <section
    class="agent-run-drawer__write-gate"
    aria-label="Write gate coverage projection"
  >
    <h4>写入门禁覆盖</h4>
    <dl class="agent-run-drawer__facts">
      <div v-if="status">
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
      </div>
      <div v-if="writeToolCount !== null">
        <dt>写入工具</dt>
        <dd>{{ writeToolCount }}</dd>
      </div>
      <div v-if="enforcedCount !== null">
        <dt>Agent 审批</dt>
        <dd>{{ enforcedCount }}</dd>
      </div>
      <div v-if="confirmationGuardCount !== null">
        <dt>确认守卫</dt>
        <dd>{{ confirmationGuardCount }}</dd>
      </div>
      <div v-if="missingGateCount !== null">
        <dt>门禁缺口</dt>
        <dd>{{ missingGateCount }}</dd>
      </div>
      <div v-if="highRiskCount !== null">
        <dt>高风险直写</dt>
        <dd>{{ highRiskCount }}</dd>
      </div>
    </dl>
    <ul
      v-if="targetRows.length"
      class="agent-run-drawer__planner-signals"
    >
      <li
        v-for="row in targetRows"
        :key="row.key"
      >
        <strong>{{ row.toolName || '写入工具' }}</strong>
        <span>{{ [row.riskLabel, row.gateStatusLabel, row.actionLabel].filter(Boolean).join(' · ') }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__write-gate {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__write-gate h4 {
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

.agent-run-drawer__planner-signals {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
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

.agent-run-drawer__planner-signals strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__planner-signals span {
  color: var(--color-text-secondary);
}
</style>
