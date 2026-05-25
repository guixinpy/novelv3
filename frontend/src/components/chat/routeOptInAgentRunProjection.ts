import type { ActionResultView } from '../../api/types'

export const ROUTE_OPT_IN_AGENT_RUN_ACTION_TYPES = [
  'prepare_route_upgrade_contract',
  'preview_pending_action_route_approval_opt_in_apply_contract',
  'apply_pending_action_route_approval_opt_in',
] as const

export type RouteOptInAgentRunActionType = typeof ROUTE_OPT_IN_AGENT_RUN_ACTION_TYPES[number]

export interface RouteOptInAgentRunActionDescriptor {
  type: RouteOptInAgentRunActionType
  buildView: (actionResult: Record<string, unknown>, status: string) => ActionResultView
}

export const ROUTE_OPT_IN_AGENT_RUN_ACTION_DESCRIPTORS: Record<RouteOptInAgentRunActionType, RouteOptInAgentRunActionDescriptor> = {
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

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
}
