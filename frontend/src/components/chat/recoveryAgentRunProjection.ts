import type { ActionResultView, WritingAgentRunDetail } from '../../api/types'

export const RECOVERY_AGENT_RUN_ACTION_TYPES = [
  'plan_recovery_tools',
  'plan_recommended_followups',
  'ui_recovery_execute',
  'ui_recommended_followup_execute',
] as const

export type RecoveryAgentRunActionType = typeof RECOVERY_AGENT_RUN_ACTION_TYPES[number]

export interface RecoveryAgentRunActionDescriptor {
  type: RecoveryAgentRunActionType
  buildView: (actionResult: Record<string, unknown>, status: string) => ActionResultView
}

export interface AgentRunFeedbackMessage {
  role: 'system'
  content: string
  action_result: {
    type: 'ui_recovery_execute' | 'ui_recommended_followup_execute'
    status: string
    data: { agent_run_id: string }
  }
  action_result_view: ActionResultView
  meta: {
    agent_run_id: string
    agent_action_type: 'ui_recovery_execute' | 'ui_recommended_followup_execute'
  }
}

export const RECOVERY_AGENT_RUN_ACTION_DESCRIPTORS: Record<RecoveryAgentRunActionType, RecoveryAgentRunActionDescriptor> = {
  plan_recovery_tools: {
    type: 'plan_recovery_tools',
    buildView: buildRecoveryPreviewActionResultView,
  },
  plan_recommended_followups: {
    type: 'plan_recommended_followups',
    buildView: buildRecommendedFollowupPreviewActionResultView,
  },
  ui_recovery_execute: {
    type: 'ui_recovery_execute',
    buildView: buildRecoveryExecutionActionResultView,
  },
  ui_recommended_followup_execute: {
    type: 'ui_recommended_followup_execute',
    buildView: buildRecommendedFollowupExecutionActionResultView,
  },
}

export function buildAgentRunExecutionFeedback(run: WritingAgentRunDetail): AgentRunFeedbackMessage {
  const status = String(run.status || '')
  const label = recoveryExecutionStatusLabel(status)
  const detailItems = [
    { label: '运行 ID', value: run.id },
    { label: '状态', value: recoveryExecutionDetailStatusLabel(status) },
  ]
  const errorSummary = typeof run.error === 'string' ? run.error.trim() : ''
  if (errorSummary) {
    detailItems.push({ label: '错误摘要', value: errorSummary })
  }
  detailItems.push(...agentDiscoveryDetailItems(run as unknown as Record<string, unknown>))
  return {
    role: 'system',
    content: '恢复执行已创建，可在运行详情中查看执行步骤。',
    action_result: {
      type: 'ui_recovery_execute',
      status,
      data: { agent_run_id: run.id },
    },
    action_result_view: {
      type: 'ui_recovery_execute',
      status,
      label,
      variant: recoveryExecutionVariant(status),
      detail_items: detailItems,
    },
    meta: {
      agent_run_id: run.id,
      agent_action_type: 'ui_recovery_execute',
    },
  }
}

function recommendedFollowupExecutionDetailItems(run: WritingAgentRunDetail) {
  const steps = Array.isArray(run.steps) ? run.steps : []
  const items: Array<{ label: string; value: string }> = []
  if (steps.length) {
    items.push({ label: '执行步骤', value: `${steps.length} 个` })
  }
  const toolNames = uniqueStrings(steps.map((step) => stringValue(step.tool_name)).filter(Boolean))
  if (toolNames.length) {
    items.push({ label: '执行工具', value: compactToolList(toolNames) })
  }
  const nextFollowups = latestStepCanonicalFollowups(steps)
  if (nextFollowups.length) {
    items.push({ label: '后继建议', value: `${nextFollowups.length} 项` })
  }
  return items
}

export function buildRecommendedFollowupExecutionFeedback(run: WritingAgentRunDetail): AgentRunFeedbackMessage {
  const status = String(run.status || '')
  const label = recommendedFollowupExecutionStatusLabel(status)
  const detailItems = [
    { label: '运行 ID', value: run.id },
    { label: '状态', value: recoveryExecutionDetailStatusLabel(status) },
  ]
  const errorSummary = typeof run.error === 'string' ? run.error.trim() : ''
  if (errorSummary) {
    detailItems.push({ label: '错误摘要', value: errorSummary })
  }
  detailItems.push(...recommendedFollowupExecutionDetailItems(run))
  detailItems.push(...agentDiscoveryDetailItems(run as unknown as Record<string, unknown>))
  return {
    role: 'system',
    content: '推荐后继执行已创建，可在运行详情中查看执行步骤。',
    action_result: {
      type: 'ui_recommended_followup_execute',
      status,
      data: { agent_run_id: run.id },
    },
    action_result_view: {
      type: 'ui_recommended_followup_execute',
      status,
      label,
      variant: recoveryExecutionVariant(status),
      detail_items: detailItems,
    },
    meta: {
      agent_run_id: run.id,
      agent_action_type: 'ui_recommended_followup_execute',
    },
  }
}

function recoveryExecutionStatusLabel(status: string) {
  if (status === 'success') return '恢复执行已完成'
  if (status === 'failed') return '恢复执行失败'
  if (status === 'running') return '恢复执行中'
  if (status === 'blocked') return '恢复执行已阻止'
  return `恢复执行已创建：${status || '未知状态'}`
}

function recommendedFollowupExecutionStatusLabel(status: string) {
  if (status === 'success') return '推荐后继执行已完成'
  if (status === 'failed') return '推荐后继执行失败'
  if (status === 'running') return '推荐后继执行中'
  if (status === 'blocked') return '推荐后继执行已阻止'
  return `推荐后继执行已创建：${status || '未知状态'}`
}

function buildRecoveryPreviewActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const detailItems = recoveryPreviewDetailItems(recordValue(actionResult.data))
  return {
    type: 'plan_recovery_tools',
    status,
    label: recoveryPreviewLabel(status),
    variant: statusVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildRecommendedFollowupPreviewActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const detailItems = recommendedFollowupPreviewDetailItems(recordValue(actionResult.data))
  return {
    type: 'plan_recommended_followups',
    status,
    label: recommendedFollowupPreviewLabel(status),
    variant: statusVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildRecoveryExecutionActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const runId = stringValue(data.agent_run_id)
  const detailItems = [
    ...(runId ? [{ label: '运行 ID', value: runId }] : []),
    ...agentDiscoveryDetailItems(data),
  ]
  return {
    type: 'ui_recovery_execute',
    status,
    label: recoveryExecutionStatusLabel(status),
    variant: recoveryExecutionVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildRecommendedFollowupExecutionActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const runId = stringValue(data.agent_run_id)
  const detailItems = [
    ...(runId ? [{ label: '运行 ID', value: runId }] : []),
    ...agentDiscoveryDetailItems(data),
  ]
  return {
    type: 'ui_recommended_followup_execute',
    status,
    label: recommendedFollowupExecutionStatusLabel(status),
    variant: recoveryExecutionVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function recoveryPreviewLabel(status: string) {
  if (status === 'success' || status === 'completed') return '恢复预览已生成'
  if (status === 'failed') return '恢复预览失败'
  return `恢复预览: ${status || '未知状态'}`
}

function recommendedFollowupPreviewLabel(status: string) {
  if (status === 'success' || status === 'completed') return '推荐后继预览已生成'
  if (status === 'failed') return '推荐后继预览失败'
  return `推荐后继预览: ${status || '未知状态'}`
}

function statusVariant(status: string) {
  if (status === 'success' || status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  return 'neutral'
}

function recoveryPreviewDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const sourceRunId = stringValue(data.source_run_id)
  if (sourceRunId) {
    items.push({ label: '来源运行', value: sourceRunId.slice(0, 8) })
  }
  items.push(...dialogRouteDecisionDetailItems(data))

  const recovery = recordValue(data.recovery)
  const recoveryStatus = stringValue(recovery.status)
  if (recoveryStatus) {
    items.push({ label: '恢复状态', value: recoveryStatusLabel(recoveryStatus) })
  }

  const executionPolicy = recordValue(data.execution_policy)
  const policyStatus = stringValue(executionPolicy.status)
  if (policyStatus) {
    items.push({ label: '执行策略', value: executionPolicyLabel(policyStatus) })
  }

  const tools = Array.isArray(data.tools) ? data.tools : []
  if (tools.length) {
    items.push({ label: '恢复工具', value: `${tools.length} 个` })
  }
  items.push(...agentDiscoveryDetailItems(data))
  return items
}

function recommendedFollowupPreviewDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const sourceRunId = stringValue(data.source_run_id)
  if (sourceRunId) {
    items.push({ label: '来源运行', value: sourceRunId.slice(0, 8) })
  }
  items.push(...dialogRouteDecisionDetailItems(data))

  const followups = recordValue(data.recommended_followups)
  const followupStatus = stringValue(followups.status)
  if (followupStatus) {
    items.push({ label: '推荐状态', value: recommendedFollowupStatusLabel(followupStatus) })
  }

  const tools = Array.isArray(data.tools) ? data.tools : []
  if (tools.length) {
    items.push({ label: '自动后继', value: `${tools.length} 个` })
    const toolSummary = toolNameSummary(tools)
    if (toolSummary) {
      items.push({ label: '后继工具', value: toolSummary })
    }
  }
  items.push(...workerDispatchDetailItems(data))

  const continuationTools = Array.isArray(followups.post_approval_continuation_tools)
    ? followups.post_approval_continuation_tools
    : []
  if (continuationTools.length) {
    items.push({ label: '写后续跑', value: `${continuationTools.length} 个工具` })
  }

  const writeTools = Array.isArray(followups.provenance_write_tools) ? followups.provenance_write_tools : []
  if (writeTools.length) {
    items.push({ label: '需确认修复', value: `${writeTools.length} 个` })
  }
  items.push(...agentDiscoveryDetailItems(data))
  return items
}

function workerDispatchDetailItems(data: Record<string, unknown>) {
  const dispatch = recordValue(data.worker_dispatch)
  const summary = recordValue(dispatch.summary)
  const routeRegistry = recordValue(dispatch.route_registry)
  const routeRegistrySummary = recordValue(routeRegistry.summary)
  const items: Array<{ label: string; value: string }> = []
  const workerCount = numberValue(summary.workers)
  if (workerCount !== null) {
    items.push({ label: 'Worker 分派', value: `${workerCount} 个 worker` })
  }
  const workerSummary = workerDispatchSummary(dispatch)
  if (workerSummary) {
    items.push({ label: '分派 Worker', value: workerSummary })
  }
  const plannedTasks = numberValue(summary.planned_tasks)
  if (plannedTasks !== null) {
    items.push({ label: '分派任务', value: `${plannedTasks} 个任务` })
  }
  const blockedTasks = numberValue(summary.blocked_tasks)
  if (blockedTasks !== null && blockedTasks > 0) {
    items.push({ label: '分派阻塞', value: `${blockedTasks} 个` })
  }
  const issueCount = numberValue(summary.issues)
  if (issueCount !== null && issueCount > 0) {
    items.push({ label: '分派问题', value: `${issueCount} 个` })
  }
  const routeRegistryStatus = stringValue(routeRegistry.status)
  if (routeRegistryStatus) {
    items.push({ label: '路由审计', value: routeRegistryStatusLabel(routeRegistryStatus) })
  }
  const unroutedAllowedTools = numberValue(routeRegistrySummary.unrouted_allowed_tools)
  if (unroutedAllowedTools !== null) {
    items.push({ label: '未路由工具', value: `${unroutedAllowedTools} 个` })
  }
  const routeIssueCount = numberValue(routeRegistrySummary.issues)
  if (routeIssueCount !== null && routeIssueCount > 0) {
    items.push({ label: '路由问题', value: `${routeIssueCount} 个` })
  }
  return items
}

function toolNameSummary(tools: unknown[]) {
  const names = tools
    .map((tool) => {
      if (typeof tool === 'string') return tool.trim()
      return stringValue(recordValue(tool).tool_name)
    })
    .filter(Boolean)
  return compactUniqueLabel(names)
}

function workerDispatchSummary(dispatch: Record<string, unknown>) {
  const dispatches = Array.isArray(dispatch.worker_dispatches) ? dispatch.worker_dispatches : []
  const names = dispatches
    .map((item) => agentProfileLabel(stringValue(recordValue(recordValue(item).worker).name)))
    .filter(Boolean)
  return compactUniqueLabel(names)
}

function compactUniqueLabel(values: string[], limit = 3) {
  const uniqueValues = [...new Set(values.filter(Boolean))]
  if (!uniqueValues.length) return ''
  if (uniqueValues.length <= limit) return uniqueValues.join(', ')
  return `${uniqueValues.slice(0, limit).join(', ')} 等 ${uniqueValues.length} 个`
}

function dialogRouteDecisionDetailItems(data: Record<string, unknown>) {
  const decision = recordValue(data.route_decision)
  const items: Array<{ label: string; value: string }> = []
  const selectedRoute = stringValue(decision.selected_route)
  if (selectedRoute) {
    items.push({ label: '继续路由', value: dialogRouteLabel(selectedRoute) })
  }
  const reasonCode = stringValue(decision.reason_code)
  if (reasonCode) {
    items.push({ label: '路由原因', value: dialogRouteReasonLabel(reasonCode) })
  }
  return items
}

function agentDiscoveryDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const definition = recordValue(data.agent_profile_definition)
  const discovery = recordValue(data.agent_tool_discovery)
  const profile = stringValue(data.agent_profile) || stringValue(discovery.effective_profile) || stringValue(definition.profile)
  const displayName = stringValue(definition.display_name)
  if (displayName || profile) {
    items.push({ label: 'Agent 身份', value: displayName || agentProfileLabel(profile) })
  }

  const role = stringValue(definition.role)
  if (role) {
    items.push({ label: 'Agent 角色', value: agentRoleLabel(role) })
  }

  const tier = stringValue(definition.tier)
  if (tier) {
    items.push({ label: '编排层级', value: tier })
  }

  const delegation = delegationLabel(definition.delegation_allowed)
  if (delegation) {
    items.push({ label: '委派', value: delegation })
  }

  const delegateTargets = Array.isArray(definition.delegate_to_profiles) ? definition.delegate_to_profiles : []
  if (definition.delegation_allowed === true && delegateTargets.length) {
    items.push({ label: '可委派目标', value: `${delegateTargets.length} 个声明` })
  }

  const scopeStatus = stringValue(discovery.status) || (discovery.scope_applied === true ? 'applied' : '')
  if (scopeStatus) {
    items.push({ label: '工具面', value: agentToolScopeStatusLabel(scopeStatus) })
  }

  const visibleToolCount = numberValue(discovery.visible_tool_count)
  if (visibleToolCount !== null) {
    items.push({ label: '可见工具', value: `${visibleToolCount} 个` })
  }

  const filteredCount = numberValue(discovery.filtered_by_profile_count)
  if (filteredCount !== null) {
    items.push({ label: '已过滤', value: `${filteredCount} 个` })
  }

  const policyAuditLabel = profilePolicyAuditLabel(recordValue(data.agent_profile_policy_audit))
  if (policyAuditLabel) {
    items.push({ label: '策略审计', value: policyAuditLabel })
  }
  items.push(...agentCommandContractDetailItems(data))
  items.push(...agentControlPlaneReadinessDetailItems(data))
  return items
}

function agentCommandContractDetailItems(data: Record<string, unknown>) {
  const contracts = recordValue(data.agent_command_contracts)
  return commandContractDetailItems(contracts)
}

function commandContractDetailItems(contracts: Record<string, unknown>) {
  const summary = recordValue(contracts.summary)
  const items: Array<{ label: string; value: string }> = []
  if (!Object.keys(summary).length) return items

  items.push({ label: '命令契约', value: '已投影' })
  const controlCommands = numberValue(summary.agent_control_commands)
  if (controlCommands !== null) {
    items.push({ label: '控制命令', value: `${controlCommands} 个` })
  }
  const gapCount = numberValue(summary.gap_count)
  if (gapCount !== null) {
    items.push({ label: '契约缺口', value: `${gapCount} 个` })
  }
  return items
}

function agentControlPlaneReadinessDetailItems(data: Record<string, unknown>) {
  const readiness = recordValue(data.agent_control_plane_readiness)
  return controlPlaneReadinessDetailItems(readiness)
}

function controlPlaneReadinessDetailItems(readiness: Record<string, unknown>) {
  const summary = recordValue(readiness.summary)
  const items: Array<{ label: string; value: string }> = []
  if (!Object.keys(summary).length) return items

  items.push({ label: '控制平面', value: agentControlPlaneStatusLabel(stringValue(readiness.status)) })
  const totalGapCount = numberValue(summary.total_gap_count)
  if (totalGapCount !== null) {
    items.push({ label: '控制面缺口', value: `${totalGapCount} 个` })
  }
  const toolGapCount = numberValue(summary.tool_gap_count)
  if (toolGapCount !== null) {
    items.push({ label: '工具缺口', value: `${toolGapCount} 个` })
  }
  const commandGapCount = numberValue(summary.command_gap_count)
  if (commandGapCount !== null) {
    items.push({ label: '命令缺口', value: `${commandGapCount} 个` })
  }
  const recommendedNextTools = Array.isArray(readiness.recommended_next_tools)
    ? readiness.recommended_next_tools
    : []
  if (recommendedNextTools.length) {
    items.push({ label: '建议检查', value: `${recommendedNextTools.length} 项` })
  }
  return items
}

function agentControlPlaneStatusLabel(status: string) {
  if (status === 'ready') return '可继续编排'
  if (status === 'degraded') return '需检查'
  if (status === 'needs_attention') return '需处理'
  return status || '未知'
}

function routeRegistryStatusLabel(status: string) {
  if (status === 'passed') return '通过'
  if (status === 'needs_attention') return '需处理'
  return status || '未知'
}

function recoveryStatusLabel(status: string) {
  if (status === 'recommended') return '建议恢复'
  if (status === 'none') return '无恢复建议'
  return status
}

function recommendedFollowupStatusLabel(status: string) {
  if (status === 'recommended') return '已推荐'
  if (status === 'none') return '无推荐'
  return status
}

function dialogRouteLabel(route: string) {
  if (route === 'recover_blocked_run') return '恢复阻塞运行'
  if (route === 'recommended_followups') return '推荐后继'
  if (route === 'chapter_generation') return '继续章节生成'
  return route
}

function dialogRouteReasonLabel(reasonCode: string) {
  if (reasonCode === 'recoverable_run_found') return '发现可恢复运行'
  if (reasonCode === 'recommended_followups_found') return '发现上一轮推荐后继'
  if (reasonCode === 'no_recovery_or_followup') return '无恢复或后继，继续章节生成'
  return reasonCode
}

function executionPolicyLabel(status: string) {
  if (status === 'ready') return '可执行'
  if (status === 'confirmation_required') return '等待确认'
  if (status === 'not_executable') return '不可执行'
  if (status === 'repeat_failed_recovery') return '重复失败保护'
  if (status === 'requires_user_input') return '需要用户补充输入'
  return status
}

function agentProfileLabel(profile: string) {
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

function agentRoleLabel(role: string) {
  if (role === 'orchestrator') return 'orchestrator'
  if (role === 'worker') return 'worker'
  return role || '未知'
}

function delegationLabel(value: unknown) {
  if (value === true) return '可委派'
  if (value === false) return '不可委派'
  return ''
}

function agentToolScopeStatusLabel(status: string) {
  if (status === 'applied') return '已按身份收窄'
  if (status === 'not_requested') return '未请求身份收窄'
  if (status === 'unknown_profile') return '未知身份，已拒绝工具面'
  if (status === 'not_available') return '暂无工具面摘要'
  return status || '未知'
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

function latestStepCanonicalFollowups(steps: WritingAgentRunDetail['steps']) {
  for (let index = steps.length - 1; index >= 0; index -= 1) {
    const output = recordValue(steps[index]?.output)
    const envelope = recordValue(output.agent_tool_result)
    const recommendations = recordValue(envelope.recommendations)
    const followups = Array.isArray(recommendations.canonical_followups)
      ? recommendations.canonical_followups
      : []
    const normalized = uniqueStrings(followups.map((item) => stringValue(item)).filter(Boolean))
    if (normalized.length) return normalized
  }
  return []
}

function uniqueStrings(values: string[]) {
  return Array.from(new Set(values))
}

function compactToolList(values: string[]) {
  const visible = values.slice(0, 3)
  const hidden = values.length - visible.length
  return hidden > 0 ? `${visible.join(', ')}, +${hidden}` : visible.join(', ')
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
}

function numberValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function recoveryExecutionDetailStatusLabel(status: string) {
  if (status === 'success') return '已完成'
  if (status === 'failed') return '失败'
  if (status === 'running') return '执行中'
  if (status === 'blocked') return '已阻止'
  return status || '未知'
}

function recoveryExecutionVariant(status: string) {
  if (status === 'success') return 'success'
  if (status === 'failed' || status === 'blocked') return 'error'
  return 'neutral'
}
