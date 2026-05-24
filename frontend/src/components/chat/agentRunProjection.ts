import type { ActionResultView, WritingAgentRunDetail } from '../../api/types'
import {
  LONGFORM_AGENT_RUN_ACTION_DESCRIPTORS,
  LONGFORM_AGENT_RUN_ACTION_TYPES,
} from './longformAgentRunProjection'

export const AGENT_RUN_ACTION_TYPES = [
  'plan_recovery_tools',
  'ui_recovery_execute',
  'inspect_agent_trace_audit',
  'prepare_route_upgrade_contract',
  'preview_pending_action_route_approval_opt_in_apply_contract',
  'apply_pending_action_route_approval_opt_in',
  ...LONGFORM_AGENT_RUN_ACTION_TYPES,
] as const
export type AgentRunActionType = typeof AGENT_RUN_ACTION_TYPES[number]

export interface AgentRunActionDescriptor {
  type: AgentRunActionType
  buildView: (actionResult: Record<string, unknown>, status: string) => ActionResultView
}

const AGENT_RUN_ACTION_DESCRIPTORS: Record<AgentRunActionType, AgentRunActionDescriptor> = {
  plan_recovery_tools: {
    type: 'plan_recovery_tools',
    buildView: buildRecoveryPreviewActionResultView,
  },
  ui_recovery_execute: {
    type: 'ui_recovery_execute',
    buildView: buildRecoveryExecutionActionResultView,
  },
  inspect_agent_trace_audit: {
    type: 'inspect_agent_trace_audit',
    buildView: buildTraceAuditActionResultView,
  },
  prepare_route_upgrade_contract: {
    type: 'prepare_route_upgrade_contract',
    buildView: buildRouteOptInContractActionResultView,
  },
  preview_pending_action_route_approval_opt_in_apply_contract: {
    type: 'preview_pending_action_route_approval_opt_in_apply_contract',
    buildView: buildRouteOptInContractActionResultView,
  },
  apply_pending_action_route_approval_opt_in: {
    type: 'apply_pending_action_route_approval_opt_in',
    buildView: buildRouteOptInApplyActionResultView,
  },
  ...LONGFORM_AGENT_RUN_ACTION_DESCRIPTORS,
}

interface AgentRunMessageLike {
  action_result?: Record<string, unknown> | null
  action_result_view?: Partial<ActionResultView> | null
  meta?: Record<string, unknown> | null
}

export interface AgentRunFeedbackMessage {
  role: 'system'
  content: string
  action_result: {
    type: 'ui_recovery_execute'
    status: string
    data: { agent_run_id: string }
  }
  action_result_view: ActionResultView
  meta: {
    agent_run_id: string
    agent_action_type: 'ui_recovery_execute'
  }
}

export function isAgentRunActionType(value: unknown) {
  return Boolean(getAgentRunActionDescriptor(value))
}

export function getAgentRunActionDescriptor(value: unknown): AgentRunActionDescriptor | null {
  if (typeof value !== 'string') return null
  return AGENT_RUN_ACTION_DESCRIPTORS[value as AgentRunActionType] || null
}

export function getAgentRunIdFromMessage(message: AgentRunMessageLike) {
  const actionType = String(
    message.action_result_view?.type
    || message.action_result?.type
    || message.meta?.agent_action_type
    || '',
  )
  if (!isAgentRunActionType(actionType)) return ''
  const metaRunId = message.meta?.agent_run_id
  if (typeof metaRunId === 'string' && metaRunId.trim()) return metaRunId.trim()
  const data = message.action_result?.data
  if (!data || typeof data !== 'object') return ''
  const dataRunId = (data as Record<string, unknown>).agent_run_id
  if (typeof dataRunId === 'string' && dataRunId.trim()) return dataRunId.trim()
  const run = recordValue((data as Record<string, unknown>).run)
  return stringValue(run.id)
}

export function buildAgentRunActionResultView(actionResult: Record<string, unknown> | null | undefined): ActionResultView | null {
  if (!actionResult) return null
  const actionType = stringValue(actionResult.type)
  const status = stringValue(actionResult.status)
  const descriptor = getAgentRunActionDescriptor(actionType)
  if (!descriptor || !status) return null
  return descriptor.buildView(actionResult, status)
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

function recoveryExecutionStatusLabel(status: string) {
  if (status === 'success') return '恢复执行已完成'
  if (status === 'failed') return '恢复执行失败'
  if (status === 'running') return '恢复执行中'
  if (status === 'blocked') return '恢复执行已阻止'
  return `恢复执行已创建：${status || '未知状态'}`
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

function buildTraceAuditActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const detailItems = traceAuditDetailItems(recordValue(actionResult.data))
  return {
    type: 'inspect_agent_trace_audit',
    status,
    label: traceAuditLabel(status),
    variant: statusVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildRouteOptInContractActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const routeStatus = stringValue(data.status) || status
  const detailItems = routeOptInContractDetailItems(data)
  const actionType = stringValue(actionResult.type) || 'preview_pending_action_route_approval_opt_in_apply_contract'
  return {
    type: actionType,
    status,
    label: routeOptInContractLabel(routeStatus),
    variant: routeStatus === 'blocked' ? 'error' : 'neutral',
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildRouteOptInApplyActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const applyStatus = stringValue(data.status) || status
  const detailItems = routeOptInApplyDetailItems(data)
  return {
    type: 'apply_pending_action_route_approval_opt_in',
    status,
    label: routeOptInApplyLabel(applyStatus),
    variant: applyStatus === 'success' ? 'success' : applyStatus === 'blocked' || applyStatus === 'failed' ? 'error' : 'neutral',
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function recoveryPreviewLabel(status: string) {
  if (status === 'success' || status === 'completed') return '恢复预览已生成'
  if (status === 'failed') return '恢复预览失败'
  return `恢复预览: ${status || '未知状态'}`
}

function traceAuditLabel(status: string) {
  if (status === 'success' || status === 'completed') return 'Trace 审计已生成'
  if (status === 'failed') return 'Trace 审计失败'
  if (status === 'running') return 'Trace 审计中'
  return `Trace 审计: ${status || '未知状态'}`
}

function routeOptInContractLabel(status: string) {
  if (status === 'requires_confirmation') return '路由升级契约待确认'
  if (status === 'blocked') return '路由升级契约已阻塞'
  if (status === 'not_required') return '路由升级无需处理'
  return `路由升级契约: ${status || '未知状态'}`
}

function routeOptInApplyLabel(status: string) {
  if (status === 'success') return '路由升级已应用'
  if (status === 'blocked') return '路由升级应用已阻塞'
  if (status === 'failed') return '路由升级应用失败'
  return `路由升级应用: ${status || '未知状态'}`
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
  return items
}

function traceAuditDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const run = recordValue(data.run)
  const runStatus = stringValue(run.status)
  if (runStatus) {
    items.push({ label: '运行状态', value: runStatusLabel(runStatus) })
  }

  const audit = recordValue(data.audit)
  const stepCount = numberValue(audit.step_count)
  if (stepCount !== null) {
    items.push({ label: '工具步骤', value: `${stepCount} 个` })
  }
  const traceCount = numberValue(audit.trace_count)
  if (traceCount !== null) {
    items.push({ label: 'Trace', value: `${traceCount} 条` })
  }

  const failure = recordValue(data.failure)
  const reasonCode = stringValue(failure.reason_code)
  if (reasonCode) {
    items.push({ label: '失败原因', value: reasonCode })
  }

  const recommendedActions = Array.isArray(data.recommended_actions) ? data.recommended_actions : []
  if (recommendedActions.length) {
    items.push({ label: '建议动作', value: `${recommendedActions.length} 个` })
  }
  return items
}

function routeOptInContractDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const contractStatus = stringValue(data.status)
  if (contractStatus) {
    items.push({ label: '契约状态', value: routeOptInContractStatusLabel(contractStatus) })
  }
  const requiredConfirmation = data.required_confirmation
  if (typeof requiredConfirmation === 'boolean') {
    items.push({ label: '需要确认', value: requiredConfirmation ? '是' : '否' })
  }
  const risk = recordValue(data.risk)
  const riskCodes = Array.isArray(risk.codes) ? risk.codes : []
  if (riskCodes.length) {
    items.push({ label: '风险项', value: `${riskCodes.length} 项` })
  }
  const recommendedTools = Array.isArray(data.recommended_next_tools) ? data.recommended_next_tools : []
  if (recommendedTools.length) {
    items.push({ label: '下一步', value: `${recommendedTools.length} 个工具` })
  }
  return items
}

function routeOptInApplyDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const applyStatus = stringValue(data.status)
  if (applyStatus) {
    items.push({ label: '应用状态', value: routeOptInApplyStatusLabel(applyStatus) })
  }
  if (typeof data.write_performed === 'boolean') {
    items.push({ label: '写入结果', value: data.write_performed ? '已写入' : '未写入' })
  }
  const reason = stringValue(data.reason)
  if (reason) {
    items.push({ label: '原因', value: reason })
  }
  const sideEffects = recordValue(data.side_effects)
  const executed = Array.isArray(sideEffects.executed) ? sideEffects.executed : []
  if (executed.length) {
    items.push({ label: '副作用', value: `${executed.length} 项` })
  }
  const recommendedTools = Array.isArray(data.recommended_next_tools) ? data.recommended_next_tools : []
  if (recommendedTools.length) {
    items.push({ label: '下一步', value: `${recommendedTools.length} 个工具` })
  }
  return items
}

function runStatusLabel(status: string) {
  if (status === 'success') return '成功'
  if (status === 'failed') return '失败'
  if (status === 'running') return '运行中'
  if (status === 'blocked') return '已阻止'
  return status
}

function recoveryStatusLabel(status: string) {
  if (status === 'recommended') return '建议恢复'
  if (status === 'none') return '无恢复建议'
  return status
}

function routeOptInContractStatusLabel(status: string) {
  if (status === 'requires_confirmation') return '等待确认'
  if (status === 'blocked') return '已阻塞'
  if (status === 'not_required') return '无需处理'
  return status
}

function routeOptInApplyStatusLabel(status: string) {
  if (status === 'success') return '成功'
  if (status === 'blocked') return '已阻塞'
  if (status === 'failed') return '失败'
  return status
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
  if (profile === 'world_model_worker') return '世界模型执行者'
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
