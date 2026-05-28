import type { ActionResultView, WritingAgentRunDetail } from '../../api/types'

export const PLANNER_AGENT_RUN_ACTION_TYPES = [
  'ui_planner_continuation_execute',
] as const

export type PlannerAgentRunActionType = typeof PLANNER_AGENT_RUN_ACTION_TYPES[number]

export interface PlannerAgentRunActionDescriptor {
  type: PlannerAgentRunActionType
  buildView: (actionResult: Record<string, unknown>, status: string) => ActionResultView
}

export interface PlannerAgentRunFeedbackMessage {
  role: 'system'
  content: string
  action_result: {
    type: 'ui_planner_continuation_execute'
    status: string
    data: { agent_run_id: string }
  }
  action_result_view: ActionResultView
  meta: {
    agent_run_id: string
    agent_action_type: 'ui_planner_continuation_execute'
  }
}

export const PLANNER_AGENT_RUN_ACTION_DESCRIPTORS: Record<PlannerAgentRunActionType, PlannerAgentRunActionDescriptor> = {
  ui_planner_continuation_execute: {
    type: 'ui_planner_continuation_execute',
    buildView: buildPlannerContinuationExecutionActionResultView,
  },
}

export function buildPlannerContinuationExecutionFeedback(
  run: WritingAgentRunDetail,
): PlannerAgentRunFeedbackMessage {
  const status = String(run.status || '')
  const detailItems = plannerContinuationDetailItems(run as unknown as Record<string, unknown>)
  return {
    role: 'system',
    content: '规划工具链执行已创建，可在运行详情中查看执行步骤。',
    action_result: {
      type: 'ui_planner_continuation_execute',
      status,
      data: { agent_run_id: run.id },
    },
    action_result_view: {
      type: 'ui_planner_continuation_execute',
      status,
      label: plannerContinuationStatusLabel(status),
      variant: plannerContinuationVariant(status),
      detail_items: detailItems,
    },
    meta: {
      agent_run_id: run.id,
      agent_action_type: 'ui_planner_continuation_execute',
    },
  }
}

function buildPlannerContinuationExecutionActionResultView(
  actionResult: Record<string, unknown>,
  status: string,
): ActionResultView {
  const data = recordValue(actionResult.data)
  const detailItems = [
    ...(stringValue(data.agent_run_id) ? [{ label: '运行 ID', value: stringValue(data.agent_run_id) }] : []),
    ...plannerContinuationDetailItems(data),
  ]
  return {
    type: 'ui_planner_continuation_execute',
    status,
    label: plannerContinuationStatusLabel(status),
    variant: plannerContinuationVariant(status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function plannerContinuationDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const runId = stringValue(data.id)
  if (runId) {
    items.push({ label: '运行 ID', value: runId })
  }
  const runStatus = stringValue(data.status)
  if (runStatus) {
    items.push({ label: '状态', value: plannerContinuationDetailStatusLabel(runStatus) })
  }
  const steps = Array.isArray(data.steps) ? data.steps : []
  if (steps.length) {
    items.push({ label: '工具步骤', value: `${steps.length} 个` })
  }
  return items
}

function plannerContinuationStatusLabel(status: string) {
  if (status === 'success') return '规划工具链执行已完成'
  if (status === 'failed') return '规划工具链执行失败'
  if (status === 'running') return '规划工具链执行中'
  if (status === 'blocked') return '规划工具链执行已阻止'
  return `规划工具链执行已创建：${status || '未知状态'}`
}

function plannerContinuationDetailStatusLabel(status: string) {
  if (status === 'success') return '已完成'
  if (status === 'failed') return '失败'
  if (status === 'running') return '执行中'
  if (status === 'blocked') return '已阻止'
  return status || '未知'
}

function plannerContinuationVariant(status: string) {
  if (status === 'success') return 'success'
  if (status === 'failed' || status === 'blocked') return 'error'
  return 'neutral'
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
}
