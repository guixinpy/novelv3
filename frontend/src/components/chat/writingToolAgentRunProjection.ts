import type { ActionResultView } from '../../api/types'

export const WRITING_TOOL_AGENT_RUN_ACTION_TYPES = [
  'review_chapter_quality',
  'review_chapter_continuity',
  'analyze_chapter_world_model',
  'review_world_model_proposals',
  'plan_world_model_proposal_resolution',
  'preview_world_model_proposal_resolution',
  'apply_world_model_proposal_resolution',
  'plan_chapter_revision',
  'create_revision_draft',
  'apply_planner_revision_patch',
  'expand_chapter_to_target',
  'compress_chapter_to_target',
] as const

export type WritingToolAgentRunActionType = typeof WRITING_TOOL_AGENT_RUN_ACTION_TYPES[number]

export interface WritingToolAgentRunActionDescriptor {
  type: WritingToolAgentRunActionType
  buildView: (actionResult: Record<string, unknown>, status: string) => ActionResultView
}

export const WRITING_TOOL_AGENT_RUN_ACTION_DESCRIPTORS: Record<WritingToolAgentRunActionType, WritingToolAgentRunActionDescriptor> = {
  review_chapter_quality: {
    type: 'review_chapter_quality',
    buildView: buildChapterQualityReviewActionResultView,
  },
  review_chapter_continuity: {
    type: 'review_chapter_continuity',
    buildView: buildChapterContinuityReviewActionResultView,
  },
  analyze_chapter_world_model: {
    type: 'analyze_chapter_world_model',
    buildView: buildWorldModelAnalysisActionResultView,
  },
  review_world_model_proposals: {
    type: 'review_world_model_proposals',
    buildView: buildWorldModelProposalReportActionResultView,
  },
  plan_world_model_proposal_resolution: {
    type: 'plan_world_model_proposal_resolution',
    buildView: buildWorldModelResolutionPlanActionResultView,
  },
  preview_world_model_proposal_resolution: {
    type: 'preview_world_model_proposal_resolution',
    buildView: buildWorldModelResolutionPreviewActionResultView,
  },
  apply_world_model_proposal_resolution: {
    type: 'apply_world_model_proposal_resolution',
    buildView: buildWorldModelResolutionApplyActionResultView,
  },
  plan_chapter_revision: {
    type: 'plan_chapter_revision',
    buildView: buildChapterRevisionPlanActionResultView,
  },
  create_revision_draft: {
    type: 'create_revision_draft',
    buildView: buildRevisionDraftActionResultView,
  },
  apply_planner_revision_patch: {
    type: 'apply_planner_revision_patch',
    buildView: buildRevisionPatchApplyActionResultView,
  },
  expand_chapter_to_target: {
    type: 'expand_chapter_to_target',
    buildView: buildChapterExpansionActionResultView,
  },
  compress_chapter_to_target: {
    type: 'compress_chapter_to_target',
    buildView: buildChapterCompressionActionResultView,
  },
}

function buildChapterQualityReviewActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const reviewStatus = stringValue(data.status) || status
  const detailItems = chapterQualityReviewDetailItems(data)
  return {
    type: 'review_chapter_quality',
    status,
    label: chapterQualityReviewLabel(status),
    variant: reviewActionVariant(reviewStatus, status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildChapterContinuityReviewActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const reviewStatus = stringValue(data.status) || status
  const detailItems = chapterContinuityReviewDetailItems(data)
  return {
    type: 'review_chapter_continuity',
    status,
    label: chapterContinuityReviewLabel(status),
    variant: reviewActionVariant(reviewStatus, status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildWorldModelAnalysisActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const analysisStatus = stringValue(data.status) || status
  const detailItems = worldModelAnalysisDetailItems(data)
  return {
    type: 'analyze_chapter_world_model',
    status,
    label: worldModelAnalysisLabel(status),
    variant: reviewActionVariant(analysisStatus, status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildWorldModelProposalReportActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const queueStatus = stringValue(data.status) || status
  const detailItems = worldModelProposalReportDetailItems(data)
  return {
    type: 'review_world_model_proposals',
    status,
    label: worldModelProposalReportLabel(queueStatus),
    variant: worldModelBlockingVariant(queueStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildWorldModelResolutionPlanActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const planStatus = stringValue(data.status) || status
  const detailItems = worldModelResolutionPlanDetailItems(data)
  return {
    type: 'plan_world_model_proposal_resolution',
    status,
    label: worldModelResolutionPlanLabel(planStatus),
    variant: worldModelBlockingVariant(planStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildWorldModelResolutionPreviewActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const previewStatus = stringValue(data.status) || status
  const detailItems = worldModelResolutionPreviewDetailItems(data)
  return {
    type: 'preview_world_model_proposal_resolution',
    status,
    label: worldModelResolutionPreviewLabel(previewStatus),
    variant: worldModelBlockingVariant(previewStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildWorldModelResolutionApplyActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const applyStatus = stringValue(data.status) || status
  const detailItems = worldModelResolutionApplyDetailItems(data)
  return {
    type: 'apply_world_model_proposal_resolution',
    status,
    label: worldModelResolutionApplyLabel(applyStatus),
    variant: worldModelBlockingVariant(applyStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildChapterRevisionPlanActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const planStatus = stringValue(data.status) || status
  const detailItems = chapterRevisionPlanDetailItems(data)
  return {
    type: 'plan_chapter_revision',
    status,
    label: chapterRevisionPlanLabel(planStatus),
    variant: revisionVariant(planStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildRevisionDraftActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const draftStatus = stringValue(data.status) || status
  const detailItems = revisionDraftDetailItems(data)
  return {
    type: 'create_revision_draft',
    status,
    label: revisionDraftLabel(draftStatus),
    variant: revisionVariant(draftStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildRevisionPatchApplyActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const applyStatus = stringValue(data.status) || status
  const detailItems = revisionPatchApplyDetailItems(data)
  return {
    type: 'apply_planner_revision_patch',
    status,
    label: revisionPatchApplyLabel(applyStatus),
    variant: revisionVariant(applyStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildChapterExpansionActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const expansionStatus = stringValue(data.status) || status
  const detailItems = chapterExpansionDetailItems(data)
  return {
    type: 'expand_chapter_to_target',
    status,
    label: chapterExpansionLabel(expansionStatus),
    variant: revisionVariant(expansionStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildChapterCompressionActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const compressionStatus = stringValue(data.status) || status
  const detailItems = chapterCompressionDetailItems(data)
  return {
    type: 'compress_chapter_to_target',
    status,
    label: chapterCompressionLabel(compressionStatus),
    variant: revisionVariant(compressionStatus),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function chapterQualityReviewLabel(status: string) {
  if (status === 'success' || status === 'completed') return '章节质量审查已生成'
  if (status === 'failed') return '章节质量审查失败'
  if (status === 'running') return '章节质量审查中'
  return `章节质量审查: ${status || '未知状态'}`
}

function chapterContinuityReviewLabel(status: string) {
  if (status === 'success' || status === 'completed') return '章节连续性审查已生成'
  if (status === 'failed') return '章节连续性审查失败'
  if (status === 'running') return '章节连续性审查中'
  return `章节连续性审查: ${status || '未知状态'}`
}

function worldModelAnalysisLabel(status: string) {
  if (status === 'success' || status === 'completed') return '世界模型分析已生成'
  if (status === 'failed') return '世界模型分析失败'
  if (status === 'running') return '世界模型分析中'
  return `世界模型分析: ${status || '未知状态'}`
}

function worldModelProposalReportLabel(status: string) {
  if (status === 'ready') return '世界模型提案队列已清空'
  if (status === 'blocked') return '世界模型提案待处理'
  if (status === 'missing_profile') return '世界模型 Profile 缺失'
  if (status === 'failed') return '世界模型提案检查失败'
  if (status === 'running') return '世界模型提案检查中'
  return `世界模型提案检查: ${status || '未知状态'}`
}

function worldModelResolutionPlanLabel(status: string) {
  if (status === 'ready') return '世界模型决议计划无需处理'
  if (status === 'blocked') return '世界模型决议计划待处理'
  if (status === 'missing_profile') return '世界模型 Profile 缺失'
  if (status === 'failed') return '世界模型决议计划失败'
  if (status === 'running') return '世界模型决议计划中'
  return `世界模型决议计划: ${status || '未知状态'}`
}

function worldModelResolutionPreviewLabel(status: string) {
  if (status === 'ready') return '世界模型决议预览已就绪'
  if (status === 'blocked') return '世界模型决议预览待处理'
  if (status === 'missing_profile') return '世界模型 Profile 缺失'
  if (status === 'failed') return '世界模型决议预览失败'
  if (status === 'running') return '世界模型决议预览中'
  return `世界模型决议预览: ${status || '未知状态'}`
}

function worldModelResolutionApplyLabel(status: string) {
  if (status === 'ready' || status === 'success' || status === 'completed') return '世界模型决议应用已完成'
  if (status === 'blocked') return '世界模型决议应用已阻塞'
  if (status === 'missing_profile') return '世界模型 Profile 缺失'
  if (status === 'failed') return '世界模型决议应用失败'
  if (status === 'running') return '世界模型决议应用中'
  return `世界模型决议应用: ${status || '未知状态'}`
}

function chapterRevisionPlanLabel(status: string) {
  if (status === 'ready') return '章节修订计划已就绪'
  if (status === 'warning') return '章节修订计划有警告'
  if (status === 'blocked') return '章节修订计划待处理'
  if (status === 'failed') return '章节修订计划失败'
  if (status === 'running') return '章节修订计划中'
  return `章节修订计划: ${status || '未知状态'}`
}

function revisionDraftLabel(status: string) {
  if (status === 'drafted') return '章节修订草稿已创建'
  if (status === 'skipped') return '章节修订草稿已跳过'
  if (status === 'blocked') return '章节修订草稿已阻塞'
  if (status === 'failed') return '章节修订草稿失败'
  if (status === 'running') return '章节修订草稿创建中'
  return `章节修订草稿: ${status || '未知状态'}`
}

function revisionPatchApplyLabel(status: string) {
  if (status === 'completed' || status === 'success') return '章节修订补丁已应用'
  if (status === 'blocked') return '章节修订补丁已阻塞'
  if (status === 'failed') return '章节修订补丁失败'
  if (status === 'running') return '章节修订补丁应用中'
  return `章节修订补丁: ${status || '未知状态'}`
}

function chapterExpansionLabel(status: string) {
  if (status === 'completed' || status === 'success') return '章节扩写已完成'
  if (status === 'blocked') return '章节扩写已阻塞'
  if (status === 'failed') return '章节扩写失败'
  if (status === 'running') return '章节扩写中'
  return `章节扩写: ${status || '未知状态'}`
}

function chapterCompressionLabel(status: string) {
  if (status === 'completed' || status === 'success') return '章节压缩已完成'
  if (status === 'blocked') return '章节压缩已阻塞'
  if (status === 'failed') return '章节压缩失败'
  if (status === 'running') return '章节压缩中'
  return `章节压缩: ${status || '未知状态'}`
}

function chapterQualityReviewDetailItems(data: Record<string, unknown>) {
  const items = chapterReviewBaseDetailItems(data, '审查状态')
  const score = numberValue(data.score)
  if (score !== null) {
    items.push({ label: '评分', value: String(score) })
  }
  items.push(...issueAndActionCountItems(data, '建议动作'))
  return items
}

function chapterContinuityReviewDetailItems(data: Record<string, unknown>) {
  const items = chapterReviewBaseDetailItems(data, '审查状态')
  const lookback = numberValue(data.lookback)
  if (lookback !== null) {
    items.push({ label: '回看窗口', value: `${lookback} 章` })
  }
  items.push(...issueAndActionCountItems(data, '建议动作'))
  return items
}

function worldModelAnalysisDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const chapterIndex = numberValue(data.chapter_index)
  if (chapterIndex !== null) {
    items.push({ label: '章节', value: `第${chapterIndex}章` })
  }
  const status = stringValue(data.status)
  if (status) {
    items.push({ label: '分析状态', value: reviewStatusLabel(status) })
  }
  const proposalCount = worldModelProposalCount(data)
  if (proposalCount !== null) {
    items.push({ label: '提案', value: `${proposalCount} 条` })
  }
  const recommendedNextToolCount = recommendedToolCount(data)
  if (recommendedNextToolCount > 0) {
    items.push({ label: '下一步', value: `${recommendedNextToolCount} 个工具` })
  }
  return items
}

function worldModelProposalReportDetailItems(data: Record<string, unknown>) {
  const items = worldModelQueueBaseDetailItems(data, '队列状态')
  const hasMore = data.has_more
  if (typeof hasMore === 'boolean') {
    items.push({ label: '还有更多', value: yesNoLabel(hasMore) })
  }
  const actionCount = recommendedToolCount(data)
  if (actionCount > 0) {
    items.push({ label: '建议动作', value: `${actionCount} 个` })
  }
  return items
}

function worldModelResolutionPlanDetailItems(data: Record<string, unknown>) {
  const items = worldModelQueueBaseDetailItems(data, '计划状态')
  const resolutionSteps = Array.isArray(data.resolution_steps) ? data.resolution_steps : []
  if (resolutionSteps.length) {
    items.push({ label: '处理步骤', value: `${resolutionSteps.length} 个` })
  }
  const highPriorityStepCount = numberValue(data.high_priority_step_count)
  if (highPriorityStepCount !== null) {
    items.push({ label: '高优先级', value: `${highPriorityStepCount} 个` })
  }
  const batchStepCount = numberValue(data.batch_step_count)
  if (batchStepCount !== null) {
    items.push({ label: '批量步骤', value: `${batchStepCount} 个` })
  }
  if (typeof data.requires_human_confirmation === 'boolean') {
    items.push({ label: '需要确认', value: yesNoLabel(data.requires_human_confirmation) })
  }
  const nextToolCount = recommendedToolCount(data)
  if (nextToolCount > 0) {
    items.push({ label: '下一步', value: `${nextToolCount} 个工具` })
  }
  return items
}

function worldModelResolutionPreviewDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const status = stringValue(data.status)
  if (status) {
    items.push({ label: '预览状态', value: reviewStatusLabel(status) })
  }
  pushCountItem(items, '待处理', data.total_actionable_items, '条')
  pushCountItem(items, '有效决策', data.valid_decision_count, '个')
  pushCountItem(items, '无效决策', data.invalid_decision_count, '个')
  pushCountItem(items, '将写入事实', data.would_create_fact_count, '条')
  pushCountItem(items, '预计解决', data.would_resolve_item_count, '条')
  pushCountItem(items, '预览后剩余', data.remaining_actionable_item_count_after_preview, '条')
  if (typeof data.requires_confirmation === 'boolean') {
    items.push({ label: '需要确认', value: yesNoLabel(data.requires_confirmation) })
  }
  const actionCount = recommendedToolCount(data)
  if (actionCount > 0) {
    items.push({ label: '建议动作', value: `${actionCount} 个` })
  }
  return items
}

function worldModelResolutionApplyDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const status = stringValue(data.status)
  if (status) {
    items.push({ label: '应用状态', value: reviewStatusLabel(status) })
  }
  pushCountItem(items, '应用前待处理', data.before_actionable_items, '条')
  pushCountItem(items, '应用后待处理', data.after_actionable_items, '条')
  pushCountItem(items, '已应用', data.applied_count, '个')
  pushCountItem(items, '无效决策', data.invalid_decision_count, '个')
  if (typeof data.requires_confirmation === 'boolean') {
    items.push({ label: '需要确认', value: yesNoLabel(data.requires_confirmation) })
  }
  if (typeof data.should_generate_next_chapter === 'boolean') {
    items.push({ label: '可继续生成', value: yesNoLabel(data.should_generate_next_chapter) })
  }
  const actionCount = recommendedToolCount(data)
  if (actionCount > 0) {
    items.push({ label: '建议动作', value: `${actionCount} 个` })
  }
  return items
}

function worldModelQueueBaseDetailItems(data: Record<string, unknown>, statusLabel: string) {
  const items: Array<{ label: string; value: string }> = []
  const status = stringValue(data.status)
  if (status) {
    items.push({ label: statusLabel, value: reviewStatusLabel(status) })
  }
  pushCountItem(items, '待处理', data.total_items, '条')
  pushCountItem(items, '本次返回', data.returned_items, '条')
  const riskCounts = recordValue(data.risk_counts)
  pushCountItem(items, '高风险', riskCounts.high, '条')
  const reviewModeCounts = recordValue(data.review_mode_counts)
  pushCountItem(items, '批量审阅', reviewModeCounts.batch, '条')
  return items
}

function chapterRevisionPlanDetailItems(data: Record<string, unknown>) {
  const items = chapterRevisionBaseDetailItems(data, '计划状态')
  const actionCount = revisionActionCount(data)
  if (actionCount > 0) {
    items.push({ label: '修订动作', value: `${actionCount} 项` })
  }
  const proposalPressureCount = worldModelProposalPressureCount(data)
  if (proposalPressureCount !== null) {
    items.push({ label: '世界模型提案', value: `${proposalPressureCount} 条` })
  }
  const nextToolCount = recommendedToolCount(data)
  if (nextToolCount > 0) {
    items.push({ label: '下一步', value: `${nextToolCount} 个工具` })
  }
  return items
}

function revisionDraftDetailItems(data: Record<string, unknown>) {
  const items = chapterRevisionBaseDetailItems(data, '草稿状态')
  pushCountItem(items, '修订序号', data.revision_index, '')
  pushCountItem(items, '批注', data.annotation_count, '个')
  pushCountItem(items, '修正', data.correction_count, '个')
  const actionCount = revisionActionCount(data)
  if (actionCount > 0) {
    items.push({ label: '修订动作', value: `${actionCount} 项` })
  }
  const nextToolCount = recommendedToolCount(data)
  if (nextToolCount > 0) {
    items.push({ label: '下一步', value: `${nextToolCount} 个工具` })
  }
  return items
}

function revisionPatchApplyDetailItems(data: Record<string, unknown>) {
  const items = chapterRevisionBaseDetailItems(data, '应用状态')
  pushCountItem(items, '修订序号', data.revision_index, '')
  pushCountItem(items, '替换', data.applied_replacement_count, '处')
  pushCountItem(items, '当前字数', data.word_count, '')
  if (typeof data.should_generate_next_chapter === 'boolean') {
    items.push({ label: '可继续生成', value: yesNoLabel(data.should_generate_next_chapter) })
  }
  const nextToolCount = recommendedToolCount(data)
  if (nextToolCount > 0) {
    items.push({ label: '下一步', value: `${nextToolCount} 个工具` })
  }
  return items
}

function chapterExpansionDetailItems(data: Record<string, unknown>) {
  const items = chapterRevisionBaseDetailItems(data, '扩写状态')
  pushCountItem(items, '原字数', data.previous_word_count, '')
  pushCountItem(items, '当前字数', data.word_count, '')
  pushCountItem(items, '目标下限', data.target_min_word_count, '')
  const warnings = Array.isArray(data.warnings) ? data.warnings : []
  if (warnings.length) {
    items.push({ label: '警告', value: `${warnings.length} 个` })
  }
  pushCountItem(items, '世界模型提案', data.pending_world_model_proposal_count, '条')
  if (typeof data.should_generate_next_chapter === 'boolean') {
    items.push({ label: '可继续生成', value: yesNoLabel(data.should_generate_next_chapter) })
  }
  const nextToolCount = recommendedToolCount(data)
  if (nextToolCount > 0) {
    items.push({ label: '下一步', value: `${nextToolCount} 个工具` })
  }
  return items
}

function chapterCompressionDetailItems(data: Record<string, unknown>) {
  const items = chapterRevisionBaseDetailItems(data, '压缩状态')
  pushCountItem(items, '原字数', data.previous_word_count, '')
  pushCountItem(items, '当前字数', data.word_count, '')
  pushCountItem(items, '目标上限', data.target_max_word_count, '')
  const remainingForbiddenTerms = Array.isArray(data.remaining_forbidden_terms) ? data.remaining_forbidden_terms : []
  if (Array.isArray(data.remaining_forbidden_terms)) {
    items.push({ label: '禁用词剩余', value: `${remainingForbiddenTerms.length} 个` })
  }
  pushCountItem(items, '重试', data.postcondition_retry_count, '次')
  const failedAttempts = Array.isArray(data.failed_attempts) ? data.failed_attempts : []
  if (Array.isArray(data.failed_attempts)) {
    items.push({ label: '失败尝试', value: `${failedAttempts.length} 次` })
  }
  pushCountItem(items, '世界模型提案', data.pending_world_model_proposal_count, '条')
  if (typeof data.should_generate_next_chapter === 'boolean') {
    items.push({ label: '可继续生成', value: yesNoLabel(data.should_generate_next_chapter) })
  }
  const nextToolCount = recommendedToolCount(data)
  if (nextToolCount > 0) {
    items.push({ label: '下一步', value: `${nextToolCount} 个工具` })
  }
  return items
}

function chapterRevisionBaseDetailItems(data: Record<string, unknown>, statusLabel: string) {
  const items: Array<{ label: string; value: string }> = []
  const chapterIndex = numberValue(data.chapter_index)
  if (chapterIndex !== null) {
    items.push({ label: '章节', value: `第${chapterIndex}章` })
  }
  const status = stringValue(data.status)
  if (status) {
    items.push({ label: statusLabel, value: revisionStatusLabel(status) })
  }
  return items
}

function revisionActionCount(data: Record<string, unknown>) {
  if (Array.isArray(data.revision_actions)) return data.revision_actions.length
  const plan = recordValue(data.plan)
  const planActions = Array.isArray(plan.revision_actions) ? plan.revision_actions : []
  return planActions.length
}

function worldModelProposalPressureCount(data: Record<string, unknown>) {
  const pressure = recordValue(data.world_model_proposal_pressure)
  const total = numberValue(pressure.total_items)
  if (total !== null) return total
  return numberValue(data.pending_world_model_proposal_count)
}

function chapterReviewBaseDetailItems(data: Record<string, unknown>, statusLabel: string) {
  const items: Array<{ label: string; value: string }> = []
  const chapterIndex = numberValue(data.chapter_index)
  if (chapterIndex !== null) {
    items.push({ label: '章节', value: `第${chapterIndex}章` })
  }
  const status = stringValue(data.status)
  if (status) {
    items.push({ label: statusLabel, value: reviewStatusLabel(status) })
  }
  return items
}

function issueAndActionCountItems(data: Record<string, unknown>, actionLabel: string) {
  const items: Array<{ label: string; value: string }> = []
  const issues = Array.isArray(data.issues) ? data.issues : []
  if (issues.length) {
    items.push({ label: '问题', value: `${issues.length} 个` })
  }
  const actionCount = recommendedToolCount(data)
  if (actionCount > 0) {
    items.push({ label: actionLabel, value: `${actionCount} 个` })
  }
  return items
}

function recommendedToolCount(data: Record<string, unknown>) {
  if (Array.isArray(data.recommended_actions)) return data.recommended_actions.length
  if (Array.isArray(data.recommended_next_tools)) return data.recommended_next_tools.length
  if (Array.isArray(data.recommended_tools)) return data.recommended_tools.length
  return 0
}

function worldModelProposalCount(data: Record<string, unknown>) {
  const explicitCount = numberValue(data.proposal_count)
  if (explicitCount !== null) return explicitCount
  const proposals = Array.isArray(data.proposals) ? data.proposals : []
  if (proposals.length) return proposals.length
  const bundle = recordValue(data.proposal_bundle)
  const bundleItemCount = numberValue(bundle.item_count)
  if (bundleItemCount !== null) return bundleItemCount
  const diagnostic = recordValue(data.world_model_proposal_diagnostic)
  const pendingCount = numberValue(diagnostic.pending_count)
  if (pendingCount !== null) return pendingCount
  return null
}

function pushCountItem(items: Array<{ label: string; value: string }>, label: string, value: unknown, unit: string) {
  const count = numberValue(value)
  if (count !== null) {
    items.push({ label, value: unit ? `${count} ${unit}` : String(count) })
  }
}

function yesNoLabel(value: boolean) {
  return value ? '是' : '否'
}

function reviewStatusLabel(status: string) {
  if (status === 'passed') return '已通过'
  if (status === 'ready') return '就绪'
  if (status === 'success' || status === 'completed') return '成功'
  if (status === 'needs_revision') return '需修订'
  if (status === 'needs_attention') return '需处理'
  if (status === 'blocked') return '已阻塞'
  if (status === 'failed') return '失败'
  if (status === 'skipped') return '已跳过'
  return status || '未知'
}

function reviewActionVariant(innerStatus: string, actionStatus: string) {
  if (innerStatus === 'failed' || innerStatus === 'blocked' || actionStatus === 'failed') return 'error'
  if (innerStatus === 'needs_revision' || innerStatus === 'needs_attention' || innerStatus === 'skipped') return 'neutral'
  return statusVariant(actionStatus)
}

function worldModelBlockingVariant(status: string) {
  if (status === 'ready' || status === 'success' || status === 'completed') return 'success'
  if (status === 'blocked' || status === 'failed' || status === 'missing_profile') return 'error'
  return 'neutral'
}

function revisionStatusLabel(status: string) {
  if (status === 'ready') return '就绪'
  if (status === 'warning') return '有警告'
  if (status === 'drafted') return '已起草'
  if (status === 'completed' || status === 'success') return '成功'
  if (status === 'blocked') return '已阻塞'
  if (status === 'failed') return '失败'
  if (status === 'skipped') return '已跳过'
  return status || '未知'
}

function revisionVariant(status: string) {
  if (status === 'ready' || status === 'drafted' || status === 'completed' || status === 'success') return 'success'
  if (status === 'blocked' || status === 'failed') return 'error'
  return 'neutral'
}

function statusVariant(status: string) {
  if (status === 'success' || status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  return 'neutral'
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
