import type { ActionResultView } from '../../api/types'

export const LONGFORM_AGENT_RUN_ACTION_TYPES = [
  'inspect_longform_chapter_batch',
  'execute_longform_chapter_batch_preflight',
  'prepare_longform_chapter_batch_execution',
  'execute_longform_chapter_batch',
  'review_longform_chapter_batch_execution',
  'route_longform_chapter_batch_after_review',
] as const

export type LongformAgentRunActionType = typeof LONGFORM_AGENT_RUN_ACTION_TYPES[number]

export interface LongformAgentRunActionDescriptor {
  type: LongformAgentRunActionType
  buildView: (actionResult: Record<string, unknown>, status: string) => ActionResultView
}

export const LONGFORM_AGENT_RUN_ACTION_DESCRIPTORS: Record<LongformAgentRunActionType, LongformAgentRunActionDescriptor> = {
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
  review_longform_chapter_batch_execution: {
    type: 'review_longform_chapter_batch_execution',
    buildView: buildLongformReviewActionResultView,
  },
  route_longform_chapter_batch_after_review: {
    type: 'route_longform_chapter_batch_after_review',
    buildView: buildLongformRouteActionResultView,
  },
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

function buildLongformReviewActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const reviewStatus = stringValue(data.status) || status
  const detailItems = longformReviewDetailItems(data, reviewStatus)
  return {
    type: 'review_longform_chapter_batch_execution',
    status,
    label: longformReviewLabel(reviewStatus),
    variant: longformReviewVariant(reviewStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildLongformRouteActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const routeStatus = stringValue(data.status) || status
  const routeDecision = stringValue(recordValue(data.route_decision).decision)
  const detailItems = longformRouteDetailItems(data, routeStatus)
  return {
    type: 'route_longform_chapter_batch_after_review',
    status,
    label: longformRouteLabel(routeStatus, routeDecision),
    variant: longformRouteVariant(routeStatus, routeDecision),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
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

function longformReviewLabel(status: string) {
  if (status === 'completed' || status === 'success') return '长篇批次审查已通过'
  if (status === 'blocked') return '长篇批次审查已阻塞'
  if (status === 'skipped') return '长篇批次审查已记录'
  if (status === 'failed') return '长篇批次审查失败'
  if (status === 'not_found') return '长篇批次未找到'
  if (status === 'running') return '长篇批次审查中'
  return `长篇批次审查: ${status || '未知状态'}`
}

function longformReviewVariant(status: string) {
  if (status === 'completed' || status === 'success') return 'success'
  if (status === 'blocked' || status === 'failed') return 'error'
  return 'neutral'
}

function longformRouteLabel(status: string, decision: string) {
  if ((status === 'completed' || status === 'success') && decision === 'continue_to_next_batch') {
    return '长篇批次已路由到下一批'
  }
  if ((status === 'completed' || status === 'success') && decision === 'stop_for_revision') {
    return '长篇批次已路由到修订'
  }
  if (status === 'blocked') return '长篇批次路由已阻塞'
  if (status === 'skipped') return '长篇批次路由已记录'
  if (status === 'failed') return '长篇批次路由失败'
  if (status === 'not_found') return '长篇批次未找到'
  if (status === 'running') return '长篇批次路由中'
  return `长篇批次路由: ${status || '未知状态'}`
}

function longformRouteVariant(status: string, decision: string) {
  if ((status === 'completed' || status === 'success') && decision === 'continue_to_next_batch') return 'success'
  if (status === 'blocked' || status === 'failed') return 'error'
  return 'neutral'
}

function statusVariant(status: string) {
  if (status === 'success' || status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  return 'neutral'
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

function longformReviewDetailItems(data: Record<string, unknown>, reviewStatus: string) {
  const items: Array<{ label: string; value: string }> = []
  const chapterIndex = numberValue(data.chapter_index)
  const task = recordValue(data.task)
  const reviewChapter = chapterIndex !== null ? `第${chapterIndex}章` : chapterRangeLabel(task)
  if (reviewChapter) {
    items.push({ label: '审查章节', value: reviewChapter })
  }

  const reviewGate = recordValue(data.review_gate)
  const gateStatus = stringValue(reviewGate.status)
  if (gateStatus) {
    items.push({ label: '审查闸门', value: reviewGateStatusLabel(gateStatus) })
  }

  const blockerCount = numberValue(reviewGate.blocker_count)
  if (blockerCount !== null) {
    items.push({ label: '阻塞项', value: `${blockerCount} 项` })
  }

  const warningCount = numberValue(reviewGate.warning_count)
  if (warningCount !== null) {
    items.push({ label: '警告项', value: `${warningCount} 项` })
  }

  const reviews = recordValue(data.reviews)
  const qualityStatus = stringValue(recordValue(reviews.quality).status)
  if (qualityStatus) {
    items.push({ label: '质量审查', value: reviewComponentStatusLabel(qualityStatus) })
  }
  const continuityStatus = stringValue(recordValue(reviews.continuity).status)
  if (continuityStatus) {
    items.push({ label: '连续性审查', value: reviewComponentStatusLabel(continuityStatus) })
  }
  const worldModelStatus = stringValue(recordValue(reviews.world_model).status)
  if (worldModelStatus) {
    items.push({ label: '世界模型', value: reviewComponentStatusLabel(worldModelStatus) })
  }

  const reason = stringValue(data.reason)
  if (reason) {
    items.push({ label: reviewStatus === 'skipped' ? '跳过原因' : '阻塞原因', value: reason })
  }

  const nextTools = Array.isArray(data.recommended_next_tools) ? data.recommended_next_tools : []
  if (nextTools.length) {
    items.push({ label: '下一步', value: `${nextTools.length} 个工具` })
  }
  return items
}

function reviewGateStatusLabel(status: string) {
  if (status === 'passed') return '已通过'
  if (status === 'needs_revision') return '需要修订'
  if (status === 'blocked') return '阻塞'
  return status
}

function reviewComponentStatusLabel(status: string) {
  if (status === 'ready') return '就绪'
  if (status === 'completed' || status === 'success') return '成功'
  if (status === 'blocked') return '阻塞'
  if (status === 'failed') return '失败'
  if (status === 'skipped') return '已跳过'
  return status
}

function longformRouteDetailItems(data: Record<string, unknown>, routeStatus: string) {
  const items: Array<{ label: string; value: string }> = []
  const chapterIndex = numberValue(data.chapter_index)
  const task = recordValue(data.task)
  const routeChapter = chapterIndex !== null ? `第${chapterIndex}章` : chapterRangeLabel(task)
  if (routeChapter) {
    items.push({ label: '路由章节', value: routeChapter })
  }

  const routeDecision = recordValue(data.route_decision)
  const decision = stringValue(routeDecision.decision)
  if (decision) {
    items.push({ label: '路由决策', value: routeDecisionLabel(decision) })
  }

  const nextChapterIndex = numberValue(routeDecision.next_chapter_index)
  if (nextChapterIndex !== null) {
    items.push({ label: '下一章', value: `第${nextChapterIndex}章` })
  }

  const nextBatchPlan = recordValue(data.next_batch_plan)
  const nextBatch = recordValue(nextBatchPlan.batch)
  const nextBatchIndexes = numberArrayValue(nextBatch.chapter_indexes)
  const nextBatchLabel = chapterIndexesLabel(nextBatchIndexes)
  if (nextBatchLabel) {
    items.push({ label: '下一批', value: nextBatchLabel })
  } else {
    const nextBatchSize = numberValue(routeDecision.next_batch_size)
    if (nextBatchSize !== null) {
      items.push({ label: '下一批', value: `${nextBatchSize} 章` })
    }
  }

  const recoveryPlan = recordValue(data.recovery_plan)
  const revisionPlan = recordValue(recoveryPlan.revision_plan)
  const revisionActions = Array.isArray(revisionPlan.revision_actions) ? revisionPlan.revision_actions : []
  if (revisionActions.length) {
    items.push({ label: '修订动作', value: `${revisionActions.length} 项` })
  }

  const reason = stringValue(data.reason)
  if (reason) {
    items.push({ label: routeStatus === 'skipped' ? '跳过原因' : '阻塞原因', value: reason })
  }

  const nextTools = Array.isArray(data.recommended_next_tools) ? data.recommended_next_tools : []
  if (nextTools.length) {
    items.push({ label: '下一步', value: `${nextTools.length} 个工具` })
  }
  return items
}

function routeDecisionLabel(decision: string) {
  if (decision === 'continue_to_next_batch') return '继续下一批'
  if (decision === 'stop_for_revision') return '进入修订'
  return decision
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
