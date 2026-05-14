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
  | 'missing_chapter_anchor'

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
  sourceId?: string
  targetId?: string
}

export interface NarrativeAtlasGraph {
  nodes: NarrativeAtlasNode[]
  edges: NarrativeAtlasEdge[]
  warnings: NarrativeAtlasWarning[]
}

export interface NarrativeAtlasChapterRange {
  start: number
  end: number
}

export interface NarrativeAtlasMetrics {
  chapters: number
  plotlines: number
  foreshadowing: number
  events: number
}

export interface BuildNarrativeAtlasGraphInput {
  plan: AthenaEvolutionPlan | null
  chapters: ChapterSummary[]
  timeline: AthenaTimeline | null
  chapterRange?: NarrativeAtlasChapterRange
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
  const chapters = collectChapters(input.plan, input.chapters, chapterStatusByIndex, input.chapterRange)
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

  addPlotlines(input.plan, nodes, edges, warnings, knownNodeIds, knownEdgeIds, input.chapterRange)
  addForeshadowing(input.plan, chapters, nodes, edges, warnings, knownNodeIds, knownEdgeIds, input.chapterRange)
  addTimeline(input.timeline, nodes, edges, warnings, knownNodeIds, knownEdgeIds, input.chapterRange)

  return { nodes, edges, warnings }
}

export function collectNarrativeAtlasChapterIndexes(
  input: Pick<BuildNarrativeAtlasGraphInput, 'plan' | 'chapters'>,
): number[] {
  const chapterStatusByIndex = new Map(input.chapters.map((chapter) => [Number(chapter.chapter_index), chapter]))
  return collectChapters(input.plan, input.chapters, chapterStatusByIndex)
    .map((chapter) => chapter.chapterIndex)
}

export function collectNarrativeAtlasMetrics(input: BuildNarrativeAtlasGraphInput): NarrativeAtlasMetrics {
  const storylinePlotlines = asRecords(input.plan?.storyline?.plotlines)
  const plotlines = storylinePlotlines.length > 0 ? storylinePlotlines : asRecords(input.plan?.outline?.plotlines)
  const chapterTotal = toNonNegativeCount(input.plan?.outline?.chapters_total ?? input.plan?.outline?.total_chapters)
  const plotlineTotal = toNonNegativeCount(
    input.plan?.storyline?.plotlines_total ?? input.plan?.outline?.plotlines_total,
  )
  const foreshadowingTotal = toNonNegativeCount(input.plan?.storyline?.foreshadowing_total)

  return {
    chapters: chapterTotal ?? collectNarrativeAtlasChapterIndexes(input).length,
    plotlines: plotlineTotal ?? plotlines.length,
    foreshadowing: foreshadowingTotal ?? asRecords(input.plan?.storyline?.foreshadowing).length,
    events: Array.isArray(input.timeline?.events) ? input.timeline.events.length : 0,
  }
}

function toNonNegativeCount(value: unknown) {
  const count = toNumber(value)
  return count !== null && count >= 0 ? count : null
}

function collectChapters(
  plan: AthenaEvolutionPlan | null,
  chapters: ChapterSummary[],
  chapterStatusByIndex: Map<number, ChapterSummary>,
  chapterRange?: NarrativeAtlasChapterRange,
): ChapterAtlasRecord[] {
  const outlineChapters = asRecords(plan?.outline?.chapters)
  const source: RecordValue[] = outlineChapters.length > 0
    ? outlineChapters
    : chapters.map((chapter) => ({
        chapter_index: chapter.chapter_index,
        title: chapter.title,
        status: chapter.status,
        id: chapter.id,
      }))

  const atlasChapters: ChapterAtlasRecord[] = []
  for (const chapter of source) {
    const chapterIndex = toNumber(chapter.chapter_index ?? chapter.chapter)
    if (chapterIndex === null) continue
    if (!isChapterInRange(chapterIndex, chapterRange)) continue

    const liveChapter = chapterStatusByIndex.get(chapterIndex)
    atlasChapters.push({
      id: chapterId(chapterIndex),
      chapterIndex,
      title: toText(chapter.title, liveChapter?.title || `第${chapterIndex}章`),
      summary: toOptionalText(chapter.summary),
      status: liveChapter?.status ?? toOptionalText(chapter.status),
      raw: chapter,
    })
  }

  return atlasChapters.sort((left, right) => left.chapterIndex - right.chapterIndex)
}

function addPlotlines(
  plan: AthenaEvolutionPlan | null,
  nodes: NarrativeAtlasNode[],
  edges: NarrativeAtlasEdge[],
  warnings: NarrativeAtlasWarning[],
  knownNodeIds: Set<string>,
  knownEdgeIds: Set<string>,
  chapterRange?: NarrativeAtlasChapterRange,
) {
  const storylinePlotlines = asRecords(plan?.storyline?.plotlines)
  const plotlines = storylinePlotlines.length > 0 ? storylinePlotlines : asRecords(plan?.outline?.plotlines)

  for (const plotline of plotlines) {
    const rawMilestones = asRecords(plotline.milestones)
    const milestones = chapterRange
      ? rawMilestones.filter((milestone) => isRecordInChapterRange(milestone, chapterRange))
      : rawMilestones
    if (chapterRange && milestones.length === 0) continue

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
    for (const milestone of milestones) {
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
        const chapterNodeId = ensureChapterAnchor(chapterIndex, nodes, warnings, knownNodeIds, milestoneId)
        addEdge(edges, knownEdgeIds, {
          id: `branch:${chapterNodeId}->${milestoneId}`,
          type: 'branch',
          source: chapterNodeId,
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
  chapterRange?: NarrativeAtlasChapterRange,
) {
  const latestChapter = chapters.length > 0 ? chapters[chapters.length - 1] : undefined

  for (const item of asRecords(plan?.storyline?.foreshadowing)) {
    const hint = toText(item.hint ?? item.title ?? item.description, '未命名伏笔')
    const itemKey = slugify(readIdentity(item) ?? hint, 'foreshadowing')
    const foreshadowingId = uniqueNodeId(`foreshadowing:${itemKey}`, knownNodeIds)
    const plantedChapter = toNumber(item.planted_chapter ?? item.plantedChapter)
    const resolvedChapter = toNumber(item.resolved_chapter ?? item.resolvedChapter)
    if (chapterRange && !isChapterInRange(plantedChapter, chapterRange) && !isChapterInRange(resolvedChapter, chapterRange)) {
      continue
    }
    const status = toOptionalText(item.status) ?? 'unknown'

    addNode(nodes, knownNodeIds, {
      id: foreshadowingId,
      type: 'foreshadowing',
      label: hint,
      chapterIndex: foreshadowingChapterIndex(plantedChapter, resolvedChapter, chapterRange),
      status,
      raw: item,
    })

    if (plantedChapter === null) {
      addWarning(warnings, {
        id: uniqueWarningId(`warning:incomplete_foreshadowing:${itemKey}`, warnings),
        type: 'incomplete_foreshadowing',
        message: `伏笔「${hint}」缺少埋设章节。`,
        sourceId: foreshadowingId,
        targetId: foreshadowingId,
      })
      continue
    }

    if (isChapterInRange(plantedChapter, chapterRange)) {
      const plantedChapterId = ensureChapterAnchor(plantedChapter, nodes, warnings, knownNodeIds, foreshadowingId)
      addEdge(edges, knownEdgeIds, {
        id: `foreshadowing:${plantedChapterId}->${foreshadowingId}`,
        type: 'foreshadowing',
        source: plantedChapterId,
        target: foreshadowingId,
      })
    }

    if (status === 'resolved' && resolvedChapter !== null && isChapterInRange(resolvedChapter, chapterRange)) {
      const resolvedChapterId = ensureChapterAnchor(resolvedChapter, nodes, warnings, knownNodeIds, foreshadowingId)
      addEdge(edges, knownEdgeIds, {
        id: `foreshadowing:${foreshadowingId}->${resolvedChapterId}`,
        type: 'foreshadowing',
        source: foreshadowingId,
        target: resolvedChapterId,
      })
      continue
    }

    if (status === 'resolved' && resolvedChapter === null) {
      addWarning(warnings, {
        id: uniqueWarningId(`warning:incomplete_foreshadowing:${itemKey}`, warnings),
        type: 'incomplete_foreshadowing',
        message: `伏笔「${hint}」标记为已回收但缺少回收章节。`,
        sourceId: foreshadowingId,
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
      id: uniqueWarningId(`warning:unresolved_foreshadowing:${itemKey}`, warnings),
      type: 'unresolved_foreshadowing',
      message: `伏笔「${hint}」尚未回收。`,
      sourceId: foreshadowingId,
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
  chapterRange?: NarrativeAtlasChapterRange,
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
    if (chapterRange && !isChapterInRange(chapterIndex, chapterRange)) continue
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
      const chapterNodeId = ensureChapterAnchor(chapterIndex, nodes, warnings, knownNodeIds, eventId)
      addEdge(edges, knownEdgeIds, {
        id: `event_anchor:${chapterNodeId}->${eventId}`,
        type: 'event_anchor',
        source: chapterNodeId,
        target: eventId,
      })
    }
  }
}

function ensureChapterAnchor(
  chapterIndex: number,
  nodes: NarrativeAtlasNode[],
  warnings: NarrativeAtlasWarning[],
  knownNodeIds: Set<string>,
  sourceId: string,
): string {
  const id = chapterId(chapterIndex)
  const isMissing = !knownNodeIds.has(id)
  if (isMissing) {
    addNode(nodes, knownNodeIds, {
      id,
      type: 'chapter',
      label: `第${chapterIndex}章`,
      chapterIndex,
      status: 'incomplete',
    })

    addWarning(warnings, {
      id: `warning:missing_chapter_anchor:${sourceId}->${id}`,
      type: 'missing_chapter_anchor',
      message: `章节锚点「${id}」缺少章节规划，已创建占位节点。`,
      sourceId,
      targetId: id,
    })
  }

  return id
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

function uniqueWarningId(baseId: string, warnings: NarrativeAtlasWarning[]): string {
  if (!warnings.some((warning) => warning.id === baseId)) return baseId

  let suffix = 2
  let candidate = `${baseId}:${suffix}`
  while (warnings.some((warning) => warning.id === candidate)) {
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
  return toOptionalText(identity) ?? null
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

function isChapterInRange(chapterIndex: number | null, chapterRange?: NarrativeAtlasChapterRange): boolean {
  if (!chapterRange) return chapterIndex !== null
  return chapterIndex !== null && chapterIndex >= chapterRange.start && chapterIndex <= chapterRange.end
}

function isRecordInChapterRange(record: RecordValue, chapterRange?: NarrativeAtlasChapterRange): boolean {
  return isChapterInRange(toNumber(record.chapter_index ?? record.chapter), chapterRange)
}

function foreshadowingChapterIndex(
  plantedChapter: number | null,
  resolvedChapter: number | null,
  chapterRange?: NarrativeAtlasChapterRange,
): number | undefined {
  if (!chapterRange) return plantedChapter ?? undefined
  return (isChapterInRange(plantedChapter, chapterRange) ? plantedChapter : resolvedChapter) ?? undefined
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
