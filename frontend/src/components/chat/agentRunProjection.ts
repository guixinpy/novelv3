import type { ActionResultView, WritingAgentRunDetail } from '../../api/types'

export const AGENT_RUN_ACTION_TYPES = ['plan_recovery_tools', 'ui_recovery_execute'] as const

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
  return typeof value === 'string' && AGENT_RUN_ACTION_TYPES.includes(value as typeof AGENT_RUN_ACTION_TYPES[number])
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
  return typeof dataRunId === 'string' ? dataRunId.trim() : ''
}

export function buildAgentRunActionResultView(actionResult: Record<string, unknown> | null | undefined): ActionResultView | null {
  if (!actionResult) return null
  const actionType = stringValue(actionResult.type)
  const status = stringValue(actionResult.status)
  if (!actionType || !status || !isAgentRunActionType(actionType)) return null
  if (actionType === 'plan_recovery_tools') {
    const detailItems = recoveryPreviewDetailItems(recordValue(actionResult.data))
    return {
      type: actionType,
      status,
      label: recoveryPreviewLabel(status),
      variant: statusVariant(status),
      ...(detailItems.length ? { detail_items: detailItems } : {}),
    }
  }
  if (actionType === 'ui_recovery_execute') {
    const data = recordValue(actionResult.data)
    const runId = stringValue(data.agent_run_id)
    return {
      type: actionType,
      status,
      label: recoveryExecutionStatusLabel(status),
      variant: recoveryExecutionVariant(status),
      ...(runId ? { detail_items: [{ label: '运行 ID', value: runId }] } : {}),
    }
  }
  return null
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

function recoveryPreviewLabel(status: string) {
  if (status === 'success' || status === 'completed') return '恢复预览已生成'
  if (status === 'failed') return '恢复预览失败'
  return `恢复预览: ${status || '未知状态'}`
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
  return items
}

function recoveryStatusLabel(status: string) {
  if (status === 'recommended') return '建议恢复'
  if (status === 'none') return '无恢复建议'
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

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
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
