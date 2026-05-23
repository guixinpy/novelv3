import type { ActionResultView, WritingAgentRunDetail } from '../../api/types'

export const AGENT_RUN_ACTION_TYPES = [
  'plan_recovery_tools',
  'ui_recovery_execute',
  'inspect_agent_trace_audit',
  'inspect_longform_chapter_batch',
  'execute_longform_chapter_batch_preflight',
  'prepare_longform_chapter_batch_execution',
  'execute_longform_chapter_batch',
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
  inspect_longform_chapter_batch: {
    type: 'inspect_longform_chapter_batch',
    buildView: buildLongformBatchActionResultView,
  },
  execute_longform_chapter_batch_preflight: {
    type: 'execute_longform_chapter_batch_preflight',
    buildView: buildLongformPreflightActionResultView,
  },
  prepare_longform_chapter_batch_execution: {
    type: 'prepare_longform_chapter_batch_execution',
    buildView: buildLongformPrepareActionResultView,
  },
  execute_longform_chapter_batch: {
    type: 'execute_longform_chapter_batch',
    buildView: buildLongformExecuteActionResultView,
  },
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
  return {
    type: 'ui_recovery_execute',
    status,
    label: recoveryExecutionStatusLabel(status),
    variant: recoveryExecutionVariant(status),
    ...(runId ? { detail_items: [{ label: '运行 ID', value: runId }] } : {}),
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

function buildLongformBatchActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const batchStatus = stringValue(data.status) || status
  const detailItems = longformBatchDetailItems(data)
  return {
    type: 'inspect_longform_chapter_batch',
    status,
    label: longformBatchLabel(batchStatus),
    variant: longformBatchVariant(batchStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildLongformPreflightActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const preflightStatus = stringValue(data.status) || status
  const detailItems = longformPreflightDetailItems(data)
  return {
    type: 'execute_longform_chapter_batch_preflight',
    status,
    label: longformPreflightLabel(preflightStatus),
    variant: longformPreflightVariant(preflightStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildLongformPrepareActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const prepareStatus = stringValue(data.status) || status
  const detailItems = longformPrepareDetailItems(data)
  return {
    type: 'prepare_longform_chapter_batch_execution',
    status,
    label: longformPrepareLabel(prepareStatus),
    variant: longformPrepareVariant(prepareStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildLongformExecuteActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const executeStatus = stringValue(data.status) || status
  const detailItems = longformExecuteDetailItems(data)
  return {
    type: 'execute_longform_chapter_batch',
    status,
    label: longformExecuteLabel(executeStatus),
    variant: longformExecuteVariant(executeStatus),
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

function longformBatchLabel(status: string) {
  if (status === 'success' || status === 'completed') return '长篇批次检查已生成'
  if (status === 'not_found') return '长篇批次未找到'
  if (status === 'failed') return '长篇批次检查失败'
  if (status === 'running') return '长篇批次检查中'
  return `长篇批次检查: ${status || '未知状态'}`
}

function longformBatchVariant(status: string) {
  if (status === 'not_found') return 'neutral'
  return statusVariant(status)
}

function longformPreflightLabel(status: string) {
  if (status === 'ready') return '长篇批次预检已就绪'
  if (status === 'blocked') return '长篇批次预检已阻塞'
  if (status === 'not_found') return '长篇批次未找到'
  if (status === 'failed') return '长篇批次预检失败'
  if (status === 'running') return '长篇批次预检中'
  if (status === 'success' || status === 'completed') return '长篇批次预检已完成'
  return `长篇批次预检: ${status || '未知状态'}`
}

function longformPreflightVariant(status: string) {
  if (status === 'ready' || status === 'success' || status === 'completed') return 'success'
  if (status === 'blocked' || status === 'failed') return 'error'
  return 'neutral'
}

function longformPrepareLabel(status: string) {
  if (status === 'approval_required') return '长篇批次执行准备待确认'
  if (status === 'blocked') return '长篇批次执行准备已阻塞'
  if (status === 'not_found') return '长篇批次未找到'
  if (status === 'failed') return '长篇批次执行准备失败'
  if (status === 'running') return '长篇批次执行准备中'
  if (status === 'success' || status === 'completed') return '长篇批次执行准备已完成'
  return `长篇批次执行准备: ${status || '未知状态'}`
}

function longformPrepareVariant(status: string) {
  if (status === 'blocked' || status === 'failed') return 'error'
  if (status === 'success' || status === 'completed') return 'success'
  return 'neutral'
}

function longformExecuteLabel(status: string) {
  if (status === 'completed' || status === 'success') return '长篇批次执行已完成'
  if (status === 'blocked') return '长篇批次执行已阻塞'
  if (status === 'failed') return '长篇批次执行失败'
  if (status === 'not_found') return '长篇批次未找到'
  if (status === 'running') return '长篇批次执行中'
  return `长篇批次执行: ${status || '未知状态'}`
}

function longformExecuteVariant(status: string) {
  if (status === 'completed' || status === 'success') return 'success'
  if (status === 'blocked' || status === 'failed') return 'error'
  return 'neutral'
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

function longformBatchDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const queue = recordValue(data.queue)
  const queueDepth = numberValue(queue.depth)
  if (queueDepth !== null) {
    items.push({ label: '队列深度', value: `${queueDepth} 个` })
  }
  const active = numberValue(queue.active)
  if (active !== null) {
    items.push({ label: '活跃任务', value: `${active} 个` })
  }

  const summary = recordValue(data.summary)
  const selected = booleanValue(summary.selected)
  if (selected !== null) {
    items.push({ label: '命中任务', value: selected ? '是' : '否' })
  }

  const selectedTask = recordValue(data.selected_task)
  const chapterRange = chapterRangeLabel(selectedTask)
  if (chapterRange) {
    items.push({ label: '章节范围', value: chapterRange })
  }

  const readiness = recordValue(selectedTask.execution_readiness)
  const readinessStatus = stringValue(readiness.status)
  if (readinessStatus) {
    items.push({ label: '执行状态', value: batchExecutionReadinessLabel(readinessStatus) })
  }
  return items
}

function chapterRangeLabel(selectedTask: Record<string, unknown>) {
  const chapterRange = recordValue(selectedTask.chapter_range)
  const start = numberValue(chapterRange.start) ?? numberValue(chapterRange.start_chapter)
  const end = numberValue(chapterRange.end) ?? numberValue(chapterRange.end_chapter)
  if (start !== null && end !== null) {
    return start === end ? `第${start}章` : `第${start}-${end}章`
  }

  const batch = recordValue(selectedTask.batch)
  const chapterIndexes = Array.isArray(batch.chapter_indexes)
    ? batch.chapter_indexes.filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
    : []
  if (!chapterIndexes.length) return ''
  const first = Math.min(...chapterIndexes)
  const last = Math.max(...chapterIndexes)
  return first === last ? `第${first}章` : `第${first}-${last}章`
}

function batchExecutionReadinessLabel(status: string) {
  if (status === 'materialized_only') return '已物化，等待执行工具'
  if (status === 'runner_managed') return '队列可执行'
  if (status === 'approval_contract_ready') return '审批契约已就绪'
  if (status === 'phase62_executed') return '批次已执行'
  if (status === 'phase63_reviewed') return '生成后审查已完成'
  if (status === 'phase64_routed_passed') return '已路由到下一批次'
  if (status === 'phase64_routed_needs_revision') return '已路由到修订流程'
  return status
}

function longformPreflightDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const checkpoint = recordValue(data.checkpoint)
  const plan = recordValue(data.canonical_execution_plan)
  const selectedChapters = numberArrayValue(checkpoint.selected_chapter_indexes)
  const fallbackChapters = numberArrayValue(plan.chapters_to_run)
  const preflightChapters = selectedChapters.length ? selectedChapters : fallbackChapters
  const preflightLabel = chapterIndexesLabel(preflightChapters)
  if (preflightLabel) {
    items.push({ label: '预检章节', value: preflightLabel })
  }

  const readyChapters = numberArrayValue(checkpoint.ready_chapter_indexes)
  if (readyChapters.length || Array.isArray(checkpoint.ready_chapter_indexes)) {
    items.push({ label: '就绪章节', value: `${readyChapters.length} 章` })
  }

  const blockedChapters = numberArrayValue(checkpoint.blocked_chapter_indexes)
  if (blockedChapters.length || Array.isArray(checkpoint.blocked_chapter_indexes)) {
    items.push({ label: '阻塞章节', value: `${blockedChapters.length} 章` })
  }

  const stoppedBeforeNode = stringValue(plan.stopped_before_node)
  if (stoppedBeforeNode) {
    items.push({ label: '停止节点', value: stoppedBeforeNodeLabel(stoppedBeforeNode) })
  }

  const reason = stringValue(data.reason)
  if (reason) {
    items.push({ label: '阻塞原因', value: reason })
  }

  const nextTools = Array.isArray(data.recommended_next_tools) ? data.recommended_next_tools : []
  if (nextTools.length) {
    items.push({ label: '下一步', value: `${nextTools.length} 个工具` })
  }
  return items
}

function chapterIndexesLabel(indexes: number[]) {
  const normalized = Array.from(new Set(indexes)).sort((left, right) => left - right)
  if (!normalized.length) return ''
  if (normalized.length === 1) return `第${normalized[0]}章`
  const first = normalized[0]
  const last = normalized[normalized.length - 1]
  const isContiguous = normalized.every((value, index) => value === first + index)
  if (isContiguous) return `第${first}-${last}章`
  return `第${normalized.join('、')}章`
}

function stoppedBeforeNodeLabel(node: string) {
  if (node === 'chapter_generation') return '正文生成前'
  if (node === 'world_model_apply') return '世界模型写入前'
  return node
}

function longformPrepareDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const attemptManifest = recordValue(data.attempt_manifest)
  const task = recordValue(data.task)
  const executionChapters = chapterIndexesLabel(numberArrayValue(attemptManifest.chapter_indexes))
    || chapterRangeLabel(task)
  if (executionChapters) {
    items.push({ label: '执行章节', value: executionChapters })
  }

  const agentApproval = recordValue(data.agent_plan_approval_contract)
  const approvalStatus = stringValue(agentApproval.status)
  if (approvalStatus) {
    items.push({ label: '审批状态', value: approvalStatusLabel(approvalStatus) })
  }

  const writeStepCount = numberValue(agentApproval.write_step_count)
  const executionSteps = Array.isArray(attemptManifest.execution_steps) ? attemptManifest.execution_steps : []
  const resolvedWriteStepCount = writeStepCount ?? executionSteps.length
  if (resolvedWriteStepCount > 0) {
    items.push({ label: '写入步骤', value: `${resolvedWriteStepCount} 个` })
  }

  const approvalContract = recordValue(data.approval_contract)
  const consumeTool = stringValue(approvalContract.consume_tool)
  if (consumeTool) {
    items.push({ label: '消费工具', value: consumeTool })
  }

  const highRiskSideEffects = Array.isArray(approvalContract.high_risk_side_effects)
    ? approvalContract.high_risk_side_effects
    : []
  if (highRiskSideEffects.length) {
    items.push({ label: '高风险副作用', value: `${highRiskSideEffects.length} 项` })
  }

  const reason = stringValue(data.reason)
  if (reason) {
    items.push({ label: '阻塞原因', value: reason })
  }

  const nextTools = Array.isArray(data.recommended_next_tools) ? data.recommended_next_tools : []
  if (nextTools.length) {
    items.push({ label: '下一步', value: `${nextTools.length} 个工具` })
  }
  return items
}

function approvalStatusLabel(status: string) {
  if (status === 'requires_confirmation' || status === 'approval_required') return '等待确认'
  if (status === 'approved') return '已确认'
  if (status === 'rejected') return '已拒绝'
  return status
}

function longformExecuteDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const executedChapters = numberArrayValue(data.executed_chapter_indexes)
  const chapterIndex = numberValue(data.chapter_index)
  const task = recordValue(data.task)
  const executionChapters = chapterIndexesLabel(executedChapters)
    || (chapterIndex !== null ? `第${chapterIndex}章` : '')
    || chapterRangeLabel(task)
  if (executionChapters) {
    items.push({ label: '执行章节', value: executionChapters })
  }

  const generation = recordValue(data.generation)
  const generationStatus = stringValue(generation.status)
  if (generationStatus) {
    items.push({ label: '生成状态', value: generationStatusLabel(generationStatus) })
  }

  const evidence = recordValue(data.evidence)
  const chapterWritten = booleanValue(evidence.chapter_content_written)
  if (chapterWritten !== null) {
    items.push({ label: '章节写入', value: chapterWritten ? '已写入' : '未写入' })
  }

  const approvalVerified = booleanValue(evidence.agent_plan_approval_verified)
  const approvalVerification = recordValue(data.agent_plan_approval_verification)
  const approvalStatus = stringValue(approvalVerification.status)
  if (approvalVerified !== null) {
    items.push({ label: '审批校验', value: approvalVerified ? '已验证' : '未验证' })
  } else if (approvalStatus) {
    items.push({ label: '审批校验', value: executionReadinessStatusLabel(approvalStatus) })
  }

  const resourceBinding = recordValue(data.execution_resource_binding)
  const bindingStatus = stringValue(resourceBinding.status)
  if (bindingStatus) {
    items.push({ label: '资源绑定', value: executionReadinessStatusLabel(bindingStatus) })
  }

  const reason = stringValue(data.reason)
  if (reason) {
    items.push({ label: '阻塞原因', value: reason })
  }

  const error = stringValue(data.error)
  if (error) {
    items.push({ label: '错误摘要', value: error })
  }

  const sideEffects = recordValue(data.side_effects)
  const executed = Array.isArray(sideEffects.executed) ? sideEffects.executed : []
  if (executed.length) {
    items.push({ label: '副作用', value: `${executed.length} 项` })
  }

  const nextTools = Array.isArray(data.recommended_next_tools) ? data.recommended_next_tools : []
  if (nextTools.length) {
    items.push({ label: '下一步', value: `${nextTools.length} 个工具` })
  }
  return items
}

function generationStatusLabel(status: string) {
  if (status === 'success' || status === 'completed') return '成功'
  if (status === 'failed') return '失败'
  if (status === 'running') return '生成中'
  return status
}

function executionReadinessStatusLabel(status: string) {
  if (status === 'ready') return '就绪'
  if (status === 'blocked') return '阻塞'
  if (status === 'failed') return '失败'
  if (status === 'success') return '成功'
  return status
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

function numberValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function numberArrayValue(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is number => typeof item === 'number' && Number.isFinite(item))
    : []
}

function booleanValue(value: unknown) {
  return typeof value === 'boolean' ? value : null
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
