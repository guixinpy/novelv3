<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import NarrativeAtlasCanvas from './NarrativeAtlasCanvas.vue'
import NarrativeAtlasControls from './NarrativeAtlasControls.vue'
import NarrativeAtlasDetailPanel from './NarrativeAtlasDetailPanel.vue'
import {
  buildNarrativeAtlasGraph,
  collectNarrativeAtlasChapterIndexes,
  collectNarrativeAtlasMetrics,
} from './narrativeAtlasGraph'
import type { AthenaEvolutionPlan, AthenaTimeline, ChapterSummary } from '../../api/types'
import type { AthenaNarrativeView } from '../../views/athenaNavigation'
import type { NarrativeAtlasEdge, NarrativeAtlasGraph, NarrativeAtlasNode } from './narrativeAtlasGraph'

type AtlasLayer = 'trunk' | 'branches' | 'foreshadowing' | 'events'
type AtlasSelection = { kind: 'node'; id: string } | { kind: 'edge'; id: string }

interface NavigatePayload {
  view: AthenaNarrativeView
  sourceKey: string
}

const props = defineProps<{
  plan: AthenaEvolutionPlan | null
  chapters: ChapterSummary[]
  timeline: AthenaTimeline | null
  loading?: boolean
}>()

const emit = defineEmits<{
  navigate: [payload: NavigatePayload]
}>()

const layers = reactive<Record<AtlasLayer, boolean>>({
  trunk: true,
  branches: true,
  foreshadowing: true,
  events: true,
})

const selected = ref<AtlasSelection | null>(null)
const atlasWindowStart = ref(1)
const ATLAS_LOCAL_THRESHOLD = 120
const ATLAS_WINDOW_SIZE = 80

const atlasChapterIndexes = computed(() =>
  collectNarrativeAtlasChapterIndexes({
    plan: props.plan,
    chapters: props.chapters,
  }),
)

const isAtlasWindowed = computed(() => atlasChapterIndexes.value.length > ATLAS_LOCAL_THRESHOLD)
const lastAtlasChapterIndex = computed(() =>
  atlasChapterIndexes.value.length
    ? atlasChapterIndexes.value[atlasChapterIndexes.value.length - 1]
    : atlasWindowStart.value,
)
const atlasWindowEnd = computed(() => Math.min(atlasWindowStart.value + ATLAS_WINDOW_SIZE - 1, lastAtlasChapterIndex.value))
const atlasScopeLabel = computed(() => `第${atlasWindowStart.value}-${atlasWindowEnd.value}章`)
const canPageAtlasPrevious = computed(() => atlasWindowStart.value > (atlasChapterIndexes.value[0] ?? 1))
const canPageAtlasNext = computed(() => atlasWindowEnd.value < lastAtlasChapterIndex.value)

const graph = computed<NarrativeAtlasGraph>(() =>
  buildNarrativeAtlasGraph({
    plan: props.plan,
    chapters: props.chapters,
    timeline: props.timeline,
    chapterRange: isAtlasWindowed.value
      ? { start: atlasWindowStart.value, end: atlasWindowEnd.value }
      : undefined,
  }),
)

const displayGraph = computed<NarrativeAtlasGraph>(() => {
  if (!isAtlasWindowed.value) return graph.value
  const visibleNodeIds = new Set<string>()
  const nodeById = new Map(graph.value.nodes.map((node) => [node.id, node]))

  for (const node of graph.value.nodes) {
    if (node.chapterIndex === undefined) continue
    if (node.chapterIndex >= atlasWindowStart.value && node.chapterIndex <= atlasWindowEnd.value) {
      visibleNodeIds.add(node.id)
    }
  }

  for (const edge of graph.value.edges) {
    const source = nodeById.get(edge.source)
    const target = nodeById.get(edge.target)
    if (visibleNodeIds.has(edge.source) && target && target.chapterIndex === undefined) {
      visibleNodeIds.add(edge.target)
    }
    if (visibleNodeIds.has(edge.target) && source && source.chapterIndex === undefined) {
      visibleNodeIds.add(edge.source)
    }
  }

  return {
    nodes: graph.value.nodes.filter((node) => visibleNodeIds.has(node.id)),
    edges: graph.value.edges.filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)),
    warnings: graph.value.warnings.filter((warning) =>
      (!warning.sourceId || visibleNodeIds.has(warning.sourceId))
      && (!warning.targetId || visibleNodeIds.has(warning.targetId)),
    ),
  }
})

const metrics = computed(() => ({
  ...collectNarrativeAtlasMetrics({
    plan: props.plan,
    chapters: props.chapters,
    timeline: props.timeline,
  }),
}))

const visibleSelectionIds = computed(() => {
  const ids = new Set<string>()
  const visibleNodeIds = new Set(
    displayGraph.value.nodes
      .filter((node) => layers[layerForNode(node)])
      .map((node) => node.id),
  )

  visibleNodeIds.forEach((id) => ids.add(`node:${id}`))
  displayGraph.value.edges
    .filter((edge) =>
      layers[layerForEdge(edge)]
      && visibleNodeIds.has(edge.source)
      && visibleNodeIds.has(edge.target),
    )
    .forEach((edge) => ids.add(`edge:${edge.id}`))

  return ids
})

watch(visibleSelectionIds, (ids) => {
  if (!selected.value) return
  if (!ids.has(`${selected.value.kind}:${selected.value.id}`)) {
    selected.value = null
  }
})

watch(() => props.plan, () => {
  selected.value = null
  atlasWindowStart.value = 1
})

function updateLayer(layer: AtlasLayer, value: boolean) {
  layers[layer] = value
}

function select(selection: AtlasSelection) {
  selected.value = selection
}

function navigate(payload: NavigatePayload) {
  emit('navigate', payload)
}

function pageAtlas(direction: -1 | 1) {
  const firstChapter = atlasChapterIndexes.value[0] ?? 1
  const lastChapter = lastAtlasChapterIndex.value
  atlasWindowStart.value = direction > 0
    ? Math.min(atlasWindowStart.value + ATLAS_WINDOW_SIZE, Math.max(firstChapter, lastChapter - ATLAS_WINDOW_SIZE + 1))
    : Math.max(firstChapter, atlasWindowStart.value - ATLAS_WINDOW_SIZE)
}

function layerForNode(node: NarrativeAtlasNode): AtlasLayer {
  if (node.type === 'plotline' || node.type === 'milestone') return 'branches'
  if (node.type === 'foreshadowing') return 'foreshadowing'
  if (node.type === 'event') return 'events'
  return 'trunk'
}

function layerForEdge(edge: NarrativeAtlasEdge): AtlasLayer {
  if (edge.type === 'branch') return 'branches'
  if (edge.type === 'event_anchor') return 'events'
  return edge.type
}
</script>

<template>
  <section class="narrative-atlas-view" data-testid="narrative-atlas-view">
    <div v-if="loading && !plan" class="narrative-atlas-view__empty">
      正在读取叙事规划...
    </div>
    <div v-else-if="!plan" class="narrative-atlas-view__empty">
      尚未生成叙事规划
    </div>

    <template v-else>
      <NarrativeAtlasControls
        :layers="layers"
        :metrics="metrics"
        @update-layer="updateLayer"
      />
      <div class="narrative-atlas-view__canvas-column">
        <div v-if="isAtlasWindowed" class="narrative-atlas-view__scope" data-testid="atlas-local-scope">
          <span>当前显示{{ atlasScopeLabel }}</span>
          <div>
            <button type="button" :disabled="!canPageAtlasPrevious" @click="pageAtlas(-1)">上一窗</button>
            <button type="button" :disabled="!canPageAtlasNext" @click="pageAtlas(1)">下一窗</button>
          </div>
        </div>
        <NarrativeAtlasCanvas
          :graph="displayGraph"
          :layers="layers"
          :selected="selected"
          @select="select"
        />
      </div>
      <NarrativeAtlasDetailPanel
        :graph="displayGraph"
        :selected="selected"
        @navigate="navigate"
      />
    </template>
  </section>
</template>

<style scoped>
.narrative-atlas-view {
  display: grid;
  grid-template-columns: 240px minmax(0, 1fr) 280px;
  height: 100%;
  min-height: 560px;
  overflow: hidden;
  background: var(--color-bg-primary);
}

.narrative-atlas-view__empty {
  grid-column: 1 / -1;
  display: grid;
  place-items: center;
  min-height: 320px;
  padding: var(--space-8);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  text-align: center;
}

.narrative-atlas-view__canvas-column {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
}

.narrative-atlas-view__scope {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.narrative-atlas-view__scope div {
  display: flex;
  gap: var(--space-2);
}

.narrative-atlas-view__scope button {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  cursor: pointer;
}

.narrative-atlas-view__scope button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

@media (max-width: 1080px) {
  .narrative-atlas-view {
    grid-template-columns: 220px minmax(0, 1fr);
    overflow: auto;
  }

  .narrative-atlas-view__canvas-column {
    min-height: 560px;
  }

  .narrative-atlas-view :deep(.narrative-atlas-detail) {
    grid-column: 1 / -1;
    border-top: 1px solid var(--color-border);
    border-left: 0;
  }
}

@media (max-width: 760px) {
  .narrative-atlas-view {
    grid-template-columns: minmax(0, 1fr);
    min-height: 0;
  }

  .narrative-atlas-view__canvas-column {
    min-height: 520px;
  }

  .narrative-atlas-view :deep(.narrative-atlas-controls),
  .narrative-atlas-view :deep(.narrative-atlas-detail) {
    border-right: 0;
    border-left: 0;
  }

  .narrative-atlas-view :deep(.narrative-atlas-canvas) {
    min-height: 520px;
  }
}
</style>
