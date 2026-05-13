# Athena Narrative Atlas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a complete `图谱` mode to Athena `叙事脉络`, using a deterministic narrative spine tree without replacing the existing text views.

**Architecture:** Build the feature entirely in the frontend first. A pure graph builder converts existing `AthenaEvolutionPlan`, `ChapterSummary[]`, and `AthenaTimeline | null` into stable nodes, edges, metrics, and warnings; Vue components render the graph, controls, and details.

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Pinia-backed existing stores, SVG, Vitest, Vue Test Utils, Vite.

---

## File Structure

- Create `frontend/src/components/athena/narrativeAtlasGraph.ts`: pure graph types and builder functions. No Vue imports.
- Create `frontend/src/components/athena/narrativeAtlasGraph.test.ts`: unit tests for graph construction, warning states, stable ids, and timeline degradation.
- Create `frontend/src/components/athena/NarrativeAtlasView.vue`: orchestration component for graph state, layer state, focus state, and selection.
- Create `frontend/src/components/athena/NarrativeAtlasView.test.ts`: component-level tests for empty state, layer toggles, selection, and fallback behavior.
- Create `frontend/src/components/athena/NarrativeAtlasCanvas.vue`: deterministic SVG rendering and accessible click targets.
- Create `frontend/src/components/athena/NarrativeAtlasControls.vue`: layer toggles, focus mode selector, graph metrics.
- Create `frontend/src/components/athena/NarrativeAtlasDetailPanel.vue`: selected node/edge details and view navigation actions.
- Modify `frontend/src/views/athenaNavigation.ts`: add `graph` to narrative views and canonical route support.
- Modify `frontend/src/views/athenaNavigation.test.ts`: add graph route tests.
- Modify `frontend/src/views/athenaSectionLoader.ts`: ensure graph loads both timeline and evolution plan data.
- Modify `frontend/src/views/athenaSectionLoader.test.ts`: add graph data-loading expectation.
- Modify `frontend/src/views/AthenaView.vue`: render `NarrativeAtlasView` when `routeState.view === 'graph'`.

---

### Task 1: Graph Builder

**Files:**
- Create: `frontend/src/components/athena/narrativeAtlasGraph.ts`
- Create: `frontend/src/components/athena/narrativeAtlasGraph.test.ts`

- [ ] **Step 1: Write failing graph builder tests**

Create `frontend/src/components/athena/narrativeAtlasGraph.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { buildNarrativeAtlasGraph } from './narrativeAtlasGraph'
import type { AthenaEvolutionPlan, AthenaTimeline, ChapterSummary } from '../../api/types'

const plan = {
  outline: {
    id: 'outline-1',
    status: 'generated',
    total_chapters: 3,
    chapters: [
      { chapter_index: 1, title: '雾港来信', summary: '陆辞收到旧灯塔来信。' },
      { chapter_index: 2, title: '灯塔旧账', summary: '叶知秋发现账册缺页。' },
      { chapter_index: 3, title: '档案回声', summary: '陈默承认隐瞒照片。' },
    ],
    plotlines: [],
  },
  storyline: {
    id: 'storyline-1',
    status: 'generated',
    plotlines: [
      {
        name: '主线：灯塔真相',
        type: 'main',
        milestones: [
          { chapter_index: 1, title: '来信启动' },
          { chapter: 3, event: '照片回收' },
        ],
      },
    ],
    foreshadowing: [
      {
        hint: '旧钥匙能打开档案室',
        planted_chapter: 1,
        resolved_chapter: 3,
        status: 'resolved',
      },
      {
        hint: '照片背面的编号',
        planted_chapter: 2,
        status: 'pending',
      },
      {
        hint: '缺少章节信息的隐喻',
        status: 'unknown',
      },
    ],
  },
} as unknown as AthenaEvolutionPlan

const chapters: ChapterSummary[] = [
  { id: 'chapter-1', chapter_index: 1, title: '雾港来信', word_count: 3200, status: 'draft' },
]

const timeline = {
  anchors: [],
  events: [
    {
      id: 'event-row-1',
      event_id: 'event.lighthouse.opened',
      chapter_index: 2,
      intra_chapter_seq: 1,
      event_type: 'world_state_changed',
      description: '旧灯塔档案室被重新打开。',
    },
  ],
} as AthenaTimeline

describe('buildNarrativeAtlasGraph', () => {
  it('builds a stable chapter spine from outline chapters', () => {
    const graph = buildNarrativeAtlasGraph({ plan, chapters, timeline: null })

    expect(graph.nodes.filter((node) => node.type === 'chapter').map((node) => node.id)).toEqual([
      'chapter:1',
      'chapter:2',
      'chapter:3',
    ])
    expect(graph.edges.filter((edge) => edge.type === 'trunk')).toHaveLength(2)
    expect(graph.metrics.chapterCount).toBe(3)
  })

  it('maps plotline milestones to branch nodes and edges', () => {
    const graph = buildNarrativeAtlasGraph({ plan, chapters, timeline: null })

    expect(graph.nodes.some((node) => node.id === 'plotline:主线-灯塔真相')).toBe(true)
    expect(graph.nodes.some((node) => node.id === 'milestone:主线-灯塔真相:1:来信启动')).toBe(true)
    expect(graph.edges.some((edge) => edge.type === 'branch' && edge.from === 'chapter:1')).toBe(true)
  })

  it('creates resolved, pending, and incomplete foreshadowing edges', () => {
    const graph = buildNarrativeAtlasGraph({ plan, chapters, timeline: null })

    expect(graph.edges).toContainEqual(expect.objectContaining({
      id: 'foreshadow:旧钥匙能打开档案室',
      type: 'foreshadowing',
      from: 'chapter:1',
      to: 'chapter:3',
      status: 'resolved',
    }))
    expect(graph.warnings).toContainEqual(expect.objectContaining({
      code: 'unresolved_foreshadowing',
      sourceId: 'foreshadow:照片背面的编号',
    }))
    expect(graph.warnings).toContainEqual(expect.objectContaining({
      code: 'incomplete_foreshadowing',
      sourceId: 'foreshadow:缺少章节信息的隐喻',
    }))
  })

  it('includes timeline events without requiring timeline data for the graph to exist', () => {
    const graph = buildNarrativeAtlasGraph({ plan, chapters, timeline })
    const noTimelineGraph = buildNarrativeAtlasGraph({ plan, chapters, timeline: null })

    expect(graph.nodes.some((node) => node.type === 'event' && node.title.includes('档案室'))).toBe(true)
    expect(noTimelineGraph.nodes.filter((node) => node.type === 'chapter')).toHaveLength(3)
    expect(noTimelineGraph.warnings).toContainEqual(expect.objectContaining({
      code: 'timeline_missing',
    }))
  })
})
```

- [ ] **Step 2: Run the failing tests**

Run:

```bash
cd D:\MyOP\CODE\NovelCodeSpace\novelv3\frontend
npm run test:unit -- narrativeAtlasGraph.test.ts
```

Expected: fail because `./narrativeAtlasGraph` does not exist.

- [ ] **Step 3: Implement graph builder**

Create `frontend/src/components/athena/narrativeAtlasGraph.ts`:

```ts
import type { AthenaEvolutionPlan, AthenaTimeline, ChapterSummary } from '../../api/types'

type RecordValue = Record<string, unknown>

export type NarrativeAtlasNodeType = 'chapter' | 'chapter_group' | 'plotline' | 'milestone' | 'foreshadowing' | 'event'
export type NarrativeAtlasEdgeType = 'trunk' | 'branch' | 'foreshadowing' | 'event_anchor'
export type NarrativeAtlasStatus = 'normal' | 'draft' | 'resolved' | 'pending' | 'incomplete' | 'warning'
export type NarrativeAtlasSourceView = 'graph' | 'timeline' | 'storyline' | 'chapters' | 'foreshadowing'

export interface NarrativeAtlasNode {
  id: string
  type: NarrativeAtlasNodeType
  title: string
  summary: string
  chapterIndex: number | null
  chapterRange: [number, number] | null
  status: NarrativeAtlasStatus
  sourceView: NarrativeAtlasSourceView
  sourceKey: string
  meta: Record<string, unknown>
}

export interface NarrativeAtlasEdge {
  id: string
  type: NarrativeAtlasEdgeType
  from: string
  to: string
  status: NarrativeAtlasStatus
  label: string
  sourceView: NarrativeAtlasSourceView
  sourceKey: string
}

export interface NarrativeAtlasWarning {
  code: 'timeline_missing' | 'unresolved_foreshadowing' | 'incomplete_foreshadowing' | 'missing_chapter_anchor'
  message: string
  sourceId: string
}

export interface NarrativeAtlasGraph {
  nodes: NarrativeAtlasNode[]
  edges: NarrativeAtlasEdge[]
  metrics: {
    chapterCount: number
    plotlineCount: number
    foreshadowingCount: number
    unresolvedForeshadowingCount: number
    eventCount: number
  }
  warnings: NarrativeAtlasWarning[]
}

export interface BuildNarrativeAtlasGraphInput {
  plan: AthenaEvolutionPlan | null
  chapters: ChapterSummary[]
  timeline: AthenaTimeline | null
}

export function buildNarrativeAtlasGraph(input: BuildNarrativeAtlasGraphInput): NarrativeAtlasGraph {
  const nodes: NarrativeAtlasNode[] = []
  const edges: NarrativeAtlasEdge[] = []
  const warnings: NarrativeAtlasWarning[] = []
  const chapterStatus = new Map(input.chapters.map((chapter) => [Number(chapter.chapter_index), chapter.status || 'draft']))
  const outlineChapters = asRecords(input.plan?.outline?.chapters)
    .map((chapter, index) => ({
      chapterIndex: toNumber(chapter.chapter_index ?? chapter.chapter),
      title: toText(chapter.title, `第${index + 1}章`),
      summary: toText(chapter.summary),
    }))
    .filter((chapter) => chapter.chapterIndex !== null)
    .sort((left, right) => Number(left.chapterIndex) - Number(right.chapterIndex))

  for (const chapter of outlineChapters) {
    const chapterIndex = Number(chapter.chapterIndex)
    nodes.push({
      id: chapterNodeId(chapterIndex),
      type: 'chapter',
      title: chapter.title,
      summary: chapter.summary,
      chapterIndex,
      chapterRange: [chapterIndex, chapterIndex],
      status: chapterStatus.has(chapterIndex) ? 'draft' : 'normal',
      sourceView: 'chapters',
      sourceKey: String(chapterIndex),
      meta: { actualStatus: chapterStatus.get(chapterIndex) || null },
    })
  }

  for (let index = 0; index < outlineChapters.length - 1; index += 1) {
    const from = chapterNodeId(Number(outlineChapters[index].chapterIndex))
    const to = chapterNodeId(Number(outlineChapters[index + 1].chapterIndex))
    edges.push({ id: `trunk:${from}:${to}`, type: 'trunk', from, to, status: 'normal', label: '', sourceView: 'chapters', sourceKey: from })
  }

  const plotlines = asRecords(input.plan?.storyline?.plotlines || input.plan?.outline?.plotlines)
  for (const plotline of plotlines) {
    addPlotline({ plotline, nodes, edges, warnings })
  }

  const foreshadowingItems = asRecords(input.plan?.storyline?.foreshadowing)
  for (const item of foreshadowingItems) {
    addForeshadowing({ item, nodes, edges, warnings, latestChapter: latestChapter(outlineChapters) })
  }

  const timelineEvents = input.timeline?.events || []
  for (const event of timelineEvents) {
    const chapterIndex = toNumber(event.chapter_index)
    const eventId = `event:${slug(toText(event.event_id, toText(event.description, 'event')))}`
    nodes.push({
      id: eventId,
      type: 'event',
      title: toText(event.description, toText(event.event_type, '事件')),
      summary: toText(event.event_type),
      chapterIndex,
      chapterRange: chapterIndex === null ? null : [chapterIndex, chapterIndex],
      status: 'normal',
      sourceView: 'timeline',
      sourceKey: toText(event.event_id, eventId),
      meta: event,
    })
    if (chapterIndex !== null) {
      edges.push({ id: `event-anchor:${eventId}`, type: 'event_anchor', from: chapterNodeId(chapterIndex), to: eventId, status: 'normal', label: '事件', sourceView: 'timeline', sourceKey: eventId })
    }
  }

  if (!input.timeline || timelineEvents.length === 0) {
    warnings.push({ code: 'timeline_missing', message: '正式时间线事件尚未生成，图谱使用叙事规划降级展示。', sourceId: 'timeline' })
  }

  return {
    nodes,
    edges,
    metrics: {
      chapterCount: outlineChapters.length,
      plotlineCount: plotlines.length,
      foreshadowingCount: foreshadowingItems.length,
      unresolvedForeshadowingCount: warnings.filter((warning) => warning.code === 'unresolved_foreshadowing').length,
      eventCount: timelineEvents.length,
    },
    warnings,
  }
}

function addPlotline(context: {
  plotline: RecordValue
  nodes: NarrativeAtlasNode[]
  edges: NarrativeAtlasEdge[]
  warnings: NarrativeAtlasWarning[]
}) {
  const title = toText(context.plotline.name || context.plotline.title, '未命名故事线')
  const plotlineId = `plotline:${slug(title)}`
  context.nodes.push({
    id: plotlineId,
    type: 'plotline',
    title,
    summary: toText(context.plotline.summary || context.plotline.description),
    chapterIndex: null,
    chapterRange: null,
    status: 'normal',
    sourceView: 'storyline',
    sourceKey: title,
    meta: { type: toText(context.plotline.type, '未分类') },
  })
  for (const milestone of asRecords(context.plotline.milestones)) {
    const chapterIndex = toNumber(milestone.chapter_index ?? milestone.chapter)
    const milestoneTitle = toText(milestone.title || milestone.summary || milestone.event, '未命名节点')
    const milestoneId = `milestone:${slug(title)}:${chapterIndex ?? 'unknown'}:${slug(milestoneTitle)}`
    context.nodes.push({
      id: milestoneId,
      type: 'milestone',
      title: milestoneTitle,
      summary: toText(milestone.summary || milestone.description || milestone.event),
      chapterIndex,
      chapterRange: chapterIndex === null ? null : [chapterIndex, chapterIndex],
      status: chapterIndex === null ? 'incomplete' : 'normal',
      sourceView: 'storyline',
      sourceKey: `${title}:${milestoneTitle}`,
      meta: { plotlineTitle: title },
    })
    context.edges.push({ id: `branch:${plotlineId}:${milestoneId}`, type: 'branch', from: chapterIndex === null ? plotlineId : chapterNodeId(chapterIndex), to: milestoneId, status: chapterIndex === null ? 'incomplete' : 'normal', label: title, sourceView: 'storyline', sourceKey: `${title}:${milestoneTitle}` })
    if (chapterIndex === null) {
      context.warnings.push({ code: 'missing_chapter_anchor', message: `故事线节点“${milestoneTitle}”缺少章节锚点。`, sourceId: milestoneId })
    }
  }
}

function addForeshadowing(context: {
  item: RecordValue
  nodes: NarrativeAtlasNode[]
  edges: NarrativeAtlasEdge[]
  warnings: NarrativeAtlasWarning[]
  latestChapter: number | null
}) {
  const title = toText(context.item.hint || context.item.title || context.item.name, '未命名伏笔')
  const plantedChapter = toNumber(context.item.planted_chapter ?? context.item.plantedChapter)
  const resolvedChapter = toNumber(context.item.resolved_chapter ?? context.item.resolvedChapter)
  const sourceId = `foreshadow:${slug(title)}`
  const status = resolvedChapter === null ? 'pending' : 'resolved'
  context.nodes.push({
    id: sourceId,
    type: 'foreshadowing',
    title,
    summary: toText(context.item.summary || context.item.description),
    chapterIndex: plantedChapter,
    chapterRange: plantedChapter === null ? null : [plantedChapter, resolvedChapter ?? plantedChapter],
    status: plantedChapter === null ? 'incomplete' : status,
    sourceView: 'foreshadowing',
    sourceKey: title,
    meta: { plantedChapter, resolvedChapter, rawStatus: toText(context.item.status) },
  })
  if (plantedChapter === null) {
    context.warnings.push({ code: 'incomplete_foreshadowing', message: `伏笔“${title}”缺少埋设章节。`, sourceId })
    return
  }
  if (resolvedChapter === null) {
    const fallbackChapter = context.latestChapter ?? plantedChapter
    context.edges.push({ id: sourceId, type: 'foreshadowing', from: chapterNodeId(plantedChapter), to: chapterNodeId(fallbackChapter), status: 'pending', label: title, sourceView: 'foreshadowing', sourceKey: title })
    context.warnings.push({ code: 'unresolved_foreshadowing', message: `伏笔“${title}”尚未回收。`, sourceId })
    return
  }
  context.edges.push({ id: sourceId, type: 'foreshadowing', from: chapterNodeId(plantedChapter), to: chapterNodeId(resolvedChapter), status: 'resolved', label: title, sourceView: 'foreshadowing', sourceKey: title })
}

function latestChapter(chapters: { chapterIndex: number | null }[]) {
  const indexes = chapters.map((chapter) => chapter.chapterIndex).filter((value): value is number => value !== null)
  return indexes.length ? Math.max(...indexes) : null
}

export function chapterNodeId(chapterIndex: number) {
  return `chapter:${chapterIndex}`
}

function asRecord(value: unknown): RecordValue | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null
}

function asRecords(value: unknown): RecordValue[] {
  return Array.isArray(value) ? value.map(asRecord).filter((item): item is RecordValue => item !== null) : []
}

function toText(value: unknown, fallback = '') {
  if (typeof value === 'string' && value.trim()) return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  return fallback
}

function toNumber(value: unknown): number | null {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : null
}

function slug(value: string) {
  return value.trim().replace(/[^\p{L}\p{N}]+/gu, '-').replace(/^-|-$/g, '') || 'item'
}
```

- [ ] **Step 4: Run graph builder tests**

Run:

```bash
cd D:\MyOP\CODE\NovelCodeSpace\novelv3\frontend
npm run test:unit -- narrativeAtlasGraph.test.ts
```

Expected: pass.

- [ ] **Step 5: Commit graph builder**

Run:

```bash
git add frontend/src/components/athena/narrativeAtlasGraph.ts frontend/src/components/athena/narrativeAtlasGraph.test.ts
git commit -m "feat: build athena narrative atlas graph"
```

---

### Task 2: Navigation And Data Loading

**Files:**
- Modify: `frontend/src/views/athenaNavigation.ts`
- Modify: `frontend/src/views/athenaNavigation.test.ts`
- Modify: `frontend/src/views/athenaSectionLoader.ts`
- Modify: `frontend/src/views/athenaSectionLoader.test.ts`

- [ ] **Step 1: Write failing navigation tests**

Append these tests to `frontend/src/views/athenaNavigation.test.ts`:

```ts
it('supports the narrative graph route', () => {
  expect(resolveAthenaRoute('narrative', { view: 'graph' })).toMatchObject({
    section: 'narrative',
    view: 'graph',
    isLegacy: false,
  })
})

it('builds the narrative graph route location', () => {
  expect(buildAthenaRoute('project-1', {
    section: 'narrative',
    view: 'graph',
    nodeType: 'all',
    tool: null,
    panel: null,
  })).toEqual({
    path: '/projects/project-1/athena/narrative',
    query: { view: 'graph' },
  })
})
```

Append this test to `frontend/src/views/athenaSectionLoader.test.ts`:

```ts
it('loads timeline and evolution plan for the narrative graph view', async () => {
  const loader = createLoader()

  await loader.loadRouteData(routeState({ section: 'narrative', view: 'graph' }))

  expect(athena.loadTimeline).toHaveBeenCalledWith('project-1')
  expect(athena.loadEvolutionPlan).toHaveBeenCalledWith('project-1')
})
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd D:\MyOP\CODE\NovelCodeSpace\novelv3\frontend
npm run test:unit -- athenaNavigation.test.ts athenaSectionLoader.test.ts
```

Expected: fail because `graph` is not a valid narrative view and loader does not handle it.

- [ ] **Step 3: Update navigation types and valid views**

In `frontend/src/views/athenaNavigation.ts`, change the narrative view type and valid view list:

```ts
export type AthenaNarrativeView = 'graph' | 'timeline' | 'storyline' | 'chapters' | 'foreshadowing'
```

```ts
const narrativeViews = ['graph', 'timeline', 'storyline', 'chapters', 'foreshadowing'] as const
```

Keep the default section view as `timeline` unless product direction explicitly changes in a separate request. This preserves existing URLs and avoids surprising users.

- [ ] **Step 4: Update route data loader**

In `frontend/src/views/athenaSectionLoader.ts`, change the narrative loading branch to:

```ts
if (routeState.section === 'narrative' && (routeState.view === 'timeline' || routeState.view === 'graph')) {
  if (!options.athena.timeline) await options.athena.loadTimeline(id)
}
if (
  routeState.section === 'narrative'
  && (routeState.view === 'graph' || routeState.view === 'storyline' || routeState.view === 'chapters' || routeState.view === 'foreshadowing')
) {
  if (!options.athena.evolutionPlan) await options.athena.loadEvolutionPlan(id)
}
```

- [ ] **Step 5: Run navigation and loader tests**

Run:

```bash
cd D:\MyOP\CODE\NovelCodeSpace\novelv3\frontend
npm run test:unit -- athenaNavigation.test.ts athenaSectionLoader.test.ts
```

Expected: pass.

- [ ] **Step 6: Commit navigation work**

Run:

```bash
git add frontend/src/views/athenaNavigation.ts frontend/src/views/athenaNavigation.test.ts frontend/src/views/athenaSectionLoader.ts frontend/src/views/athenaSectionLoader.test.ts
git commit -m "feat: add athena narrative graph route"
```

---

### Task 3: Atlas View Container

**Files:**
- Create: `frontend/src/components/athena/NarrativeAtlasView.vue`
- Create: `frontend/src/components/athena/NarrativeAtlasView.test.ts`

- [ ] **Step 1: Write failing component tests**

Create `frontend/src/components/athena/NarrativeAtlasView.test.ts`:

```ts
// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import NarrativeAtlasView from './NarrativeAtlasView.vue'
import type { AthenaEvolutionPlan, ChapterSummary } from '../../api/types'

const plan = {
  outline: {
    id: 'outline-1',
    status: 'generated',
    total_chapters: 2,
    chapters: [
      { chapter_index: 1, title: '旧灯塔', summary: '旧灯塔重新点亮。' },
      { chapter_index: 2, title: '档案室', summary: '档案室出现缺页账册。' },
    ],
    plotlines: [],
  },
  storyline: {
    id: 'storyline-1',
    status: 'generated',
    plotlines: [
      { name: '主线：灯塔真相', type: 'main', milestones: [{ chapter_index: 1, title: '点亮灯塔' }] },
    ],
    foreshadowing: [
      { hint: '旧钥匙', planted_chapter: 1, resolved_chapter: 2, status: 'resolved' },
    ],
  },
} as unknown as AthenaEvolutionPlan

const chapters: ChapterSummary[] = [
  { id: 'chapter-1', chapter_index: 1, title: '旧灯塔', word_count: 3000, status: 'draft' },
]

describe('NarrativeAtlasView', () => {
  it('renders graph metrics and chapter spine data', () => {
    const wrapper = mount(NarrativeAtlasView, { props: { plan, chapters, timeline: null } })

    expect(wrapper.text()).toContain('章节 2')
    expect(wrapper.text()).toContain('故事线 1')
    expect(wrapper.text()).toContain('伏笔 1')
    expect(wrapper.text()).toContain('旧灯塔')
  })

  it('shows empty state when no plan exists', () => {
    const wrapper = mount(NarrativeAtlasView, { props: { plan: null, chapters: [], timeline: null } })

    expect(wrapper.text()).toContain('尚未生成叙事规划')
  })

  it('selects a node and renders its details', async () => {
    const wrapper = mount(NarrativeAtlasView, { props: { plan, chapters, timeline: null } })

    await wrapper.get('[data-atlas-node-id="chapter:1"]').trigger('click')

    expect(wrapper.text()).toContain('选中节点')
    expect(wrapper.text()).toContain('旧灯塔重新点亮')
  })

  it('can hide and show foreshadowing layer', async () => {
    const wrapper = mount(NarrativeAtlasView, { props: { plan, chapters, timeline: null } })

    expect(wrapper.find('[data-atlas-layer="foreshadowing"]').exists()).toBe(true)
    await wrapper.get('[data-atlas-toggle="foreshadowing"]').setValue(false)
    expect(wrapper.find('[data-atlas-layer="foreshadowing"]').exists()).toBe(false)
  })
})
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd D:\MyOP\CODE\NovelCodeSpace\novelv3\frontend
npm run test:unit -- NarrativeAtlasView.test.ts
```

Expected: fail because `NarrativeAtlasView.vue` does not exist.

- [ ] **Step 3: Create container component**

Create `frontend/src/components/athena/NarrativeAtlasView.vue`:

```vue
<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AthenaEvolutionPlan, AthenaTimeline, ChapterSummary } from '../../api/types'
import {
  buildNarrativeAtlasGraph,
  type NarrativeAtlasEdge,
  type NarrativeAtlasNode,
} from './narrativeAtlasGraph'
import NarrativeAtlasCanvas from './NarrativeAtlasCanvas.vue'
import NarrativeAtlasControls from './NarrativeAtlasControls.vue'
import NarrativeAtlasDetailPanel from './NarrativeAtlasDetailPanel.vue'

const props = defineProps<{
  plan: AthenaEvolutionPlan | null
  chapters: ChapterSummary[]
  timeline: AthenaTimeline | null
}>()

const emit = defineEmits<{
  navigate: [payload: { view: 'timeline' | 'storyline' | 'chapters' | 'foreshadowing'; sourceKey: string }]
}>()

const layers = ref({
  trunk: true,
  branches: true,
  foreshadowing: true,
  events: true,
})
const focusMode = ref<'structure' | 'unresolved' | 'storyline' | 'events'>('structure')
const selectedId = ref<string | null>(null)

const graph = computed(() => buildNarrativeAtlasGraph({
  plan: props.plan,
  chapters: props.chapters,
  timeline: props.timeline,
}))

const selected = computed<NarrativeAtlasNode | NarrativeAtlasEdge | null>(() => {
  if (!selectedId.value) return null
  return graph.value.nodes.find((node) => node.id === selectedId.value)
    || graph.value.edges.find((edge) => edge.id === selectedId.value)
    || null
})

function selectItem(id: string) {
  selectedId.value = id
}
</script>

<template>
  <section class="narrative-atlas">
    <div v-if="!plan" class="narrative-atlas__empty">
      <strong>尚未生成叙事规划</strong>
      <span>生成故事线或章节大纲后，图谱会显示章节主干、故事线枝干和伏笔埋收。</span>
    </div>
    <template v-else>
      <NarrativeAtlasControls
        v-model:layers="layers"
        v-model:focus-mode="focusMode"
        :metrics="graph.metrics"
        :warnings="graph.warnings"
      />
      <NarrativeAtlasCanvas
        :graph="graph"
        :layers="layers"
        :focus-mode="focusMode"
        :selected-id="selectedId"
        @select="selectItem"
      />
      <NarrativeAtlasDetailPanel
        :item="selected"
        :graph="graph"
        @navigate="emit('navigate', $event)"
      />
    </template>
  </section>
</template>

<style scoped>
.narrative-atlas {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr) 280px;
  gap: var(--space-4);
  height: 100%;
  min-height: 560px;
  padding: var(--space-4);
}

.narrative-atlas__empty {
  grid-column: 1 / -1;
  display: grid;
  place-items: center;
  align-content: center;
  gap: var(--space-2);
  color: var(--color-text-tertiary);
  text-align: center;
}

.narrative-atlas__empty strong {
  color: var(--color-text-secondary);
  font-weight: var(--font-semibold);
}

@media (max-width: 980px) {
  .narrative-atlas {
    grid-template-columns: 1fr;
    min-height: auto;
  }
}
</style>
```

- [ ] **Step 4: Run component test and observe missing child failures**

Run:

```bash
cd D:\MyOP\CODE\NovelCodeSpace\novelv3\frontend
npm run test:unit -- NarrativeAtlasView.test.ts
```

Expected: fail because `NarrativeAtlasCanvas.vue`, `NarrativeAtlasControls.vue`, and `NarrativeAtlasDetailPanel.vue` do not exist.

- [ ] **Step 5: Commit only after child components pass in later tasks**

Do not commit this task until Tasks 4 and 5 finish because the container intentionally references child components.

---

### Task 4: Controls And Detail Panel

**Files:**
- Create: `frontend/src/components/athena/NarrativeAtlasControls.vue`
- Create: `frontend/src/components/athena/NarrativeAtlasDetailPanel.vue`

- [ ] **Step 1: Create controls component**

Create `frontend/src/components/athena/NarrativeAtlasControls.vue`:

```vue
<script setup lang="ts">
import type { NarrativeAtlasGraph, NarrativeAtlasWarning } from './narrativeAtlasGraph'

const layers = defineModel<{
  trunk: boolean
  branches: boolean
  foreshadowing: boolean
  events: boolean
}>('layers', { required: true })
const focusMode = defineModel<'structure' | 'unresolved' | 'storyline' | 'events'>('focusMode', { required: true })

defineProps<{
  metrics: NarrativeAtlasGraph['metrics']
  warnings: NarrativeAtlasWarning[]
}>()
</script>

<template>
  <aside class="atlas-controls">
    <div class="atlas-controls__metrics">
      <span>章节 {{ metrics.chapterCount }}</span>
      <span>故事线 {{ metrics.plotlineCount }}</span>
      <span>伏笔 {{ metrics.foreshadowingCount }}</span>
      <span v-if="metrics.eventCount">事件 {{ metrics.eventCount }}</span>
    </div>

    <section>
      <h3>图层</h3>
      <label><input v-model="layers.trunk" data-atlas-toggle="trunk" type="checkbox"> 章节主干</label>
      <label><input v-model="layers.branches" data-atlas-toggle="branches" type="checkbox"> 故事线枝干</label>
      <label><input v-model="layers.foreshadowing" data-atlas-toggle="foreshadowing" type="checkbox"> 伏笔埋收</label>
      <label><input v-model="layers.events" data-atlas-toggle="events" type="checkbox"> 正式事件</label>
    </section>

    <section>
      <h3>聚焦</h3>
      <select v-model="focusMode" class="atlas-controls__select" aria-label="图谱聚焦模式">
        <option value="structure">全书结构</option>
        <option value="unresolved">只看未回收伏笔</option>
        <option value="storyline">故事线枝干</option>
        <option value="events">正式事件覆盖</option>
      </select>
    </section>

    <section v-if="warnings.length">
      <h3>提示</h3>
      <p v-for="warning in warnings.slice(0, 4)" :key="`${warning.code}-${warning.sourceId}`">
        {{ warning.message }}
      </p>
    </section>
  </aside>
</template>

<style scoped>
.atlas-controls {
  display: grid;
  align-content: start;
  gap: var(--space-4);
  border-right: 1px solid var(--color-border);
  padding-right: var(--space-4);
}

.atlas-controls__metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.atlas-controls section {
  display: grid;
  gap: var(--space-2);
}

.atlas-controls h3 {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.atlas-controls label,
.atlas-controls p {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.atlas-controls__select {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2);
  background: var(--color-surface);
  color: var(--color-text-primary);
}

@media (max-width: 980px) {
  .atlas-controls {
    border-right: 0;
    border-bottom: 1px solid var(--color-border);
    padding-right: 0;
    padding-bottom: var(--space-3);
  }
}
</style>
```

- [ ] **Step 2: Create detail panel component**

Create `frontend/src/components/athena/NarrativeAtlasDetailPanel.vue`:

```vue
<script setup lang="ts">
import type { NarrativeAtlasEdge, NarrativeAtlasGraph, NarrativeAtlasNode } from './narrativeAtlasGraph'

const props = defineProps<{
  item: NarrativeAtlasNode | NarrativeAtlasEdge | null
  graph: NarrativeAtlasGraph
}>()

const emit = defineEmits<{
  navigate: [payload: { view: 'timeline' | 'storyline' | 'chapters' | 'foreshadowing'; sourceKey: string }]
}>()

function isEdge(item: NarrativeAtlasNode | NarrativeAtlasEdge): item is NarrativeAtlasEdge {
  return 'from' in item && 'to' in item
}

function title(item: NarrativeAtlasNode | NarrativeAtlasEdge | null) {
  if (!item) return '未选择节点'
  return isEdge(item) ? item.label || edgeTypeLabel(item.type) : item.title
}

function body(item: NarrativeAtlasNode | NarrativeAtlasEdge | null) {
  if (!item) return '点击章节、故事线节点或伏笔线查看详情。'
  if (isEdge(item)) return `${edgeTypeLabel(item.type)}：${item.from} → ${item.to}`
  return item.summary || nodeTypeLabel(item.type)
}

function targetView(item: NarrativeAtlasNode | NarrativeAtlasEdge | null) {
  if (!item) return null
  if (isEdge(item)) return item.sourceView === 'graph' ? null : item.sourceView
  return item.sourceView === 'graph' ? null : item.sourceView
}

function nodeTypeLabel(type: NarrativeAtlasNode['type']) {
  const labels: Record<NarrativeAtlasNode['type'], string> = {
    chapter: '章节',
    chapter_group: '章节段',
    plotline: '故事线',
    milestone: '故事线节点',
    foreshadowing: '伏笔',
    event: '正式事件',
  }
  return labels[type]
}

function edgeTypeLabel(type: NarrativeAtlasEdge['type']) {
  const labels: Record<NarrativeAtlasEdge['type'], string> = {
    trunk: '章节主干',
    branch: '故事线枝干',
    foreshadowing: '伏笔埋收',
    event_anchor: '事件锚点',
  }
  return labels[type]
}

function navigate() {
  const view = targetView(props.item)
  if (!view || !props.item) return
  emit('navigate', { view, sourceKey: props.item.sourceKey })
}
</script>

<template>
  <aside class="atlas-detail">
    <span>选中节点</span>
    <h3>{{ title(item) }}</h3>
    <p>{{ body(item) }}</p>
    <dl v-if="item && !isEdge(item)">
      <dt>类型</dt>
      <dd>{{ nodeTypeLabel(item.type) }}</dd>
      <dt v-if="item.chapterIndex">章节</dt>
      <dd v-if="item.chapterIndex">第{{ item.chapterIndex }}章</dd>
      <dt>状态</dt>
      <dd>{{ item.status }}</dd>
    </dl>
    <dl v-else-if="item && isEdge(item)">
      <dt>类型</dt>
      <dd>{{ edgeTypeLabel(item.type) }}</dd>
      <dt>状态</dt>
      <dd>{{ item.status }}</dd>
    </dl>
    <button v-if="targetView(item)" class="atlas-detail__button" type="button" @click="navigate">
      切到文本视图
    </button>
  </aside>
</template>

<style scoped>
.atlas-detail {
  display: grid;
  align-content: start;
  gap: var(--space-3);
  border-left: 1px solid var(--color-border);
  padding-left: var(--space-4);
}

.atlas-detail span {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.atlas-detail h3 {
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.atlas-detail p,
.atlas-detail dd,
.atlas-detail dt {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.atlas-detail dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-1) var(--space-2);
}

.atlas-detail dt {
  color: var(--color-text-tertiary);
}

.atlas-detail__button {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface);
  color: var(--color-text-primary);
  cursor: pointer;
}

@media (max-width: 980px) {
  .atlas-detail {
    border-left: 0;
    border-top: 1px solid var(--color-border);
    padding-left: 0;
    padding-top: var(--space-3);
  }
}
</style>
```

---

### Task 5: SVG Canvas

**Files:**
- Create: `frontend/src/components/athena/NarrativeAtlasCanvas.vue`

- [ ] **Step 1: Create deterministic SVG canvas**

Create `frontend/src/components/athena/NarrativeAtlasCanvas.vue`:

```vue
<script setup lang="ts">
import { computed } from 'vue'
import type { NarrativeAtlasEdge, NarrativeAtlasGraph, NarrativeAtlasNode } from './narrativeAtlasGraph'

const props = defineProps<{
  graph: NarrativeAtlasGraph
  layers: {
    trunk: boolean
    branches: boolean
    foreshadowing: boolean
    events: boolean
  }
  focusMode: 'structure' | 'unresolved' | 'storyline' | 'events'
  selectedId: string | null
}>()

const emit = defineEmits<{
  select: [id: string]
}>()

interface PositionedNode extends NarrativeAtlasNode {
  x: number
  y: number
}

const positionedNodes = computed(() => {
  const chapters = props.graph.nodes.filter((node) => node.type === 'chapter').sort((left, right) => Number(left.chapterIndex || 0) - Number(right.chapterIndex || 0))
  const yByChapter = new Map<number, number>()
  chapters.forEach((node, index) => yByChapter.set(Number(node.chapterIndex), 72 + index * 92))
  const branchOffsets = new Map<string, number>()
  const nodes: PositionedNode[] = []

  for (const node of props.graph.nodes) {
    if (node.type === 'chapter') {
      nodes.push({ ...node, x: 360, y: yByChapter.get(Number(node.chapterIndex)) || 72 })
    } else if (node.type === 'event') {
      nodes.push({ ...node, x: 492, y: chapterY(node, yByChapter) })
    } else if (node.type === 'foreshadowing') {
      nodes.push({ ...node, x: 188, y: chapterY(node, yByChapter) - 26 })
    } else {
      const plotlineKey = String(node.meta.plotlineTitle || node.title)
      const offset = branchOffsets.get(plotlineKey) ?? branchOffsets.size
      branchOffsets.set(plotlineKey, offset)
      const side = offset % 2 === 0 ? -1 : 1
      const lane = Math.floor(offset / 2)
      nodes.push({ ...node, x: 360 + side * (150 + lane * 64), y: chapterY(node, yByChapter) })
    }
  }
  return nodes
})

const nodeById = computed(() => new Map(positionedNodes.value.map((node) => [node.id, node])))
const visibleEdges = computed(() => props.graph.edges.filter(isEdgeVisible))
const visibleNodes = computed(() => positionedNodes.value.filter(isNodeVisible))
const height = computed(() => Math.max(420, 120 + props.graph.metrics.chapterCount * 92))

function chapterY(node: NarrativeAtlasNode, yByChapter: Map<number, number>) {
  if (node.chapterIndex !== null) return yByChapter.get(node.chapterIndex) || 72
  return 72
}

function isNodeVisible(node: NarrativeAtlasNode) {
  if (node.type === 'event') return props.layers.events
  if (node.type === 'foreshadowing') return props.layers.foreshadowing
  if (node.type === 'plotline' || node.type === 'milestone') return props.layers.branches
  return props.layers.trunk
}

function isEdgeVisible(edge: NarrativeAtlasEdge) {
  if (edge.type === 'trunk') return props.layers.trunk
  if (edge.type === 'branch') return props.layers.branches
  if (edge.type === 'foreshadowing') return props.layers.foreshadowing
  if (edge.type === 'event_anchor') return props.layers.events
  return true
}

function edgePath(edge: NarrativeAtlasEdge) {
  const from = nodeById.value.get(edge.from)
  const to = nodeById.value.get(edge.to)
  if (!from || !to) return ''
  const curve = Math.max(80, Math.abs(to.x - from.x) * 0.55)
  return `M ${from.x} ${from.y} C ${from.x} ${from.y + curve * 0.25}, ${to.x} ${to.y - curve * 0.25}, ${to.x} ${to.y}`
}

function edgeClass(edge: NarrativeAtlasEdge) {
  return [
    'atlas-canvas__edge',
    `atlas-canvas__edge--${edge.type}`,
    `atlas-canvas__edge--${edge.status}`,
    { 'atlas-canvas__edge--selected': edge.id === props.selectedId },
  ]
}

function nodeClass(node: PositionedNode) {
  return [
    'atlas-canvas__node',
    `atlas-canvas__node--${node.type}`,
    `atlas-canvas__node--${node.status}`,
    { 'atlas-canvas__node--selected': node.id === props.selectedId },
  ]
}
</script>

<template>
  <div class="atlas-canvas">
    <svg :viewBox="`0 0 720 ${height}`" role="img" aria-label="叙事图谱">
      <g data-atlas-layer="edges">
        <path
          v-for="edge in visibleEdges"
          :key="edge.id"
          :class="edgeClass(edge)"
          :d="edgePath(edge)"
          tabindex="0"
          @click="emit('select', edge.id)"
          @keydown.enter.prevent="emit('select', edge.id)"
        />
      </g>
      <g data-atlas-layer="nodes">
        <g
          v-for="node in visibleNodes"
          :key="node.id"
          :class="nodeClass(node)"
          :transform="`translate(${node.x} ${node.y})`"
          :data-atlas-node-id="node.id"
          tabindex="0"
          @click="emit('select', node.id)"
          @keydown.enter.prevent="emit('select', node.id)"
        >
          <rect x="-62" y="-18" width="124" height="36" rx="8" />
          <text text-anchor="middle" dominant-baseline="middle">{{ node.title }}</text>
        </g>
      </g>
    </svg>
  </div>
</template>

<style scoped>
.atlas-canvas {
  min-height: 520px;
  overflow: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: linear-gradient(180deg, var(--color-surface), var(--color-surface-muted));
}

.atlas-canvas svg {
  width: 100%;
  min-width: 720px;
}

.atlas-canvas__edge {
  fill: none;
  stroke-width: 2.5;
  cursor: pointer;
}

.atlas-canvas__edge--trunk { stroke: var(--color-brand); stroke-width: 5; }
.atlas-canvas__edge--branch { stroke: #16a34a; stroke-width: 4; }
.atlas-canvas__edge--foreshadowing { stroke: #d97706; stroke-dasharray: 8 7; }
.atlas-canvas__edge--event_anchor { stroke: var(--color-text-tertiary); stroke-dasharray: 4 5; }
.atlas-canvas__edge--pending { stroke: #dc2626; }
.atlas-canvas__edge--incomplete { stroke: var(--color-text-tertiary); }
.atlas-canvas__edge--selected { stroke-width: 6; }

.atlas-canvas__node {
  cursor: pointer;
  outline: none;
}

.atlas-canvas__node rect {
  fill: var(--color-surface);
  stroke: var(--color-border);
  stroke-width: 1.5;
}

.atlas-canvas__node text {
  fill: var(--color-text-primary);
  font-size: 12px;
  pointer-events: none;
}

.atlas-canvas__node--chapter rect { stroke: var(--color-brand); stroke-width: 2; }
.atlas-canvas__node--milestone rect,
.atlas-canvas__node--plotline rect { fill: #f0fdf4; stroke: #16a34a; }
.atlas-canvas__node--foreshadowing rect { fill: #fffbeb; stroke: #d97706; stroke-dasharray: 4 3; }
.atlas-canvas__node--event rect { fill: #f8fafc; stroke: var(--color-text-tertiary); }
.atlas-canvas__node--pending rect { fill: #fee2e2; stroke: #dc2626; }
.atlas-canvas__node--selected rect { stroke-width: 3; }
</style>
```

- [ ] **Step 2: Run the atlas view test**

Run:

```bash
cd D:\MyOP\CODE\NovelCodeSpace\novelv3\frontend
npm run test:unit -- NarrativeAtlasView.test.ts
```

Expected: pass.

- [ ] **Step 3: Commit container and child components**

Run:

```bash
git add frontend/src/components/athena/NarrativeAtlasView.vue frontend/src/components/athena/NarrativeAtlasView.test.ts frontend/src/components/athena/NarrativeAtlasCanvas.vue frontend/src/components/athena/NarrativeAtlasControls.vue frontend/src/components/athena/NarrativeAtlasDetailPanel.vue
git commit -m "feat: render athena narrative atlas"
```

---

### Task 6: Athena View Integration

**Files:**
- Modify: `frontend/src/views/AthenaView.vue`

- [ ] **Step 1: Import and render atlas view**

In `frontend/src/views/AthenaView.vue`, add:

```ts
import NarrativeAtlasView from '../components/athena/NarrativeAtlasView.vue'
```

In the narrative template branch, insert `NarrativeAtlasView` before `TimelineView`:

```vue
<NarrativeAtlasView
  v-if="routeState.view === 'graph'"
  :plan="athena.evolutionPlan"
  :chapters="project.chapters"
  :timeline="athena.timeline"
  @navigate="(target) => updateAthenaRoute({ view: target.view })"
/>
<TimelineView
  v-else-if="routeState.view === 'timeline'"
  :events="timelineEvents"
  :anchors="timelineAnchors"
  :fallback-summary="narrativeFallbackSummary"
/>
```

Keep `NarrativeWorkbench` as the `v-else` branch for text views.

- [ ] **Step 2: Run focused frontend tests**

Run:

```bash
cd D:\MyOP\CODE\NovelCodeSpace\novelv3\frontend
npm run test:unit -- narrativeAtlasGraph.test.ts NarrativeAtlasView.test.ts athenaNavigation.test.ts athenaSectionLoader.test.ts
```

Expected: pass.

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd D:\MyOP\CODE\NovelCodeSpace\novelv3\frontend
npm run build
```

Expected: `vue-tsc --noEmit` passes and Vite writes assets to `backend/static`.

- [ ] **Step 4: Commit integration**

Run:

```bash
git add frontend/src/views/AthenaView.vue
git commit -m "feat: integrate narrative atlas into athena"
```

---

### Task 7: Browser Verification

**Files:**
- No source files unless verification reveals a concrete defect.

- [ ] **Step 1: Ensure local servers are running**

Verify:

```powershell
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:5173" -TimeoutSec 5
Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/docs" -TimeoutSec 5
```

Expected: both return HTTP 200.

- [ ] **Step 2: Open graph URL**

Open:

```text
http://127.0.0.1:5173/projects/b9d50481-6f5c-4f54-9b60-984c43e40808/athena/narrative?view=graph
```

Expected:

- The view renders `章节`, `故事线`, and `伏笔` metrics.
- The SVG contains chapter nodes and branch nodes.
- Existing text views remain available in the narrative navigation.

- [ ] **Step 3: Verify interaction**

Manual checks:

- Click a chapter node. Expected: right panel title changes to that chapter.
- Turn off `伏笔埋收`. Expected: foreshadowing SVG elements disappear.
- Turn `伏笔埋收` back on. Expected: foreshadowing SVG elements return.
- Select a foreshadowing node or line. Expected: right panel shows foreshadowing title and status.
- Click `切到文本视图`. Expected: Athena switches to the matching text view.

- [ ] **Step 4: Verify narrow viewport**

Use browser devtools or Playwright to check a mobile-width viewport:

```bash
cd D:\MyOP\CODE\NovelCodeSpace\novelv3\frontend
node -e "console.log('Use the in-app browser responsive mode for 390px width verification')"
```

Expected:

- Controls stack above the canvas.
- The canvas scrolls horizontally instead of crushing node text.
- The detail panel appears below the canvas.

- [ ] **Step 5: Final status check**

Run:

```bash
cd D:\MyOP\CODE\NovelCodeSpace\novelv3
git status --short --branch
```

Expected: main branch is ahead by the implementation commits and has no unstaged source changes.

---

## Self-Review

Spec coverage:

- Adds a `图谱` narrative view without replacing text views: Tasks 2 and 6.
- Uses deterministic frontend graph builder from existing data: Task 1.
- Renders spine, branches, foreshadowing, event anchors: Tasks 1 and 5.
- Provides layers, focus mode, metrics, warnings: Tasks 4 and 5.
- Provides detail panel and text-view navigation: Tasks 4 and 6.
- Handles empty and degraded states: Tasks 1, 3, and 7.
- Adds unit, component, build, and browser verification: Tasks 1 through 7.

Placeholder scan:

- The plan contains no placeholder markers, no undefined named tasks, and no open-ended implementation steps.

Type consistency:

- `NarrativeAtlasGraph`, `NarrativeAtlasNode`, `NarrativeAtlasEdge`, and warning types are defined in Task 1 and imported consistently by Tasks 3 through 5.
- Route view `graph` is introduced in Task 2 and consumed by Task 6.
