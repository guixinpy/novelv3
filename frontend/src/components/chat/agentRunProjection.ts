import type { ActionResultView } from '../../api/types'
import {
  AGENT_RUN_ACTION_DESCRIPTORS,
} from './agentRunActionRegistry'
import type {
  AgentRunActionDescriptor,
  AgentRunActionType,
} from './agentRunActionRegistry'
export { AGENT_RUN_ACTION_TYPES } from './agentRunActionRegistry'
export type {
  AgentRunActionDescriptor,
  AgentRunActionType,
} from './agentRunActionRegistry'
export type { AgentRunFeedbackMessage } from './recoveryAgentRunProjection'
export {
  buildAgentRunExecutionFeedback,
  buildRecommendedFollowupExecutionFeedback,
} from './recoveryAgentRunProjection'
export type { PlannerAgentRunFeedbackMessage } from './plannerAgentRunProjection'
export {
  buildPlannerContinuationExecutionFeedback,
} from './plannerAgentRunProjection'

interface AgentRunMessageLike {
  action_result?: Record<string, unknown> | null
  action_result_view?: Partial<ActionResultView> | null
  meta?: Record<string, unknown> | null
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
  const runId = stringValue(run.id)
  if (runId) return runId
  const selectedTask = recordValue((data as Record<string, unknown>).selected_task)
  const agentRuns = Array.isArray(selectedTask.agent_runs) ? selectedTask.agent_runs : []
  const firstRun = recordValue(agentRuns[0])
  return stringValue(firstRun.id)
}

export function buildAgentRunActionResultView(actionResult: Record<string, unknown> | null | undefined): ActionResultView | null {
  if (!actionResult) return null
  const actionType = stringValue(actionResult.type)
  const status = stringValue(actionResult.status)
  const descriptor = getAgentRunActionDescriptor(actionType)
  if (!descriptor || !status) return null
  return descriptor.buildView(actionResult, status)
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
}
