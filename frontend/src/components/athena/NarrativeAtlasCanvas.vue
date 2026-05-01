<script setup lang="ts">
import { computed } from 'vue'
import type {
  NarrativeAtlasEdge,
  NarrativeAtlasGraph,
  NarrativeAtlasNode,
} from './narrativeAtlasGraph'

type AtlasLayer = 'trunk' | 'branches' | 'foreshadowing' | 'events'
type AtlasSelection = { kind: 'node'; id: string } | { kind: 'edge'; id: string }

interface AtlasNodePosition {
  node: NarrativeAtlasNode
  x: number
  y: number
  layer: AtlasLayer
}

interface AtlasEdgePosition {
  edge: NarrativeAtlasEdge
  layer: AtlasLayer
  source: AtlasNodePosition
  target: AtlasNodePosition
  path: string
}

const props = defineProps<{
  graph: NarrativeAtlasGraph
  layers: Record<AtlasLayer, boolean>
  selected: AtlasSelection | null
}>()

const emit = defineEmits<{
  select: [selection: AtlasSelection]
}>()

const canvasWidth = 1180
const minimumCanvasHeight = 560
const canvasTopPadding = 96
const chapterSpacing = 92
const eventNodeSpacing = 56
const nodePadding = 72
const chapterSpineX = 420
const foreshadowingTrackX = 300
const plotlineTrackX = 650
const milestoneTrackX = 760
const eventTrackX = 1040

const chapterNodes = computed(() =>
  props.graph.nodes
    .filter((node) => node.type === 'chapter')
    .slice()
    .sort((left, right) => Number(left.chapterIndex ?? 0) - Number(right.chapterIndex ?? 0)),
)

const eventStackExtraHeight = computed(() => {
  const counts = new Map<number, number>()
  props.graph.nodes
    .filter((node) => node.type === 'event' && node.chapterIndex !== undefined)
    .forEach((node) => counts.set(Number(node.chapterIndex), (counts.get(Number(node.chapterIndex)) ?? 0) + 1))

  const maxSameChapterEvents = Math.max(1, ...counts.values())
  return (maxSameChapterEvents - 1) * eventNodeSpacing
})

const canvasHeight = computed(() =>
  Math.max(
    minimumCanvasHeight,
    120 + Math.max(chapterNodes.value.length, 1) * chapterSpacing + eventStackExtraHeight.value,
  ),
)

const viewBox = computed(() => `0 0 ${canvasWidth} ${canvasHeight.value}`)

const positions = computed(() => {
  const map = new Map<string, AtlasNodePosition>()
  const chapterYByIndex = new Map<number, number>()

  chapterNodes.value.forEach((node, index) => {
    const y = canvasTopPadding + index * chapterSpacing
    if (node.chapterIndex !== undefined) chapterYByIndex.set(node.chapterIndex, y)
    map.set(node.id, { node, x: chapterSpineX, y, layer: 'trunk' })
  })

  placeLayer('plotline', plotlineTrackX, 'branches', map, chapterYByIndex)
  placeLayer('milestone', milestoneTrackX, 'branches', map, chapterYByIndex)
  placeLayer('foreshadowing', foreshadowingTrackX, 'foreshadowing', map, chapterYByIndex)
  placeLayer('event', eventTrackX, 'events', map, chapterYByIndex)

  return map
})

const visibleNodes = computed(() =>
  Array.from(positions.value.values()).filter((item) => props.layers[item.layer]),
)

const visibleNodeIds = computed(() => new Set(visibleNodes.value.map((item) => item.node.id)))

const visibleEdges = computed(() =>
  props.graph.edges
    .map((edge) => {
      const layer = edgeLayer(edge)
      const source = positions.value.get(edge.source)
      const target = positions.value.get(edge.target)
      if (!props.layers[layer] || !source || !target) return null
      if (!visibleNodeIds.value.has(source.node.id) || !visibleNodeIds.value.has(target.node.id)) return null
      return {
        edge,
        layer,
        source,
        target,
        path: edgePath(edge, source, target),
      }
    })
    .filter((edge): edge is AtlasEdgePosition => edge !== null),
)

function placeLayer(
  type: NarrativeAtlasNode['type'],
  x: number,
  layer: AtlasLayer,
  map: Map<string, AtlasNodePosition>,
  chapterYByIndex: Map<number, number>,
) {
  const nodes = props.graph.nodes.filter((node) => node.type === type)
  const perChapterCount = new Map<number, number>()
  const fallbackSpacing = nodes.length > 1
    ? (canvasHeight.value - canvasTopPadding * 2) / (nodes.length - 1)
    : 0

  nodes.forEach((node, index) => {
    const baseY = node.chapterIndex !== undefined && chapterYByIndex.has(node.chapterIndex)
      ? Number(chapterYByIndex.get(node.chapterIndex))
      : nodes.length > 1
        ? canvasTopPadding + index * fallbackSpacing
        : Math.min(canvasTopPadding + chapterSpacing, canvasHeight.value / 2)
    const chapterKey = node.chapterIndex ?? -index - 1
    const slot = perChapterCount.get(chapterKey) ?? 0
    perChapterCount.set(chapterKey, slot + 1)
    const offset = slotOffset(type, slot)
    map.set(node.id, {
      node,
      x: clamp(x + offset.x, nodePadding, canvasWidth - nodePadding),
      y: clamp(baseY + offset.y, 48, canvasHeight.value - 48),
      layer,
    })
  })
}

function edgeLayer(edge: NarrativeAtlasEdge): AtlasLayer {
  if (edge.type === 'branch') return 'branches'
  if (edge.type === 'event_anchor') return 'events'
  return edge.type
}

function nodeLayer(node: NarrativeAtlasNode): AtlasLayer {
  if (node.type === 'plotline' || node.type === 'milestone') return 'branches'
  if (node.type === 'foreshadowing') return 'foreshadowing'
  if (node.type === 'event') return 'events'
  return 'trunk'
}

function edgePath(edge: NarrativeAtlasEdge, source: AtlasNodePosition, target: AtlasNodePosition) {
  if (edge.type === 'trunk') return `M ${source.x} ${source.y} L ${target.x} ${target.y}`

  const middleX = source.x + (target.x - source.x) / 2
  const curveBias = edge.type === 'foreshadowing'
    ? target.x < source.x ? -28 : 28
    : edge.type === 'event_anchor'
      ? 36
      : 20
  return `M ${source.x} ${source.y} C ${middleX + curveBias} ${source.y}, ${middleX + curveBias} ${target.y}, ${target.x} ${target.y}`
}

function selectNode(node: NarrativeAtlasNode) {
  emit('select', { kind: 'node', id: node.id })
}

function selectEdge(edge: NarrativeAtlasEdge) {
  emit('select', { kind: 'edge', id: edge.id })
}

function isNodeSelected(node: NarrativeAtlasNode) {
  return props.selected?.kind === 'node' && props.selected.id === node.id
}

function isEdgeSelected(edge: NarrativeAtlasEdge) {
  return props.selected?.kind === 'edge' && props.selected.id === edge.id
}

function nodeClass(node: NarrativeAtlasNode) {
  return [
    'narrative-atlas-canvas__node',
    `narrative-atlas-canvas__node--${node.type}`,
    { 'narrative-atlas-canvas__node--selected': isNodeSelected(node) },
  ]
}

function edgeClass(edge: NarrativeAtlasEdge) {
  return [
    'narrative-atlas-canvas__edge',
    `narrative-atlas-canvas__edge--${edge.type}`,
    { 'narrative-atlas-canvas__edge--selected': isEdgeSelected(edge) },
  ]
}

function nodeTitle(node: NarrativeAtlasNode) {
  const chapter = node.chapterIndex !== undefined ? `第${node.chapterIndex}章，` : ''
  return `${chapter}${node.label}`
}

function displayNodeLabel(node: NarrativeAtlasNode) {
  if (node.chapterIndex && node.type === 'chapter') return `第${node.chapterIndex}章`
  return node.label.length > 9 ? `${node.label.slice(0, 9)}...` : node.label
}

function edgeTitle(edge: NarrativeAtlasEdge) {
  const source = positions.value.get(edge.source)?.node.label ?? edge.source
  const target = positions.value.get(edge.target)?.node.label ?? edge.target
  return `${source} 到 ${target}`
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max)
}

function slotOffset(type: NarrativeAtlasNode['type'], slot: number) {
  const lane = slot % 3
  const row = Math.floor(slot / 3)
  const y = (lane - 1) * 14 + row * 42

  if (type === 'foreshadowing') return { x: -lane * 112, y }
  if (type === 'event') return { x: 0, y: slot * eventNodeSpacing }
  if (type === 'milestone') return { x: lane * 126, y }
  if (type === 'plotline') return { x: (slot % 2) * 126, y: Math.floor(slot / 2) * 42 }

  return { x: 0, y: 0 }
}
</script>

<template>
  <section class="narrative-atlas-canvas" data-testid="narrative-atlas-canvas" aria-label="叙事图谱画布">
    <svg :viewBox="viewBox" :width="canvasWidth" :height="canvasHeight" role="img" aria-label="Athena Narrative Atlas">
      <defs>
        <marker
          v-for="layer in ['trunk', 'branches', 'foreshadowing', 'events']"
          :id="`atlas-arrow-${layer}`"
          :key="layer"
          markerWidth="8"
          markerHeight="8"
          refX="6"
          refY="4"
          orient="auto"
        >
          <path d="M 0 0 L 8 4 L 0 8 z" class="narrative-atlas-canvas__marker" />
        </marker>
      </defs>

      <g class="narrative-atlas-canvas__grid" aria-hidden="true">
        <line :x1="chapterSpineX" y1="56" :x2="chapterSpineX" :y2="canvasHeight - 56" />
        <text :x="foreshadowingTrackX - 40" y="52">伏笔</text>
        <text :x="chapterSpineX - 34" y="52">章节</text>
        <text :x="plotlineTrackX - 34" y="52">故事线</text>
        <text :x="eventTrackX - 24" y="52">事件</text>
      </g>

      <g class="narrative-atlas-canvas__edges">
        <path
          v-for="item in visibleEdges"
          :key="item.edge.id"
          :class="edgeClass(item.edge)"
          :d="item.path"
          :data-atlas-layer="item.layer"
          :data-atlas-edge-id="item.edge.id"
          :aria-label="edgeTitle(item.edge)"
          :aria-pressed="isEdgeSelected(item.edge)"
          role="button"
          tabindex="0"
          marker-end="url(#atlas-arrow-trunk)"
          @click="selectEdge(item.edge)"
          @keydown.enter.prevent="selectEdge(item.edge)"
          @keydown.space.prevent="selectEdge(item.edge)"
        />
      </g>

      <g class="narrative-atlas-canvas__nodes">
        <g
          v-for="item in visibleNodes"
          :key="item.node.id"
          :class="nodeClass(item.node)"
          :data-atlas-layer="nodeLayer(item.node)"
          :data-atlas-node-id="item.node.id"
          :aria-label="nodeTitle(item.node)"
          :aria-pressed="isNodeSelected(item.node)"
          role="button"
          tabindex="0"
          :transform="`translate(${item.x}, ${item.y})`"
          @click="selectNode(item.node)"
          @keydown.enter.prevent="selectNode(item.node)"
          @keydown.space.prevent="selectNode(item.node)"
        >
          <circle v-if="item.node.type === 'chapter'" r="28" />
          <rect v-else x="-56" y="-20" width="112" height="40" rx="6" />
          <text text-anchor="middle" dominant-baseline="middle">
            {{ displayNodeLabel(item.node) }}
          </text>
          <title>{{ nodeTitle(item.node) }}</title>
        </g>
      </g>
    </svg>
  </section>
</template>

<style scoped>
.narrative-atlas-canvas {
  min-width: 0;
  height: 100%;
  overflow: auto;
  background:
    linear-gradient(180deg, rgba(79, 70, 229, 0.04), transparent 220px),
    var(--color-bg-primary);
}

.narrative-atlas-canvas svg {
  display: block;
  min-width: 720px;
  width: auto;
  height: auto;
  max-width: none;
}

.narrative-atlas-canvas__grid line {
  stroke: var(--color-border-strong);
  stroke-dasharray: 6 8;
  stroke-width: 1.2;
}

.narrative-atlas-canvas__grid text {
  fill: var(--color-text-tertiary);
  font-size: 12px;
  font-weight: var(--font-semibold);
}

.narrative-atlas-canvas__edge {
  fill: none;
  stroke: var(--color-text-tertiary);
  stroke-width: 2;
  stroke-linecap: round;
  cursor: pointer;
  outline: none;
}

.narrative-atlas-canvas__edge:focus-visible,
.narrative-atlas-canvas__node:focus-visible {
  outline: 2px solid var(--color-brand);
  outline-offset: 4px;
}

.narrative-atlas-canvas__edge--trunk {
  stroke: #475569;
  stroke-width: 3;
}

.narrative-atlas-canvas__edge--branch {
  stroke: var(--color-brand);
}

.narrative-atlas-canvas__edge--foreshadowing {
  stroke: var(--color-warning);
  stroke-dasharray: 7 6;
}

.narrative-atlas-canvas__edge--event_anchor {
  stroke: var(--color-success);
  stroke-dasharray: 3 5;
}

.narrative-atlas-canvas__edge--selected {
  stroke-width: 4;
  filter: drop-shadow(0 2px 3px rgba(26, 26, 26, 0.18));
}

.narrative-atlas-canvas__marker {
  fill: currentColor;
}

.narrative-atlas-canvas__node {
  cursor: pointer;
  outline: none;
}

.narrative-atlas-canvas__node circle,
.narrative-atlas-canvas__node rect {
  fill: var(--color-bg-white);
  stroke: var(--color-border-strong);
  stroke-width: 1.5;
  filter: drop-shadow(0 8px 12px rgba(26, 26, 26, 0.08));
}

.narrative-atlas-canvas__node text {
  max-width: 104px;
  fill: var(--color-text-primary);
  font-size: 12px;
  font-weight: var(--font-semibold);
  pointer-events: none;
}

.narrative-atlas-canvas__node--chapter circle {
  fill: var(--color-brand-light);
  stroke: var(--color-brand);
}

.narrative-atlas-canvas__node--plotline rect,
.narrative-atlas-canvas__node--milestone rect {
  fill: #F8FAFC;
  stroke: var(--color-brand);
}

.narrative-atlas-canvas__node--foreshadowing rect {
  fill: var(--color-warning-light);
  stroke: var(--color-warning);
}

.narrative-atlas-canvas__node--event rect {
  fill: var(--color-success-light);
  stroke: var(--color-success);
}

.narrative-atlas-canvas__node--selected circle,
.narrative-atlas-canvas__node--selected rect {
  stroke-width: 3;
  filter: drop-shadow(0 10px 16px rgba(79, 70, 229, 0.22));
}
</style>
