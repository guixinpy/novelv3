<script setup lang="ts">
import { computed } from 'vue'
import BaseModal from '../base/BaseModal.vue'
import type { WritingAgentRunDetail } from '../../api/types'

type PlannerPlanExecutePayload = {
  sourceRunId: string
  sourcePlanId: string
  goal: string
  tools: Array<Record<string, unknown>>
  planner: Record<string, unknown>
  approvalContractHash?: string
  approvalContract?: Record<string, unknown>
}

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
  executeRecommendedFollowups: [payload: { sourceRunId: string; planHash: string }]
  executePlannerPlan: [payload: PlannerPlanExecutePayload]
  applyRouteUpgrade: [payload: {
    sourceRunId: string
    pendingActionId: string
    approvalContractHash: string
    approvalContract: Record<string, unknown>
  }]
}>()

const steps = computed(() => props.run?.steps || [])
const runInput = computed(() => (isRecord(props.run?.input) ? props.run.input : {}))
const inputPlannerOutput = computed(() => recordValue(runInput.value.planner))
const plannerPreviewOutput = computed(() => {
  for (let index = steps.value.length - 1; index >= 0; index -= 1) {
    const step = steps.value[index]
    if (step?.tool_name !== 'plan_writing_agent_run' && step?.tool_name !== 'plan_dialog_intent_agent_run') continue
    const output = recordValue(step.output)
    const nestedPlan = recordValue(output.plan)
    return Object.keys(nestedPlan).length ? nestedPlan : output
  }
  return {}
})
const plannerSourceIsPreview = computed(() => (
  Object.keys(inputPlannerOutput.value).length === 0 && Object.keys(plannerPreviewOutput.value).length > 0
))
const plannerOutput = computed(() => (
  Object.keys(inputPlannerOutput.value).length ? inputPlannerOutput.value : plannerPreviewOutput.value
))
const nestedPlannerOutput = computed(() => recordValue(plannerOutput.value.planner))
const nestedPlanOutput = computed(() => recordValue(plannerOutput.value.plan))
const directPlannerTrace = computed(() => recordValue(plannerOutput.value.trace))
const nestedPlanTrace = computed(() => recordValue(nestedPlanOutput.value.trace))
const plannerTrace = computed(() => (
  Object.keys(directPlannerTrace.value).length ? directPlannerTrace.value : nestedPlanTrace.value
))
const plannerSummary = computed(() => (
  Object.keys(nestedPlannerOutput.value).length ? nestedPlannerOutput.value : plannerOutput.value
))
const plannerStatus = computed(() => (
  stringValue(plannerOutput.value.status) || stringValue(nestedPlanOutput.value.status)
))
const plannerIntentClass = computed(() => (
  stringValue(plannerSummary.value.intent_class) ||
  stringValue(nestedPlanOutput.value.intent_class) ||
  stringValue(plannerTrace.value.intent_class)
))
const plannerVersion = computed(() => (
  stringValue(plannerSummary.value.planner_version) ||
  stringValue(nestedPlanOutput.value.planner_version) ||
  stringValue(plannerTrace.value.planner_version)
))
const plannerChapterIndex = computed(() => (
  numberValue(plannerSummary.value.chapter_index) ??
  numberValue(nestedPlanOutput.value.chapter_index)
))
const plannerPlanId = computed(() => (
  stringValue(plannerTrace.value.plan_id) ||
  stringValue(plannerSummary.value.plan_id) ||
  stringValue(nestedPlanTrace.value.plan_id)
))
const plannerToolRequests = computed(() => {
  const direct = toolRequestList(plannerOutput.value.tools)
  if (direct.length) return direct
  const nested = toolRequestList(nestedPlanOutput.value.tools)
  return nested
})
const plannerSelectedTools = computed(() => {
  const traced = uniqueStrings(toolNameList(plannerTrace.value.selected_tools))
  if (traced.length) return traced
  const direct = uniqueStrings(toolNameList(plannerToolRequests.value))
  if (direct.length) return direct
  return uniqueStrings(toolNameList(plannerOutput.value.steps))
})
const plannerRiskFlags = computed(() => stringList(plannerTrace.value.risk_flags))
const plannerMissingDependencies = computed(() => dependencyList(plannerTrace.value.missing_dependencies))
const plannerApprovalContract = computed(() => {
  const direct = recordValue(plannerOutput.value.approval_contract)
  if (Object.keys(direct).length) return direct
  return recordValue(nestedPlanOutput.value.approval_contract)
})
const plannerApprovalStatus = computed(() => stringValue(plannerApprovalContract.value.status))
const plannerApprovalHash = computed(() => (
  stringValue(recordValue(plannerApprovalContract.value.approval).approval_contract_hash)
))
const plannerReferencePatterns = computed(() => {
  const traced = referencePatternList(plannerTrace.value.reference_patterns)
  if (traced.length) return traced
  const nested = referencePatternList(nestedPlanTrace.value.reference_patterns)
  if (nested.length) return nested
  for (const step of steps.value) {
    const outputTrace = recordValue(recordValue(step.output).trace)
    const patterns = referencePatternList(outputTrace.reference_patterns)
    if (patterns.length) return patterns
  }
  return []
})
const plannerReferencePatternVersion = computed(() => {
  if (plannerReferencePatterns.value.length === 0) return ''
  if (stringValue(plannerTrace.value.reference_pattern_version)) return stringValue(plannerTrace.value.reference_pattern_version)
  if (stringValue(nestedPlanTrace.value.reference_pattern_version)) return stringValue(nestedPlanTrace.value.reference_pattern_version)
  for (const step of steps.value) {
    const outputTrace = recordValue(recordValue(step.output).trace)
    const version = stringValue(outputTrace.reference_pattern_version)
    if (version) return version
  }
  return ''
})
const hasPlannerProjection = computed(() => Boolean(
  Object.keys(plannerOutput.value).length &&
  (
    plannerStatus.value ||
    plannerIntentClass.value ||
    plannerVersion.value ||
    plannerSelectedTools.value.length ||
    plannerApprovalStatus.value ||
    plannerRiskFlags.value.length ||
    plannerMissingDependencies.value.length ||
    plannerReferencePatterns.value.length
  ),
))
const plannerExecutePayload = computed<PlannerPlanExecutePayload | null>(() => {
  if (!plannerSourceIsPreview.value || props.run?.status !== 'success') return null
  const approvalReady = (
    plannerApprovalStatus.value === 'requires_confirmation' &&
    Boolean(plannerApprovalHash.value) &&
    Object.keys(plannerApprovalContract.value).length > 0
  )
  if (plannerApprovalStatus.value !== 'not_required' && !approvalReady) return null
  if (!props.run?.id || !plannerPlanId.value || !plannerToolRequests.value.length) return null
  return {
    sourceRunId: props.run.id,
    sourcePlanId: plannerPlanId.value,
    goal: `执行规划工具链：${plannerIntentLabel(plannerIntentClass.value)}`,
    tools: plannerToolRequests.value,
    planner: plannerOutput.value,
    ...(approvalReady
      ? {
          approvalContractHash: plannerApprovalHash.value,
          approvalContract: plannerApprovalContract.value,
        }
      : {}),
  }
})
const agentProfileDefinition = computed(() => recordValue(props.run?.agent_profile_definition))
const agentProfileScope = computed(() => recordValue(props.run?.agent_profile_scope))
const agentToolDiscovery = computed(() => recordValue(props.run?.agent_tool_discovery))
const agentProfilePolicyAudit = computed(() => recordValue(props.run?.agent_profile_policy_audit))
const agentCommandContracts = computed(() => recordValue(props.run?.agent_command_contracts))
const agentCommandContractSummary = computed(() => recordValue(agentCommandContracts.value.summary))
const hasAgentCommandContracts = computed(() => Object.keys(agentCommandContractSummary.value).length > 0)
const agentControlCommandCount = computed(() => numberValue(agentCommandContractSummary.value.agent_control_commands))
const agentCommandContractGapCount = computed(() => numberValue(agentCommandContractSummary.value.gap_count))
const agentControlPlaneReadiness = computed(() => recordValue(props.run?.agent_control_plane_readiness))
const agentControlPlaneSummary = computed(() => recordValue(agentControlPlaneReadiness.value.summary))
const hasAgentControlPlaneReadiness = computed(() => Object.keys(agentControlPlaneSummary.value).length > 0)
const agentControlPlaneStatus = computed(() => stringValue(agentControlPlaneReadiness.value.status))
const agentControlPlaneTotalGapCount = computed(() => numberValue(agentControlPlaneSummary.value.total_gap_count))
const agentControlPlaneToolGapCount = computed(() => numberValue(agentControlPlaneSummary.value.tool_gap_count))
const agentControlPlaneCommandGapCount = computed(() => numberValue(agentControlPlaneSummary.value.command_gap_count))
const agentControlPlaneRecommendedCheckCount = computed(() => (
  Array.isArray(agentControlPlaneReadiness.value.recommended_next_tools)
    ? agentControlPlaneReadiness.value.recommended_next_tools.length
    : 0
))
const agentProfile = computed(() => (
  stringValue(props.run?.agent_profile) ||
  stringValue(agentProfileDefinition.value.profile) ||
  stringValue(agentToolDiscovery.value.effective_profile) ||
  stringValue(agentProfileScope.value.agent_profile)
))
const agentProfileTier = computed(() => stringValue(agentProfileDefinition.value.tier))
const agentProfileDelegationAllowed = computed(() => (
  typeof agentProfileDefinition.value.delegation_allowed === 'boolean'
    ? agentProfileDefinition.value.delegation_allowed
    : null
))
const agentProfileDelegateTargetCount = computed(() => {
  const targets = agentProfileDefinition.value.delegate_to_profiles
  if (agentProfileDefinition.value.delegation_allowed !== true || !Array.isArray(targets)) {
    return 0
  }
  return targets.length
})
const hasAgentProfileProjection = computed(() => Boolean(
  agentProfile.value ||
  Object.keys(agentProfileDefinition.value).length ||
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
const agentProfilePolicyAuditLabel = computed(() => profilePolicyAuditLabel(agentProfilePolicyAudit.value))
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
const recommendedFollowupPreview = computed(() => {
  const step = steps.value.find((item) => item.tool_name === 'plan_recommended_followups')
  return isRecord(step?.output) ? step.output : null
})
const recommendedFollowupState = computed(() => recordValue(recommendedFollowupPreview.value?.recommended_followups))
const recommendedFollowupTools = computed(() => {
  const tools = recommendedFollowupPreview.value?.tools
  return Array.isArray(tools) ? tools.filter(isRecord) : []
})
const recommendedFollowupExecutionPolicy = computed(() => recordValue(recommendedFollowupPreview.value?.execution_policy))
const recommendedFollowupWriteTools = computed(() => {
  const tools = recommendedFollowupState.value.provenance_write_tools
  return Array.isArray(tools) ? tools.filter(isRecord) : []
})
const retrievalContextOutput = computed(() => latestToolOutput('search_agent_retrieval_context'))
const retrievalContextSummary = computed(() => recordValue(retrievalContextOutput.value?.summary))
const retrievalContextItems = computed(() => recordList(retrievalContextOutput.value?.items))
const retrievalContextCoverageLabel = computed(() => {
  const returned = numberValue(retrievalContextSummary.value.returned)
  const total = numberValue(retrievalContextSummary.value.total)
  if (returned !== null && total !== null) return `返回 ${returned} / 共 ${total}`
  if (returned !== null) return `返回 ${returned}`
  if (total !== null) return `共 ${total}`
  return ''
})
const retrievalPrimarySourceLabel = computed(() => {
  const item = retrievalContextItems.value[0]
  if (!item) return ''
  const title = stringValue(item.title) || stringValue(item.source_ref)
  const chapter = chapterIndexLabel(item.chapter_index)
  return [title, chapter].filter(Boolean).join(' · ')
})
const retrievalRecommendedTools = computed(() => stringList(retrievalContextOutput.value?.recommended_next_tools))
const postChapterMemoryOutput = computed(() => latestToolOutput('plan_post_chapter_memory_capture'))
const postChapterMemorySummary = computed(() => recordValue(postChapterMemoryOutput.value?.summary))
const postChapterMemoryChapterLabel = computed(() => chapterIndexLabel(postChapterMemoryOutput.value?.chapter_index))
const postChapterMemoryCaptureStatus = computed(() => stringValue(postChapterMemoryOutput.value?.capture_status))
const postChapterMemoryCandidateCount = computed(() => numberValue(postChapterMemorySummary.value.candidate_count))
const postChapterMemoryReviewStepCount = computed(() => numberValue(postChapterMemorySummary.value.review_step_count))
const postChapterMemoryRecommendedTools = computed(() => stringList(postChapterMemoryOutput.value?.recommended_next_tools))
const hasMemoryLoopProjection = computed(() => Boolean(
  retrievalContextOutput.value || postChapterMemoryOutput.value,
))
const hasRecommendedFollowupPolicy = computed(() => Boolean(
  recommendedFollowupPreview.value &&
  (recommendedFollowupTools.value.length || recommendedFollowupWriteTools.value.length),
))
const runKindLabel = computed(() => {
  if (isRecoveryExecutionRun.value) return '恢复执行'
  if (recoveryPreview.value) return '恢复预览'
  if (recommendedFollowupPreview.value) return '后继预览'
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
const recommendedFollowupExecutePayload = computed(() => {
  const sourceRunId = stringValue(recommendedFollowupPreview.value?.source_run_id)
  const planHash = stringValue(recommendedFollowupPreview.value?.plan_hash)
  if (
    recommendedFollowupTools.value.length &&
    recommendedFollowupExecutionPolicy.value.requires_followup_run === true &&
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

function executeRecommendedFollowups() {
  if (!recommendedFollowupExecutePayload.value) return
  emit('executeRecommendedFollowups', recommendedFollowupExecutePayload.value)
}

function executePlannerPlan() {
  if (!plannerExecutePayload.value) return
  emit('executePlannerPlan', plannerExecutePayload.value)
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
  const displayName = stringValue(agentProfileDefinition.value.display_name)
  if (displayName) return displayName
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

function agentControlPlaneStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可继续编排'
  if (value === 'degraded') return '需检查'
  if (value === 'needs_attention') return '需处理'
  return value || '未知'
}

function plannerIntentLabel(intent: unknown) {
  const value = stringValue(intent)
  if (value === 'setup_project') return '基础设定'
  if (value === 'build_storyline') return '故事线'
  if (value === 'build_outline') return '大纲'
  if (value === 'review_chapter') return '审稿章节'
  if (value === 'continue_next_chapter') return '续写章节'
  if (value === 'recover_blocked_run') return '恢复阻塞'
  if (value === 'inspect_tools') return '工具检查'
  return value || '未知'
}

function plannerStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'completed') return '已完成'
  if (value === 'blocked') return '已阻塞'
  if (value === 'success') return '成功'
  if (value === 'failed') return '失败'
  return value || '未知'
}

function plannerApprovalStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'not_required') return '无需审批'
  if (value === 'requires_confirmation') return '需要审批'
  if (value === 'blocked') return '已阻止'
  return value || '未知'
}

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function profilePolicyAuditLabel(audit: Record<string, unknown>) {
  const status = stringValue(audit.status)
  const summary = recordValue(audit.summary)
  const issueCount = numberValue(summary.issues)
  if (status === 'passed') return '通过'
  if (status === 'needs_attention') {
    return issueCount !== null ? `需关注：${issueCount} 个问题` : '需关注'
  }
  return status
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

function postChapterMemoryCaptureStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可写入候选'
  if (value === 'needs_review') return '需要审稿'
  if (value === 'missing_chapter') return '缺少章节'
  return value || '未知'
}

function recordValue(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {}
}

function recordList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value.filter(isRecord)
}

function latestToolOutput(toolName: string) {
  for (let index = steps.value.length - 1; index >= 0; index -= 1) {
    const step = steps.value[index]
    if (step?.tool_name !== toolName) continue
    const output = recordValue(step.output)
    if (Object.keys(output).length) return output
  }
  return null
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

function stringList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => stringValue(item))
    .filter(Boolean)
}

function toolNameList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => {
      if (typeof item === 'string') return item.trim()
      return stringValue(recordValue(item).tool_name)
    })
    .filter(Boolean)
}

function toolRequestList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value
    .filter(isRecord)
    .filter((item) => Boolean(stringValue(item.tool_name)))
}

function uniqueStrings(values: string[]) {
  return [...new Set(values)]
}

function dependencyList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => {
      if (typeof item === 'string') return { code: item }
      return recordValue(item)
    })
    .filter((item) => Object.keys(item).length > 0)
}

function referencePatternList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value.filter(isRecord)
}

function sourceLinesLabel(value: unknown) {
  const lines = stringList(value)
  return lines.length ? `lines ${lines.join(', ')}` : ''
}

function appliedPatternsLabel(value: unknown) {
  return stringList(value).join(', ')
}

function missingDependencyCode(value: Record<string, unknown>) {
  return stringValue(value.code) || stringValue(value.reason) || 'unknown_dependency'
}

function missingDependencyTool(value: Record<string, unknown>) {
  return stringValue(value.tool_name)
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
            <div v-if="agentProfileTier">
              <dt>编排层级</dt>
              <dd>{{ agentProfileTier }}</dd>
            </div>
            <div v-if="agentProfileDelegationAllowed !== null">
              <dt>委派</dt>
              <dd>{{ agentProfileDelegationAllowed ? '可委派' : '不可委派' }}</dd>
            </div>
            <div v-if="agentProfileDelegateTargetCount > 0">
              <dt>可委派目标</dt>
              <dd>{{ agentProfileDelegateTargetCount }} 个声明</dd>
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
            <div v-if="agentProfilePolicyAuditLabel">
              <dt>策略审计</dt>
              <dd>{{ agentProfilePolicyAuditLabel }}</dd>
            </div>
            <div v-if="hasAgentCommandContracts">
              <dt>命令契约</dt>
              <dd>已投影</dd>
            </div>
            <div v-if="agentControlCommandCount !== null">
              <dt>控制命令</dt>
              <dd>{{ agentControlCommandCount }}</dd>
            </div>
            <div v-if="agentCommandContractGapCount !== null">
              <dt>契约缺口</dt>
              <dd>{{ agentCommandContractGapCount }}</dd>
            </div>
            <div v-if="hasAgentControlPlaneReadiness">
              <dt>控制平面</dt>
              <dd>{{ agentControlPlaneStatusLabel(agentControlPlaneStatus) }}</dd>
            </div>
            <div v-if="agentControlPlaneTotalGapCount !== null">
              <dt>控制面缺口</dt>
              <dd>{{ agentControlPlaneTotalGapCount }}</dd>
            </div>
            <div v-if="agentControlPlaneToolGapCount !== null">
              <dt>工具缺口</dt>
              <dd>{{ agentControlPlaneToolGapCount }}</dd>
            </div>
            <div v-if="agentControlPlaneCommandGapCount !== null">
              <dt>命令缺口</dt>
              <dd>{{ agentControlPlaneCommandGapCount }}</dd>
            </div>
            <div v-if="agentControlPlaneRecommendedCheckCount > 0">
              <dt>建议检查</dt>
              <dd>{{ agentControlPlaneRecommendedCheckCount }}</dd>
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
          v-if="hasPlannerProjection"
          class="agent-run-drawer__planner"
          aria-label="Agent planner projection"
        >
          <h4>Agent 规划投影</h4>
          <dl class="agent-run-drawer__facts">
            <div v-if="plannerIntentClass">
              <dt>意图</dt>
              <dd>{{ plannerIntentLabel(plannerIntentClass) }}</dd>
            </div>
            <div v-if="plannerStatus">
              <dt>规划状态</dt>
              <dd>{{ plannerStatusLabel(plannerStatus) }}</dd>
            </div>
            <div v-if="plannerChapterIndex !== null">
              <dt>章节</dt>
              <dd>{{ chapterIndexLabel(plannerChapterIndex) }}</dd>
            </div>
            <div v-if="plannerVersion">
              <dt>规划器</dt>
              <dd>{{ plannerVersion }}</dd>
            </div>
            <div v-if="plannerApprovalStatus">
              <dt>审批</dt>
              <dd>{{ plannerApprovalStatusLabel(plannerApprovalStatus) }}</dd>
            </div>
            <div v-if="plannerSelectedTools.length">
              <dt>工具链</dt>
              <dd>{{ plannerSelectedTools.length }} 个工具</dd>
            </div>
            <div v-if="plannerRiskFlags.length">
              <dt>风险</dt>
              <dd>{{ plannerRiskFlags.length }} 项</dd>
            </div>
            <div v-if="plannerMissingDependencies.length">
              <dt>缺依赖</dt>
              <dd>{{ plannerMissingDependencies.length }} 项</dd>
            </div>
            <div v-if="plannerReferencePatterns.length">
              <dt>参考模式</dt>
              <dd>{{ plannerReferencePatterns.length }} 个来源</dd>
            </div>
            <div v-if="plannerReferencePatternVersion">
              <dt>模式版本</dt>
              <dd>{{ plannerReferencePatternVersion }}</dd>
            </div>
          </dl>
          <ul
            v-if="plannerSelectedTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="tool in plannerSelectedTools"
              :key="`planner-tool:${tool}`"
            >
              {{ tool }}
            </li>
          </ul>
          <ul
            v-if="plannerRiskFlags.length"
            class="agent-run-drawer__planner-signals"
          >
            <li
              v-for="flag in plannerRiskFlags"
              :key="`planner-risk:${flag}`"
            >
              {{ flag }}
            </li>
          </ul>
          <ul
            v-if="plannerMissingDependencies.length"
            class="agent-run-drawer__planner-signals"
          >
            <li
              v-for="(dependency, index) in plannerMissingDependencies"
              :key="`planner-dependency:${missingDependencyCode(dependency)}:${index}`"
            >
              <strong>{{ missingDependencyCode(dependency) }}</strong>
              <span v-if="missingDependencyTool(dependency)">{{ missingDependencyTool(dependency) }}</span>
            </li>
          </ul>
          <ul
            v-if="plannerReferencePatterns.length"
            class="agent-run-drawer__reference-patterns"
          >
            <li
              v-for="(pattern, index) in plannerReferencePatterns"
              :key="`reference-pattern:${pattern.source || index}`"
            >
              <div>
                <strong>{{ pattern.source || 'unknown-source' }}</strong>
                <span v-if="sourceLinesLabel(pattern.source_lines)">{{ sourceLinesLabel(pattern.source_lines) }}</span>
              </div>
              <p v-if="appliedPatternsLabel(pattern.applied_patterns)">{{ appliedPatternsLabel(pattern.applied_patterns) }}</p>
              <p v-if="pattern.decision">{{ pattern.decision }}</p>
            </li>
          </ul>
          <div v-if="plannerExecutePayload" class="agent-run-drawer__actions">
            <button
              type="button"
              class="agent-run-drawer__execute"
              data-testid="execute-planner-plan"
              @click="executePlannerPlan"
            >
              确认执行规划工具链
            </button>
          </div>
        </section>

        <section
          v-if="hasMemoryLoopProjection"
          class="agent-run-drawer__memory-loop"
          aria-label="Agent memory loop"
        >
          <h4>Agent 记忆闭环</h4>
          <dl class="agent-run-drawer__facts">
            <div v-if="retrievalContextCoverageLabel">
              <dt>检索证据</dt>
              <dd>{{ retrievalContextCoverageLabel }}</dd>
            </div>
            <div v-if="retrievalPrimarySourceLabel">
              <dt>检索来源</dt>
              <dd>{{ retrievalPrimarySourceLabel }}</dd>
            </div>
            <div v-if="postChapterMemoryOutput">
              <dt>写后记忆</dt>
              <dd>{{ postChapterMemoryChapterLabel }} {{ postChapterMemoryCaptureStatusLabel(postChapterMemoryCaptureStatus) }}</dd>
            </div>
            <div v-if="postChapterMemoryCandidateCount !== null">
              <dt>候选</dt>
              <dd>候选 {{ postChapterMemoryCandidateCount }}</dd>
            </div>
            <div v-if="postChapterMemoryReviewStepCount !== null">
              <dt>审稿</dt>
              <dd>审稿证据 {{ postChapterMemoryReviewStepCount }}</dd>
            </div>
          </dl>
          <ul
            v-if="retrievalRecommendedTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="tool in retrievalRecommendedTools"
              :key="`retrieval-next:${tool}`"
            >
              {{ tool }}
            </li>
          </ul>
          <ul
            v-if="postChapterMemoryRecommendedTools.length"
            class="agent-run-drawer__write-tools"
          >
            <li
              v-for="tool in postChapterMemoryRecommendedTools"
              :key="`post-memory-next:${tool}`"
            >
              {{ tool }}
            </li>
          </ul>
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
          v-if="hasRecommendedFollowupPolicy"
          class="agent-run-drawer__followups"
          aria-label="Recommended follow-up policy"
        >
          <h4>推荐后继策略</h4>
          <dl class="agent-run-drawer__facts">
            <div>
              <dt>自动诊断工具</dt>
              <dd>{{ recommendedFollowupTools.length }} 个</dd>
            </div>
            <div>
              <dt>需确认修复</dt>
              <dd>{{ recommendedFollowupWriteTools.length }} 个</dd>
            </div>
          </dl>
          <ul
            v-if="recommendedFollowupTools.length"
            class="agent-run-drawer__tools"
          >
            <li
              v-for="(tool, index) in recommendedFollowupTools"
              :key="`followup:${tool.tool_name || 'tool'}:${index}`"
            >
              {{ tool.tool_name }}
            </li>
          </ul>
          <ul
            v-if="recommendedFollowupWriteTools.length"
            class="agent-run-drawer__write-tools"
          >
            <li
              v-for="(tool, index) in recommendedFollowupWriteTools"
              :key="`write:${tool.tool_name || 'tool'}:${index}`"
            >
              {{ tool.tool_name }}
            </li>
          </ul>
          <div v-if="recommendedFollowupExecutePayload" class="agent-run-drawer__actions">
            <button
              type="button"
              class="agent-run-drawer__execute"
              data-testid="execute-recommended-followups"
              @click="executeRecommendedFollowups"
            >
              确认执行后继
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
.agent-run-drawer__planner h4,
.agent-run-drawer__memory-loop h4,
.agent-run-drawer__recovery h4,
.agent-run-drawer__followups h4,
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

.agent-run-drawer__planner {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__memory-loop {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__recovery {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__followups {
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
.agent-run-drawer__tools,
.agent-run-drawer__write-tools,
.agent-run-drawer__planner-signals,
.agent-run-drawer__reference-patterns {
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

.agent-run-drawer__reference-patterns li {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
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

.agent-run-drawer__write-tools li {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-warning);
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
