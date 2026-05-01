import type { AthenaEvolutionPlan, AthenaTimeline, ChapterSummary } from '../../api/types'

export type NarrativeAtlasNodeType =
  | 'chapter'
  | 'chapter_group'
  | 'plotline'
  | 'milestone'
  | 'foreshadowing'
  | 'event'

export type NarrativeAtlasEdgeType = 'trunk' | 'branch' | 'foreshadowing' | 'event_anchor'

export type NarrativeAtlasWarningType =
  | 'timeline_missing'
  | 'unresolved_foreshadowing'
  | 'incomplete_foreshadowing'

export interface NarrativeAtlasNode {
  id: string
  type: NarrativeAtlasNodeType
  label: string
  chapterIndex?: number
  summary?: string
  status?: string
  raw?: Record<string, unknown>
}

export interface NarrativeAtlasEdge {
  id: string
  type: NarrativeAtlasEdgeType
  source: string
  target: string
  label?: string
}

export interface NarrativeAtlasWarning {
  id: string
  type: NarrativeAtlasWarningType
  message: string
  targetId?: string
}

export interface NarrativeAtlasGraph {
  nodes: NarrativeAtlasNode[]
  edges: NarrativeAtlasEdge[]
  warnings: NarrativeAtlasWarning[]
}

export interface BuildNarrativeAtlasGraphInput {
  plan: AthenaEvolutionPlan | null
  chapters: ChapterSummary[]
  timeline: AthenaTimeline | null
}

type RecordValue = Record<string, unknown>

interface ChapterAtlasRecord {
  id: string
  chapterIndex: number
  title: string
  summary?: string
  status?: string
  raw?: RecordValue
}

export function buildNarrativeAtlasGraph(input: BuildNarrativeAtlasGraphInput): NarrativeAtlasGraph {
  const nodes: NarrativeAtlasNode[] = []
  const edges: NarrativeAtlasEdge[] = []
  const warnings: NarrativeAtlasWarning[] = []
  const chapterStatusByIndex = new Map(input.chapters.map((chapter) => [Number(chapter.chapter_index), chapter]))
  const chapters = collectChapters(input.plan, input.chapters, chapterStatusByIndex)
  const knownNodeIds = new Set<string>()
  const knownEdgeIds = new Set<string>()

  for (const chapter of chapters) {
    addNode(nodes, knownNodeIds, {
      id: chapter.id,
      type: 'chapter',
      label: chapter.title,
      chapterIndex: chapter.chapterIndex,
      summary: chapter.summary,
      status: chapter.status,
      raw: chapter.raw,
    })
  }

  for (let index = 1; index < chapters.length; index += 1) {
    addEdge(edges, knownEdgeIds, {
      id: `trunk:${chapters[index - 1].id}->${chapters[index].id}`,
      type: 'trunk',
      source: chapters[index - 1].id,
      target: chapters[index].id,
    })
  }

  addPlotlines(input.plan, nodes, edges, knownNodeIds, knownEdgeIds)
  addForeshadowing(input.plan, chapters, nodes, edges, warnings, knownNodeIds, knownEdgeIds)
  addTimeline(input.timeline, nodes, edges, warnings, knownNodeIds, knownEdgeIds)

  return { nodes, edges, warnings }
}

function collectChapters(
  plan: AthenaEvolutionPlan | null,
  chapters: ChapterSummary[],
  chapterStatusByIndex: Map<number, ChapterSummary>,
): ChapterAtlasRecord[] {
  const outlineChapters = asRecords(plan?.outline?.chapters)
  const source = outlineChapters.length > 0
    ? outlineChapters
    : chapters.map((chapter) => ({
        chapter_index: chapter.chapter_index,
        title: chapter.title,
        status: chapter.status,
        rawId: chapter.id,
      }))

  return source
    .map((chapter) => {
      const chapterIndex = toNumber(chapter.chapter_index ?? chapter.chapter)
      if (chapterIndex === null) return null

      const liveChapter = chapterStatusByIndex.get(chapterIndex)
      return {
        id: chapterId(chapterIndex),
        chapterIndex,
        title: toText(chapter.title, liveChapter?.title || `第${chapterIndex}章`),
        summary: toOptionalText(chapter.summary),
        status: liveChapter?.status ?? toOptionalText(chapter.status),
        raw: chapter,
      } satisfies ChapterAtlasRecord
    })
    .filter((chapter): chapter is ChapterAtlasRecord => chapter !== null)
    .sort((left, right) => left.chapterIndex - right.chapterIndex)
}

function addPlotlines(
  plan: AthenaEvolutionPlan | null,
  nodes: NarrativeAtlasNode[],
  edges: NarrativeAtlasEdge[],
  knownNodeIds: Set<string>,
  knownEdgeIds: Set<string>,
) {
  const storylinePlotlines = asRecords(plan?.storyline?.plotlines)
  const plotlines = storylinePlotlines.length > 0 ? storylinePlotlines : asRecords(plan?.outline?.plotlines)

  for (const plotline of plotlines) {
    const name = toText(plotline.name ?? plotline.title, '未命名故事线')
    const plotlineKey = slugify(readIdentity(plotline) ?? name, 'plotline')
    const plotlineId = uniqueNodeId(`plotline:${plotlineKey}`, knownNodeIds)

    addNode(nodes, knownNodeIds, {
      id: plotlineId,
      type: 'plotline',
      label: name,
      status: toOptionalText(plotline.status ?? plotline.type),
      raw: plotline,
    })

    const plotlineNodeKey = plotlineId.startsWith('plotline:') ? plotlineId.slice('plotline:'.length) : plotlineKey
    for (const milestone of asRecords(plotline.milestones)) {
      const label = toText(milestone.title ?? milestone.event ?? milestone.summary ?? milestone.description, '未命名节点')
      const chapterIndex = toNumber(milestone.chapter_index ?? milestone.chapter)
      const milestoneKey = slugify(readIdentity(milestone) ?? label, 'milestone')
      const milestoneId = uniqueNodeId(`milestone:${plotlineNodeKey}:${milestoneKey}`, knownNodeIds)

      addNode(nodes, knownNodeIds, {
        id: milestoneId,
        type: 'milestone',
        label,
        chapterIndex: chapterIndex ?? undefined,
        summary: uniqueSummary(toOptionalText(milestone.summary ?? milestone.description ?? milestone.event), label),
        status: toOptionalText(milestone.status),
        raw: milestone,
      })
      addEdge(edges, knownEdgeIds, {
        id: `branch:${plotlineId}->${milestoneId}`,
        type: 'branch',
        source: plotlineId,
        target: milestoneId,
      })

      if (chapterIndex !== null) {
        addEdge(edges, knownEdgeIds, {
          id: `branch:${chapterId(chapterIndex)}->${milestoneId}`,
          type: 'branch',
          source: chapterId(chapterIndex),
          target: milestoneId,
        })
      }
    }
  }
}

function addForeshadowing(
  plan: AthenaEvolutionPlan | null,
  chapters: ChapterAtlasRecord[],
  nodes: NarrativeAtlasNode[],
  edges: NarrativeAtlasEdge[],
  warnings: NarrativeAtlasWarning[],
  knownNodeIds: Set<string>,
  knownEdgeIds: Set<string>,
) {
  const latestChapter = chapters.at(-1)

  for (const item of asRecords(plan?.storyline?.foreshadowing)) {
    const hint = toText(item.hint ?? item.title ?? item.description, '未命名伏笔')
    const itemKey = slugify(readIdentity(item) ?? hint, 'foreshadowing')
    const foreshadowingId = uniqueNodeId(`foreshadowing:${itemKey}`, knownNodeIds)
    const plantedChapter = toNumber(item.planted_chapter ?? item.plantedChapter)
    const resolvedChapter = toNumber(item.resolved_chapter ?? item.resolvedChapter)
    const status = toOptionalText(item.status) ?? 'unknown'

    addNode(nodes, knownNodeIds, {
      id: foreshadowingId,
      type: 'foreshadowing',
      label: hint,
      chapterIndex: plantedChapter ?? undefined,
      status,
      raw: item,
    })

    if (plantedChapter === null) {
      addWarning(warnings, {
        id: `warning:incomplete_foreshadowing:${itemKey}`,
        type: 'incomplete_foreshadowing',
        message: `伏笔「${hint}」缺少埋设章节。`,
        targetId: foreshadowingId,
      })
      continue
    }

    addEdge(edges, knownEdgeIds, {
      id: `foreshadowing:${chapterId(plantedChapter)}->${foreshadowingId}`,
      type: 'foreshadowing',
      source: chapterId(plantedChapter),
      target: foreshadowingId,
    })

    if (status === 'resolved' && resolvedChapter !== null) {
      addEdge(edges, knownEdgeIds, {
        id: `foreshadowing:${foreshadowingId}->${chapterId(resolvedChapter)}`,
        type: 'foreshadowing',
        source: foreshadowingId,
        target: chapterId(resolvedChapter),
      })
      continue
    }

    if (status === 'resolved' && resolvedChapter === null) {
      addWarning(warnings, {
        id: `warning:incomplete_foreshadowing:${itemKey}`,
        type: 'incomplete_foreshadowing',
        message: `伏笔「${hint}」标记为已回收但缺少回收章节。`,
        targetId: foreshadowingId,
      })
      continue
    }

    if (latestChapter) {
      addEdge(edges, knownEdgeIds, {
        id: `foreshadowing:${foreshadowingId}->${latestChapter.id}`,
        type: 'foreshadowing',
        source: foreshadowingId,
        target: latestChapter.id,
      })
    }

    addWarning(warnings, {
      id: `warning:unresolved_foreshadowing:${itemKey}`,
      type: 'unresolved_foreshadowing',
      message: `伏笔「${hint}」尚未回收。`,
      targetId: foreshadowingId,
    })
  }
}

function addTimeline(
  timeline: AthenaTimeline | null,
  nodes: NarrativeAtlasNode[],
  edges: NarrativeAtlasEdge[],
  warnings: NarrativeAtlasWarning[],
  knownNodeIds: Set<string>,
  knownEdgeIds: Set<string>,
) {
  const events = Array.isArray(timeline?.events) ? timeline.events : []

  if (events.length === 0) {
    addWarning(warnings, {
      id: 'warning:timeline_missing',
      type: 'timeline_missing',
      message: '时间线事件缺失，图谱仅展示章节与叙事规划数据。',
    })
    return
  }

  for (const event of events) {
    const eventRecord = event as RecordValue
    const eventKey = toText(event.event_id ?? event.id, `chapter-${event.chapter_index}-${event.intra_chapter_seq}`)
    const eventId = uniqueNodeId(`event:${eventKey}`, knownNodeIds)
    const chapterIndex = toNumber(event.chapter_index)
    const label = toText(event.description, toText(event.event_type, eventKey))

    addNode(nodes, knownNodeIds, {
      id: eventId,
      type: 'event',
      label,
      chapterIndex: chapterIndex ?? undefined,
      status: toOptionalText(event.event_type),
      raw: eventRecord,
    })

    if (chapterIndex !== null) {
      addEdge(edges, knownEdgeIds, {
        id: `event_anchor:${chapterId(chapterIndex)}->${eventId}`,
        type: 'event_anchor',
        source: chapterId(chapterIndex),
        target: eventId,
      })
    }
  }
}

function addNode(nodes: NarrativeAtlasNode[], knownNodeIds: Set<string>, node: NarrativeAtlasNode) {
  if (knownNodeIds.has(node.id)) return

  knownNodeIds.add(node.id)
  nodes.push(node)
}

function addEdge(edges: NarrativeAtlasEdge[], knownEdgeIds: Set<string>, edge: NarrativeAtlasEdge) {
  if (knownEdgeIds.has(edge.id)) return

  knownEdgeIds.add(edge.id)
  edges.push(edge)
}

function addWarning(warnings: NarrativeAtlasWarning[], warning: NarrativeAtlasWarning) {
  if (warnings.some((item) => item.id === warning.id)) return

  warnings.push(warning)
}

function uniqueNodeId(baseId: string, knownIds: Set<string>): string {
  if (!knownIds.has(baseId)) return baseId

  let suffix = 2
  let candidate = `${baseId}:${suffix}`
  while (knownIds.has(candidate)) {
    suffix += 1
    candidate = `${baseId}:${suffix}`
  }
  return candidate
}

function chapterId(chapterIndex: number): string {
  return `chapter:${chapterIndex}`
}

function asRecords(value: unknown): RecordValue[] {
  return Array.isArray(value) ? value.filter(isRecord) : []
}

function isRecord(value: unknown): value is RecordValue {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function readIdentity(record: RecordValue): string | null {
  const identity = record.id ?? record.plotline_id ?? record.milestone_id ?? record.foreshadowing_id
  return toOptionalText(identity)
}

function toText(value: unknown, fallback = ''): string {
  const text = toOptionalText(value)
  return text ?? fallback
}

function toOptionalText(value: unknown): string | undefined {
  if (typeof value === 'string' && value.trim()) return value.trim()
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  return undefined
}

function toNumber(value: unknown): number | null {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : null
}

function slugify(value: string, fallback: string): string {
  const slug = value
    .normalize('NFKC')
    .trim()
    .replace(/[\s\p{P}\p{S}]+/gu, '')

  return slug || fallback
}

function uniqueSummary(summary: string | undefined, title: string): string | undefined {
  return summary && summary !== title ? summary : undefined
}
