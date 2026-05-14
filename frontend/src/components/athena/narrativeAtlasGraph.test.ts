import { describe, expect, it } from 'vitest'
import { buildNarrativeAtlasGraph } from './narrativeAtlasGraph'
import type { AthenaEvolutionPlan, AthenaTimeline, ChapterSummary } from '../../api/types'

const chapters: ChapterSummary[] = [
  { id: 'chapter-1', chapter_index: 1, title: '异常信号', word_count: 1200, status: 'draft' },
  { id: 'chapter-2', chapter_index: 2, title: '灯塔回声', word_count: 1800, status: 'draft' },
  { id: 'chapter-3', chapter_index: 3, title: '潮汐门', word_count: 2200, status: 'done' },
]

const plan = {
  outline: {
    id: 'outline-1',
    status: 'generated',
    total_chapters: 3,
    chapters: [
      { chapter_index: 1, title: '异常信号', summary: '潮汐门出现异常读数。' },
      { chapter_index: 2, title: '灯塔回声', summary: '林澈抵达旧灯塔。' },
      { chapter_index: 3, title: '潮汐门', summary: '旧计划浮出水面。' },
    ],
    plotlines: [
      {
        name: '副线：灯塔守夜',
        type: 'subplot',
        milestones: [
          { chapter: 2, event: '第一次看到灯塔' },
        ],
      },
    ],
  },
  storyline: {
    id: 'storyline-1',
    status: 'generated',
    plotlines: [
      {
        name: '主线：潮汐根源',
        type: 'main',
        milestones: [
          { chapter_index: 1, title: '发现异常', summary: '读数指向旧计划。' },
          { chapter: 3, event: '确认潮汐门真相' },
        ],
      },
    ],
    foreshadowing: [
      {
        hint: '普罗米修斯-意识锚点文件',
        planted_chapter: 1,
        resolved_chapter: 3,
        status: 'resolved',
      },
      {
        hint: '潮汐钟慢了三分钟',
        planted_chapter: 2,
        status: 'pending',
      },
      {
        hint: '没有源头的警报',
        resolved_chapter: 3,
        status: 'resolved',
      },
    ],
  },
} as unknown as AthenaEvolutionPlan

describe('narrativeAtlasGraph', () => {
  it('builds a stable chapter spine from outline chapters', () => {
    const graph = buildNarrativeAtlasGraph({ plan, chapters, timeline: null })

    expect(graph.nodes.filter((node) => node.type === 'chapter')).toMatchObject([
      { id: 'chapter:1', label: '异常信号', chapterIndex: 1 },
      { id: 'chapter:2', label: '灯塔回声', chapterIndex: 2 },
      { id: 'chapter:3', label: '潮汐门', chapterIndex: 3 },
    ])
    expect(graph.edges.filter((edge) => edge.type === 'trunk')).toEqual([
      { id: 'trunk:chapter:1->chapter:2', type: 'trunk', source: 'chapter:1', target: 'chapter:2' },
      { id: 'trunk:chapter:2->chapter:3', type: 'trunk', source: 'chapter:2', target: 'chapter:3' },
    ])
  })

  it('maps plotline milestones to branch nodes and edges', () => {
    const graph = buildNarrativeAtlasGraph({ plan, chapters, timeline: null })

    expect(graph.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'plotline:主线潮汐根源', type: 'plotline', label: '主线：潮汐根源' }),
      expect.objectContaining({ id: 'milestone:主线潮汐根源:发现异常', type: 'milestone', label: '发现异常', chapterIndex: 1 }),
      expect.objectContaining({ id: 'milestone:主线潮汐根源:确认潮汐门真相', type: 'milestone', label: '确认潮汐门真相', chapterIndex: 3 }),
    ]))
    expect(graph.edges).toEqual(expect.arrayContaining([
      { id: 'branch:plotline:主线潮汐根源->milestone:主线潮汐根源:发现异常', type: 'branch', source: 'plotline:主线潮汐根源', target: 'milestone:主线潮汐根源:发现异常' },
      { id: 'branch:chapter:1->milestone:主线潮汐根源:发现异常', type: 'branch', source: 'chapter:1', target: 'milestone:主线潮汐根源:发现异常' },
      { id: 'branch:chapter:3->milestone:主线潮汐根源:确认潮汐门真相', type: 'branch', source: 'chapter:3', target: 'milestone:主线潮汐根源:确认潮汐门真相' },
    ]))
  })

  it('creates resolved, pending, and incomplete foreshadowing edges', () => {
    const graph = buildNarrativeAtlasGraph({ plan, chapters, timeline: null })

    expect(graph.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'foreshadowing:普罗米修斯意识锚点文件', type: 'foreshadowing', label: '普罗米修斯-意识锚点文件' }),
      expect.objectContaining({ id: 'foreshadowing:潮汐钟慢了三分钟', type: 'foreshadowing', label: '潮汐钟慢了三分钟' }),
    ]))
    expect(graph.edges).toEqual(expect.arrayContaining([
      { id: 'foreshadowing:chapter:1->foreshadowing:普罗米修斯意识锚点文件', type: 'foreshadowing', source: 'chapter:1', target: 'foreshadowing:普罗米修斯意识锚点文件' },
      { id: 'foreshadowing:foreshadowing:普罗米修斯意识锚点文件->chapter:3', type: 'foreshadowing', source: 'foreshadowing:普罗米修斯意识锚点文件', target: 'chapter:3' },
      { id: 'foreshadowing:chapter:2->foreshadowing:潮汐钟慢了三分钟', type: 'foreshadowing', source: 'chapter:2', target: 'foreshadowing:潮汐钟慢了三分钟' },
      { id: 'foreshadowing:foreshadowing:潮汐钟慢了三分钟->chapter:3', type: 'foreshadowing', source: 'foreshadowing:潮汐钟慢了三分钟', target: 'chapter:3' },
    ]))
    expect(graph.warnings).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'warning:unresolved_foreshadowing:潮汐钟慢了三分钟', type: 'unresolved_foreshadowing', targetId: 'foreshadowing:潮汐钟慢了三分钟' }),
      expect.objectContaining({ id: 'warning:incomplete_foreshadowing:没有源头的警报', type: 'incomplete_foreshadowing' }),
    ]))
  })

  it('includes timeline events without requiring timeline data for the graph to exist', () => {
    const missingTimelineGraph = buildNarrativeAtlasGraph({ plan, chapters, timeline: null })

    expect(missingTimelineGraph.nodes.some((node) => node.type === 'chapter')).toBe(true)
    expect(missingTimelineGraph.warnings).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'warning:timeline_missing', type: 'timeline_missing' }),
    ]))

    const timeline: AthenaTimeline = {
      anchors: [],
      events: [
        {
          id: 'event-row-1',
          event_id: 'event.tidegate.alert',
          chapter_index: 2,
          intra_chapter_seq: 1,
          event_type: 'discovery',
          description: '潮汐门警报触发。',
        },
      ],
    }
    const graph = buildNarrativeAtlasGraph({ plan, chapters, timeline })

    expect(graph.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'event:event.tidegate.alert', type: 'event', label: '潮汐门警报触发。', chapterIndex: 2 }),
    ]))
    expect(graph.edges).toEqual(expect.arrayContaining([
      { id: 'event_anchor:chapter:2->event:event.tidegate.alert', type: 'event_anchor', source: 'chapter:2', target: 'event:event.tidegate.alert' },
    ]))
    expect(graph.warnings.some((warning) => warning.type === 'timeline_missing')).toBe(false)
  })

  it('creates placeholder chapters for missing anchors so edges never dangle', () => {
    const sparsePlan = {
      outline: {
        id: 'outline-sparse',
        status: 'generated',
        total_chapters: 1,
        chapters: [
          { chapter_index: 1, title: '唯一章节' },
        ],
        plotlines: [],
      },
      storyline: {
        id: 'storyline-sparse',
        status: 'generated',
        plotlines: [
          {
            name: '远端线索',
            milestones: [
              { chapter_index: 5, title: '第五章节点' },
            ],
          },
        ],
        foreshadowing: [
          {
            hint: '第五章埋设',
            planted_chapter: 5,
            resolved_chapter: 5,
            status: 'resolved',
          },
        ],
      },
    } as unknown as AthenaEvolutionPlan
    const timeline: AthenaTimeline = {
      anchors: [],
      events: [
        {
          id: 'event-row-5',
          event_id: 'event.chapter.five',
          chapter_index: 5,
          intra_chapter_seq: 1,
          event_type: 'reveal',
          description: '第五章事件。',
        },
      ],
    }

    const graph = buildNarrativeAtlasGraph({
      plan: sparsePlan,
      chapters: [{ id: 'chapter-1', chapter_index: 1, title: '唯一章节', word_count: 1000, status: 'draft' }],
      timeline,
    })
    const nodeIds = new Set(graph.nodes.map((node) => node.id))

    expect(graph.edges.every((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))).toBe(true)
    expect(graph.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'chapter:5', type: 'chapter', label: '第5章', chapterIndex: 5, status: 'incomplete' }),
    ]))
    expect(graph.warnings).toEqual(expect.arrayContaining([
      expect.objectContaining({ type: 'missing_chapter_anchor', targetId: 'chapter:5' }),
    ]))
  })

  it('keeps duplicate foreshadowing warnings attached to their unique nodes', () => {
    const duplicatePlan = {
      outline: {
        id: 'outline-duplicate',
        status: 'generated',
        total_chapters: 2,
        chapters: [
          { chapter_index: 1, title: '开端' },
          { chapter_index: 2, title: '追踪' },
        ],
        plotlines: [],
      },
      storyline: {
        id: 'storyline-duplicate',
        status: 'generated',
        plotlines: [],
        foreshadowing: [
          { hint: '同一枚钥匙', planted_chapter: 1, status: 'pending' },
          { hint: '同一枚钥匙', planted_chapter: 2, status: 'pending' },
        ],
      },
    } as unknown as AthenaEvolutionPlan

    const graph = buildNarrativeAtlasGraph({ plan: duplicatePlan, chapters: [], timeline: null })
    const foreshadowingIds = new Set(
      graph.nodes.filter((node) => node.type === 'foreshadowing').map((node) => node.id),
    )
    const unresolvedWarnings = graph.warnings.filter((warning) => warning.type === 'unresolved_foreshadowing')

    expect(unresolvedWarnings).toHaveLength(2)
    expect(new Set(unresolvedWarnings.map((warning) => warning.sourceId))).toEqual(new Set([
      'foreshadowing:同一枚钥匙',
      'foreshadowing:同一枚钥匙:2',
    ]))
    expect(unresolvedWarnings.every((warning) => foreshadowingIds.has(String(warning.sourceId)))).toBe(true)
  })

  it('builds only local chapter-window nodes when a chapter range is provided', () => {
    const chapterCount = 1000
    const largePlan = {
      outline: {
        id: 'outline-longform',
        status: 'generated',
        total_chapters: chapterCount,
        chapters: Array.from({ length: chapterCount }, (_, index) => {
          const chapterIndex = index + 1
          return {
            chapter_index: chapterIndex,
            title: `长篇第${chapterIndex}章`,
            summary: `第${chapterIndex}章摘要`,
          }
        }),
        plotlines: [],
      },
      storyline: {
        id: 'storyline-longform',
        status: 'generated',
        plotlines: [
          {
            name: '主线：长篇主干',
            milestones: [
              { chapter_index: 12, title: '远端起点' },
              { chapter_index: 420, title: '窗口内推进' },
              { chapter_index: 960, title: '远端终局' },
            ],
          },
        ],
        foreshadowing: [
          { hint: '窗口外伏笔', planted_chapter: 120, status: 'pending' },
          { hint: '窗口内伏笔', planted_chapter: 430, status: 'pending' },
        ],
      },
    } as unknown as AthenaEvolutionPlan
    const largeTimeline: AthenaTimeline = {
      anchors: [],
      events: [
        {
          id: 'event-outside',
          event_id: 'event.outside',
          chapter_index: 300,
          intra_chapter_seq: 1,
          event_type: 'outside',
          description: '窗口外事件',
        },
        {
          id: 'event-inside',
          event_id: 'event.inside',
          chapter_index: 440,
          intra_chapter_seq: 1,
          event_type: 'inside',
          description: '窗口内事件',
        },
      ],
    }

    const graph = buildNarrativeAtlasGraph({
      plan: largePlan,
      chapters: [],
      timeline: largeTimeline,
      chapterRange: { start: 401, end: 480 },
    })

    const chapterIndexes = graph.nodes
      .filter((node) => node.type === 'chapter')
      .map((node) => node.chapterIndex)

    expect(chapterIndexes).toHaveLength(80)
    expect(chapterIndexes[0]).toBe(401)
    expect(chapterIndexes[79]).toBe(480)
    expect(graph.nodes).toEqual(expect.arrayContaining([
      expect.objectContaining({ type: 'milestone', label: '窗口内推进', chapterIndex: 420 }),
      expect.objectContaining({ type: 'foreshadowing', label: '窗口内伏笔', chapterIndex: 430 }),
      expect.objectContaining({ type: 'event', label: '窗口内事件', chapterIndex: 440 }),
    ]))
    expect(graph.nodes).not.toEqual(expect.arrayContaining([
      expect.objectContaining({ label: '远端起点' }),
      expect.objectContaining({ label: '远端终局' }),
      expect.objectContaining({ label: '窗口外伏笔' }),
      expect.objectContaining({ label: '窗口外事件' }),
    ]))
    expect(graph.edges.filter((edge) => edge.type === 'trunk')).toHaveLength(79)
  })
})
