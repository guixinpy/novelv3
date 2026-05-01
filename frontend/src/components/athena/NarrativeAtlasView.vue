<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import NarrativeAtlasCanvas from './NarrativeAtlasCanvas.vue'
import NarrativeAtlasControls from './NarrativeAtlasControls.vue'
import NarrativeAtlasDetailPanel from './NarrativeAtlasDetailPanel.vue'
import { buildNarrativeAtlasGraph } from './narrativeAtlasGraph'
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

const graph = computed<NarrativeAtlasGraph>(() =>
  buildNarrativeAtlasGraph({
    plan: props.plan,
    chapters: props.chapters,
    timeline: props.timeline,
  }),
)

const metrics = computed(() => ({
  chapters: graph.value.nodes.filter((node) => node.type === 'chapter').length,
  plotlines: graph.value.nodes.filter((node) => node.type === 'plotline').length,
  foreshadowing: graph.value.nodes.filter((node) => node.type === 'foreshadowing').length,
  events: graph.value.nodes.filter((node) => node.type === 'event').length,
}))

const visibleSelectionIds = computed(() => {
  const ids = new Set<string>()
  const visibleNodeIds = new Set(
    graph.value.nodes
      .filter((node) => layers[layerForNode(node)])
      .map((node) => node.id),
  )

  visibleNodeIds.forEach((id) => ids.add(`node:${id}`))
  graph.value.edges
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
    <div v-if="!plan" class="narrative-atlas-view__empty">
      尚未生成叙事规划
    </div>

    <template v-else>
      <NarrativeAtlasControls
        :layers="layers"
        :metrics="metrics"
        @update-layer="updateLayer"
      />
      <NarrativeAtlasCanvas
        :graph="graph"
        :layers="layers"
        :selected="selected"
        @select="select"
      />
      <NarrativeAtlasDetailPanel
        :graph="graph"
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

@media (max-width: 1080px) {
  .narrative-atlas-view {
    grid-template-columns: 220px minmax(0, 1fr);
    overflow: auto;
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
