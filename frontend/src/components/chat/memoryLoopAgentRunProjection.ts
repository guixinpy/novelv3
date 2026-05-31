import type { ActionResultView } from '../../api/types'

export const MEMORY_LOOP_AGENT_RUN_ACTION_TYPES = [
  'inspect_agent_memory_activation_plan',
  'search_agent_retrieval_context',
  'plan_post_chapter_memory_capture',
] as const

export type MemoryLoopAgentRunActionType = typeof MEMORY_LOOP_AGENT_RUN_ACTION_TYPES[number]

export interface MemoryLoopAgentRunActionDescriptor {
  type: MemoryLoopAgentRunActionType
  buildView: (actionResult: Record<string, unknown>, status: string) => ActionResultView
}

export const MEMORY_LOOP_AGENT_RUN_ACTION_DESCRIPTORS: Record<MemoryLoopAgentRunActionType, MemoryLoopAgentRunActionDescriptor> = {
  inspect_agent_memory_activation_plan: {
    type: 'inspect_agent_memory_activation_plan',
    buildView: buildMemoryActivationActionResultView,
  },
  search_agent_retrieval_context: {
    type: 'search_agent_retrieval_context',
    buildView: buildRetrievalContextActionResultView,
  },
  plan_post_chapter_memory_capture: {
    type: 'plan_post_chapter_memory_capture',
    buildView: buildPostChapterMemoryCaptureActionResultView,
  },
}

function buildMemoryActivationActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const activationStatus = stringValue(data.status) || status
  const detailItems = memoryActivationDetailItems(data)
  return {
    type: 'inspect_agent_memory_activation_plan',
    status,
    label: memoryActivationLabel(activationStatus, status),
    variant: memoryLoopVariant(activationStatus, status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildRetrievalContextActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const retrievalStatus = stringValue(data.status) || status
  const detailItems = retrievalContextDetailItems(data)
  return {
    type: 'search_agent_retrieval_context',
    status,
    label: retrievalContextLabel(retrievalStatus, data),
    variant: memoryLoopVariant(retrievalStatus, status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function buildPostChapterMemoryCaptureActionResultView(actionResult: Record<string, unknown>, status: string): ActionResultView {
  const data = recordValue(actionResult.data)
  const captureStatus = stringValue(data.capture_status) || stringValue(data.status) || status
  const detailItems = postChapterMemoryCaptureDetailItems(data)
  return {
    type: 'plan_post_chapter_memory_capture',
    status,
    label: postChapterMemoryCaptureLabel(captureStatus, status),
    variant: memoryLoopVariant(captureStatus, status),
    ...(detailItems.length ? { detail_items: detailItems } : {}),
  }
}

function memoryActivationDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const activationStatus = stringValue(data.status)
  if (activationStatus) {
    items.push({ label: '写前激活', value: memoryActivationStatusLabel(activationStatus) })
  }

  const coverage = recordValue(data.coverage)
  const counts = Object.keys(recordValue(coverage.activated_counts)).length
    ? recordValue(coverage.activated_counts)
    : recordValue(data.activated_counts)
  pushCountItem(items, '长篇记忆', counts.longform, '个')
  pushCountItem(items, '伏笔', counts.foreshadowing, '个')
  pushCountItem(items, '知识库经验', counts.knowledge_base, '个')

  const nextToolCount = recommendedToolCount(data)
  if (nextToolCount > 0) {
    items.push({ label: '下一步', value: `${nextToolCount} 个工具` })
  }
  return items
}

function retrievalContextDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const summary = recordValue(data.summary)
  const returned = numberValue(summary.returned)
  const total = numberValue(summary.total)
  const coverage = retrievalCoverageLabel(returned, total)
  if (coverage) {
    items.push({ label: '检索证据', value: coverage })
  }

  const primarySource = retrievalPrimarySourceLabel(recordList(data.items)[0])
  if (primarySource) {
    items.push({ label: '首个来源', value: primarySource })
  }

  const nextToolCount = recommendedToolCount(data)
  if (nextToolCount > 0) {
    items.push({ label: '下一步', value: `${nextToolCount} 个工具` })
  }
  return items
}

function postChapterMemoryCaptureDetailItems(data: Record<string, unknown>) {
  const items: Array<{ label: string; value: string }> = []
  const chapterIndex = numberValue(data.chapter_index)
  if (chapterIndex !== null) {
    items.push({ label: '章节', value: `第${chapterIndex}章` })
  }

  const captureStatus = stringValue(data.capture_status)
  if (captureStatus) {
    items.push({ label: '写后记忆', value: postChapterMemoryCaptureStatusLabel(captureStatus) })
  }

  const summary = recordValue(data.summary)
  pushCountItem(items, '候选', summary.candidate_count, '个')
  pushCountItem(items, '审稿证据', summary.review_step_count, '个')

  const nextToolCount = recommendedToolCount(data)
  if (nextToolCount > 0) {
    items.push({ label: '下一步', value: `${nextToolCount} 个工具` })
  }
  return items
}

function memoryActivationLabel(activationStatus: string, actionStatus: string) {
  if (actionStatus === 'failed' || activationStatus === 'failed') return '写前记忆激活失败'
  if (actionStatus === 'running' || activationStatus === 'running') return '写前记忆激活中'
  if (activationStatus === 'ready' || activationStatus === 'completed' || activationStatus === 'success') {
    return '写前记忆已激活'
  }
  if (activationStatus === 'degraded') return '写前记忆降级激活'
  if (activationStatus === 'blocked') return '写前记忆已阻止'
  return `写前记忆: ${activationStatus || '未知状态'}`
}

function retrievalContextLabel(status: string, data: Record<string, unknown>) {
  if (status === 'failed') return '检索证据获取失败'
  if (status === 'running') return '检索证据检索中'
  const summary = recordValue(data.summary)
  const returned = numberValue(summary.returned)
  if (returned === 0) return '检索证据为空'
  if (status === 'completed' || status === 'success') return '检索证据已返回'
  return `检索证据: ${status || '未知状态'}`
}

function postChapterMemoryCaptureLabel(captureStatus: string, actionStatus: string) {
  if (actionStatus === 'failed' || captureStatus === 'failed') return '写后记忆规划失败'
  if (actionStatus === 'running' || captureStatus === 'running') return '写后记忆规划中'
  if (captureStatus === 'ready') return '写后记忆候选已规划'
  if (captureStatus === 'needs_review') return '写后记忆等待审稿'
  if (captureStatus === 'missing_chapter') return '写后记忆缺少章节'
  if (captureStatus === 'completed' || captureStatus === 'success') return '写后记忆规划已完成'
  return `写后记忆规划: ${captureStatus || '未知状态'}`
}

function memoryActivationStatusLabel(status: string) {
  if (status === 'ready') return '已激活'
  if (status === 'degraded') return '降级激活'
  if (status === 'blocked') return '已阻止'
  if (status === 'completed' || status === 'success') return '完成'
  return status || '未知'
}

function postChapterMemoryCaptureStatusLabel(status: string) {
  if (status === 'ready') return '可写入候选'
  if (status === 'needs_review') return '需要审稿'
  if (status === 'missing_chapter') return '缺少章节'
  if (status === 'completed' || status === 'success') return '完成'
  return status || '未知'
}

function retrievalCoverageLabel(returned: number | null, total: number | null) {
  if (returned !== null && total !== null) return `返回 ${returned} / 共 ${total}`
  if (returned !== null) return `返回 ${returned}`
  if (total !== null) return `共 ${total}`
  return ''
}

function retrievalPrimarySourceLabel(item: Record<string, unknown> | undefined) {
  if (!item) return ''
  const title = stringValue(item.title) || stringValue(item.source_ref)
  const chapterIndex = numberValue(item.chapter_index)
  const chapter = chapterIndex !== null ? `第${chapterIndex}章` : ''
  const sourceType = retrievalSourceTypeLabel(stringValue(item.source_type))
  return [title, chapter || sourceType].filter(Boolean).join(' · ')
}

function retrievalSourceTypeLabel(sourceType: string) {
  if (sourceType === 'knowledge_base_candidate') return '知识库候选'
  if (sourceType === 'longform_memory') return '长篇记忆'
  if (sourceType === 'world_fact') return '世界事实'
  return ''
}

function memoryLoopVariant(innerStatus: string, actionStatus: string) {
  if (innerStatus === 'failed' || innerStatus === 'blocked' || actionStatus === 'failed') return 'error'
  if (innerStatus === 'needs_review' || innerStatus === 'missing_chapter' || innerStatus === 'skipped') return 'neutral'
  return statusVariant(actionStatus)
}

function statusVariant(status: string) {
  if (status === 'success' || status === 'completed') return 'success'
  if (status === 'failed') return 'error'
  return 'neutral'
}

function recommendedToolCount(data: Record<string, unknown>) {
  return Array.isArray(data.recommended_next_tools) ? data.recommended_next_tools.length : 0
}

function pushCountItem(items: Array<{ label: string; value: string }>, label: string, value: unknown, unit: string) {
  const count = numberValue(value)
  if (count !== null) {
    items.push({ label, value: `${count} ${unit}` })
  }
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function recordList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is Record<string, unknown> => Boolean(item && typeof item === 'object' && !Array.isArray(item)))
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
}

function numberValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}
