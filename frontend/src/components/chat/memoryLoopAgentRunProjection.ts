import type { ActionResultView } from '../../api/types'

export const MEMORY_LOOP_AGENT_RUN_ACTION_TYPES = [
  'search_agent_retrieval_context',
  'plan_post_chapter_memory_capture',
] as const

export type MemoryLoopAgentRunActionType = typeof MEMORY_LOOP_AGENT_RUN_ACTION_TYPES[number]

export interface MemoryLoopAgentRunActionDescriptor {
  type: MemoryLoopAgentRunActionType
  buildView: (actionResult: Record<string, unknown>, status: string) => ActionResultView
}

export const MEMORY_LOOP_AGENT_RUN_ACTION_DESCRIPTORS: Record<MemoryLoopAgentRunActionType, MemoryLoopAgentRunActionDescriptor> = {
  search_agent_retrieval_context: {
    type: 'search_agent_retrieval_context',
    buildView: buildRetrievalContextActionResultView,
  },
  plan_post_chapter_memory_capture: {
    type: 'plan_post_chapter_memory_capture',
    buildView: buildPostChapterMemoryCaptureActionResultView,
  },
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
