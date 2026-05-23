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
