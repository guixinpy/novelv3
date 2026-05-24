<script setup lang="ts">
import { computed } from 'vue'
import BaseModal from '../base/BaseModal.vue'
import type { WritingAgentRunDetail } from '../../api/types'

const props = defineProps<{
  open: boolean
  loading: boolean
  error: string
  run: WritingAgentRunDetail | null
  pendingActionId?: string | null
}>()

const emit = defineEmits<{
  close: []
  refresh: []
  executeRecovery: [payload: { sourceRunId: string; planHash: string }]
  applyRouteUpgrade: [payload: {
    sourceRunId: string
    pendingActionId: string
    approvalContractHash: string
    approvalContract: Record<string, unknown>
  }]
}>()

const steps = computed(() => props.run?.steps || [])
const runInput = computed(() => (isRecord(props.run?.input) ? props.run.input : {}))
const agentProfileScope = computed(() => recordValue(props.run?.agent_profile_scope))
const agentToolDiscovery = computed(() => recordValue(props.run?.agent_tool_discovery))
const agentProfile = computed(() => (
  stringValue(props.run?.agent_profile) ||
  stringValue(agentToolDiscovery.value.effective_profile) ||
  stringValue(agentProfileScope.value.agent_profile)
))
const hasAgentProfileProjection = computed(() => Boolean(
  agentProfile.value ||
  Object.keys(agentToolDiscovery.value).length ||
  Object.keys(agentProfileScope.value).length,
))
const toolDiscoveryStatus = computed(() => (
  stringValue(agentToolDiscovery.value.status) ||
  (agentToolDiscovery.value.scope_applied === true ? 'applied' : '') ||
  stringValue(agentProfileScope.value.status)
))
const allowedVisibleToolCount = computed(() => (
  numberValue(agentToolDiscovery.value.visible_tool_count) ??
  numberValue(agentProfileScope.value.allowed_visible_tool_count)
))
const profileFilteredVisibleToolCount = computed(() => (
  numberValue(agentToolDiscovery.value.filtered_by_profile_count) ??
  numberValue(agentProfileScope.value.profile_filtered_visible_tool_count)
))
const recoveryPreview = computed(() => {
  const step = steps.value.find((item) => item.tool_name === 'plan_recovery_tools')
  return isRecord(step?.output) ? step.output : null
})
const isRecoveryExecutionRun = computed(() => (
  props.run?.entrypoint === 'ui_recovery_execute' ||
  runInput.value.execute_recovery === true
))
const executionPolicy = computed(() => {
  const value = recoveryPreview.value?.execution_policy
  return isRecord(value) ? value : null
})
const guardrails = computed(() => {
  const value = recoveryPreview.value?.guardrails
  return isRecord(value) ? value : null
})
const guardrailBlockers = computed(() => {
  const blockers = guardrails.value?.blockers
  return Array.isArray(blockers) ? blockers.filter(isRecord) : []
})
const recoveryTools = computed(() => {
  const tools = recoveryPreview.value?.tools
  return Array.isArray(tools) ? tools.filter(isRecord) : []
})
const hasRecoveryPolicy = computed(() => Boolean(executionPolicy.value || guardrails.value || recoveryTools.value.length))
const runKindLabel = computed(() => {
  if (isRecoveryExecutionRun.value) return '恢复执行'
  if (recoveryPreview.value) return '恢复预览'
  if (props.run?.entrypoint === 'dialog_auto_plan') return '自动规划'
  return '普通运行'
})
const recoverySourceRunId = computed(() => (
  stringValue(runInput.value.recovery_run_id) || stringValue(recoveryPreview.value?.source_run_id)
))
const recoveryPlanHash = computed(() => (
  stringValue(runInput.value.recovery_plan_hash) || stringValue(recoveryPreview.value?.plan_hash)
))
const recoveryExecutePayload = computed(() => {
  const sourceRunId = stringValue(recoveryPreview.value?.source_run_id)
  const planHash = stringValue(recoveryPreview.value?.plan_hash)
  if (
    recoveryPreview.value?.can_execute === true &&
    executionPolicy.value?.status === 'ready' &&
    sourceRunId &&
    planHash
  ) {
    return { sourceRunId, planHash }
  }
  return null
})
const routeUpgradeContractOutput = computed(() => {
  for (let index = steps.value.length - 1; index >= 0; index -= 1) {
    const step = steps.value[index]
    if (step?.tool_name !== 'preview_pending_action_route_approval_opt_in_apply_contract') continue
    const output = recordValue(step.output)
    if (Object.keys(output).length) return output
  }
  return null
})
const routeUpgradeStatus = computed(() => stringValue(routeUpgradeContractOutput.value?.status))
const routeUpgradeRequiredConfirmation = computed(() => routeUpgradeContractOutput.value?.required_confirmation === true)
const routeUpgradeContract = computed(() => recordValue(routeUpgradeContractOutput.value?.approval_contract))
const routeUpgradeContractHash = computed(() => stringValue(routeUpgradeContractOutput.value?.approval_contract_hash))
const routeUpgradePendingActionId = computed(() => {
  const output = routeUpgradeContractOutput.value
  const routePreview = recordValue(output?.route_apply_preview)
  const recommendedCall = firstRecommendedRouteApplyCall(output)
  const recommendedParams = recordValue(recommendedCall?.params)
  return (
    stringValue(output?.pending_action_id) ||
    stringValue(routePreview.pending_action_id) ||
    stringValue(recommendedParams.pending_action_id)
  )
})
const canApplyRouteUpgrade = computed(() => {
  const output = routeUpgradeContractOutput.value
  if (!props.run?.id || !output) return false
  if (props.run.entrypoint !== 'pending_action_safety_action') return false
  if (props.run.status !== 'success') return false
  if (routeUpgradeStatus.value !== 'requires_confirmation') return false
  if (!routeUpgradeRequiredConfirmation.value) return false
  if (!routeUpgradePendingActionId.value || !routeUpgradeContractHash.value || !Object.keys(routeUpgradeContract.value).length) return false
  if (String(props.pendingActionId || '').trim() !== routeUpgradePendingActionId.value) return false
  return hasRouteApplyRecommendation(output)
})

function close() {
  emit('close')
}

function refreshRun() {
  emit('refresh')
}

function executeRecovery() {
  if (!recoveryExecutePayload.value) return
  emit('executeRecovery', recoveryExecutePayload.value)
}

function applyRouteUpgrade() {
  if (!canApplyRouteUpgrade.value || !props.run?.id) return
  emit('applyRouteUpgrade', {
    sourceRunId: props.run.id,
    pendingActionId: routeUpgradePendingActionId.value,
    approvalContractHash: routeUpgradeContractHash.value,
    approvalContract: routeUpgradeContract.value,
  })
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === 'object' && !Array.isArray(value))
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value : ''
}

function numberValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function booleanLabel(value: unknown, trueLabel: string, falseLabel: string) {
  return value === true ? trueLabel : falseLabel
}

function agentProfileLabel(profile: unknown) {
  const value = stringValue(profile)
  if (value === 'orchestrator') return '编排主控'
  if (value === 'drafting_worker') return '创作执行者'
  if (value === 'reviewer_worker') return '审稿执行者'
  if (value === 'world_model_worker') return '世界模型执行者'
  if (value === 'recovery_worker') return '恢复维护者'
  return value || '未标注'
}

function agentProfileScopeStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'applied') return '已按身份收窄'
  if (value === 'not_requested') return '未请求身份收窄'
  if (value === 'unknown_profile') return '未知身份，已拒绝工具面'
  return value || '未知'
}

function policyStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可执行'
  if (value === 'requires_user_input') return '需要用户补充输入'
  if (value === 'confirmation_required') return '等待确认'
  if (value === 'repeat_failed_recovery') return '重复失败保护'
  if (value === 'blocked') return '已阻止'
  if (value === 'not_executable') return '不可执行'
  return value || '未知'
}

function guardrailStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '通过'
  if (value === 'blocked') return '已阻止'
  return value || '未知'
}

function routeUpgradeStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'requires_confirmation') return '等待确认'
  if (value === 'blocked') return '已阻止'
  if (value === 'not_required') return '无需处理'
  if (value === 'success') return '成功'
  return value || '未知'
}

function recordValue(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {}
}

function firstRecommendedRouteApplyCall(output: Record<string, unknown> | null | undefined) {
  const calls = Array.isArray(output?.recommended_next_tool_calls) ? output.recommended_next_tool_calls : []
  return calls
    .filter(isRecord)
    .find((call) => call.tool_name === 'apply_pending_action_route_approval_opt_in') || null
}

function hasRouteApplyRecommendation(output: Record<string, unknown>) {
  const tools = Array.isArray(output.recommended_next_tools) ? output.recommended_next_tools : []
  if (tools.includes('apply_pending_action_route_approval_opt_in')) return true
  return Boolean(firstRecommendedRouteApplyCall(output))
}
</script>

<template>
  <BaseModal
    :open="open"
    title="Agent 运行详情"
    width="720px"
    test-id="agent-run-drawer"
    @close="close"
  >
    <div class="agent-run-drawer">
      <p v-if="loading" class="agent-run-drawer__state">正在加载 Agent 运行详情...</p>
      <p v-else-if="error" class="agent-run-drawer__state agent-run-drawer__state--error">{{ error }}</p>
      <p v-else-if="!run" class="agent-run-drawer__state">暂无运行详情。</p>
      <template v-else>
        <section class="agent-run-drawer__summary">
          <div class="agent-run-drawer__summary-head">
            <div>
              <span class="agent-run-drawer__eyebrow">目标</span>
              <h4>{{ run.goal }}</h4>
            </div>
            <button
              type="button"
              class="agent-run-drawer__ghost"
              data-testid="refresh-agent-run"
              @click="refreshRun"
            >
              刷新运行
            </button>
          </div>
          <dl>
            <div>
              <dt>状态</dt>
              <dd>{{ run.status }}</dd>
            </div>
            <div>
              <dt>入口</dt>
              <dd>{{ run.entrypoint }}</dd>
            </div>
            <div>
              <dt>运行 ID</dt>
              <dd>{{ run.id }}</dd>
            </div>
            <div>
              <dt>运行类型</dt>
              <dd>{{ runKindLabel }}</dd>
            </div>
            <div v-if="hasAgentProfileProjection">
              <dt>Agent 身份</dt>
              <dd>{{ agentProfileLabel(agentProfile) }}</dd>
            </div>
            <div v-if="toolDiscoveryStatus">
              <dt>工具面</dt>
              <dd>{{ agentProfileScopeStatusLabel(toolDiscoveryStatus) }}</dd>
            </div>
            <div v-if="allowedVisibleToolCount !== null">
              <dt>可见工具</dt>
              <dd>{{ allowedVisibleToolCount }}</dd>
            </div>
            <div v-if="profileFilteredVisibleToolCount !== null">
              <dt>已过滤</dt>
              <dd>{{ profileFilteredVisibleToolCount }}</dd>
            </div>
            <div v-if="recoverySourceRunId">
              <dt>来源运行</dt>
              <dd>{{ recoverySourceRunId }}</dd>
            </div>
            <div v-if="recoveryPlanHash">
              <dt>计划哈希</dt>
              <dd>{{ recoveryPlanHash }}</dd>
            </div>
          </dl>
        </section>

        <section
          v-if="hasRecoveryPolicy"
          class="agent-run-drawer__recovery"
          aria-label="Recovery policy"
        >
          <h4>恢复执行策略</h4>
          <dl v-if="executionPolicy" class="agent-run-drawer__facts">
            <div>
              <dt>策略状态</dt>
              <dd>{{ policyStatusLabel(executionPolicy.status) }}</dd>
            </div>
            <div>
              <dt>确认要求</dt>
              <dd>{{ booleanLabel(executionPolicy.requires_confirmation, '需要确认', '无需确认') }}</dd>
            </div>
            <div>
              <dt>计划哈希</dt>
              <dd>{{ booleanLabel(executionPolicy.requires_plan_hash, '需要计划哈希', '无需计划哈希') }}</dd>
            </div>
            <div>
              <dt>自动执行</dt>
              <dd>{{ booleanLabel(executionPolicy.safe_auto_execute, '允许安全自动执行', '不允许自动执行') }}</dd>
            </div>
          </dl>
          <dl v-if="guardrails" class="agent-run-drawer__facts">
            <div>
              <dt>保护策略</dt>
              <dd>{{ guardrailStatusLabel(guardrails.status) }}</dd>
            </div>
          </dl>
          <ul
            v-if="guardrailBlockers.length"
            class="agent-run-drawer__blockers"
          >
            <li
              v-for="(blocker, index) in guardrailBlockers"
              :key="`${blocker.code || 'blocker'}:${index}`"
            >
              <strong>{{ blocker.code }}</strong>
              <span v-if="blocker.tool_name">{{ blocker.tool_name }}</span>
              <p>{{ blocker.message || '未提供阻止原因。' }}</p>
            </li>
          </ul>
          <ul
            v-if="recoveryTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="(tool, index) in recoveryTools"
              :key="`${tool.tool_name || 'tool'}:${index}`"
            >
              {{ tool.tool_name }}
            </li>
          </ul>
          <div v-if="recoveryExecutePayload" class="agent-run-drawer__actions">
            <button
              type="button"
              class="agent-run-drawer__execute"
              data-testid="execute-recovery"
              @click="executeRecovery"
            >
              确认执行恢复
            </button>
          </div>
        </section>

        <section
          v-if="routeUpgradeContractOutput"
          class="agent-run-drawer__route-upgrade"
          aria-label="Route upgrade approval"
        >
          <h4>路由升级审批</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>契约状态</dt>
              <dd>{{ routeUpgradeStatusLabel(routeUpgradeStatus) }}</dd>
            </div>
            <div>
              <dt>确认要求</dt>
              <dd>{{ routeUpgradeRequiredConfirmation ? '需要确认' : '无需确认' }}</dd>
            </div>
            <div v-if="routeUpgradePendingActionId">
              <dt>待处理动作</dt>
              <dd>{{ routeUpgradePendingActionId }}</dd>
            </div>
          </dl>
          <div v-if="canApplyRouteUpgrade" class="agent-run-drawer__actions">
            <button
              type="button"
              class="agent-run-drawer__execute"
              data-testid="apply-route-upgrade"
              @click="applyRouteUpgrade"
            >
              确认应用路由升级
            </button>
          </div>
        </section>

        <section class="agent-run-drawer__steps" aria-label="Agent run steps">
          <h4>工具步骤</h4>
          <ol v-if="steps.length">
            <li
              v-for="step in steps"
              :key="step.id"
              class="agent-run-drawer__step"
            >
              <span class="agent-run-drawer__step-index">#{{ step.step_index }}</span>
              <span class="agent-run-drawer__step-tool">{{ step.tool_name }}</span>
              <span class="agent-run-drawer__step-status">{{ step.status }}</span>
            </li>
          </ol>
          <p v-else class="agent-run-drawer__state">暂无工具步骤。</p>
        </section>
      </template>
    </div>
  </BaseModal>
</template>

<style scoped>
.agent-run-drawer {
  display: grid;
  gap: var(--space-4);
}

.agent-run-drawer__state {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.agent-run-drawer__state--error {
  color: var(--color-error);
}

.agent-run-drawer__summary {
  display: grid;
  gap: var(--space-3);
}

.agent-run-drawer__summary-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.agent-run-drawer__eyebrow {
  display: block;
  margin-bottom: var(--space-1);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.agent-run-drawer__summary h4,
.agent-run-drawer__recovery h4,
.agent-run-drawer__steps h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.agent-run-drawer__summary dl,
.agent-run-drawer__facts {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.agent-run-drawer__summary dl div,
.agent-run-drawer__facts div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: var(--space-3);
}

.agent-run-drawer__summary dt,
.agent-run-drawer__facts dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-drawer__summary dd,
.agent-run-drawer__facts dd {
  margin: 0;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__recovery {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__route-upgrade {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__blockers,
.agent-run-drawer__tools {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__blockers li {
  display: grid;
  gap: 2px;
  padding: var(--space-2);
  border-left: 3px solid var(--color-warning);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
}

.agent-run-drawer__blockers strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__blockers span {
  color: var(--color-text-secondary);
  overflow-wrap: anywhere;
}

.agent-run-drawer__blockers p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
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

.agent-run-drawer__actions {
  display: flex;
  justify-content: flex-end;
}

.agent-run-drawer__execute {
  min-height: 32px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-primary);
  border-radius: var(--radius-sm);
  background: var(--color-primary);
  color: var(--color-bg-white);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
}

.agent-run-drawer__execute:hover {
  filter: brightness(0.96);
}

.agent-run-drawer__ghost {
  min-height: 30px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  white-space: nowrap;
  cursor: pointer;
}

.agent-run-drawer__ghost:hover {
  border-color: var(--color-border-strong);
  color: var(--color-text-primary);
}

.agent-run-drawer__steps {
  display: grid;
  gap: var(--space-2);
}

.agent-run-drawer__steps ol {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__step {
  display: grid;
  grid-template-columns: 3rem minmax(0, 1fr) max-content;
  gap: var(--space-2);
  align-items: center;
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
  font-size: var(--text-xs);
}

.agent-run-drawer__step-index,
.agent-run-drawer__step-status {
  color: var(--color-text-tertiary);
}

.agent-run-drawer__step-tool {
  min-width: 0;
  color: var(--color-text-primary);
  font-weight: var(--font-medium);
  overflow-wrap: anywhere;
}
</style>
