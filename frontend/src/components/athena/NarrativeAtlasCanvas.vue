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

const viewBox = '0 0 1040 560'
const canvasWidth = 1040
const leftPadding = 88
const rightPadding = 88

const chapterNodes = computed(() =>
  props.graph.nodes
    .filter((node) => node.type === 'chapter')
    .slice()
    .sort((left, right) => Number(left.chapterIndex ?? 0) - Number(right.chapterIndex ?? 0)),
)

const positions = computed(() => {
  const map = new Map<string, AtlasNodePosition>()
  const chapterXByIndex = new Map<number, number>()
  const chapterSpacing = chapterNodes.value.length > 1
    ? (canvasWidth - leftPadding - rightPadding) / (chapterNodes.value.length - 1)
    : 0

  chapterNodes.value.forEach((node, index) => {
    const x = chapterNodes.value.length > 1 ? leftPadding + index * chapterSpacing : canvasWidth / 2
    if (node.chapterIndex !== undefined) chapterXByIndex.set(node.chapterIndex, x)
    map.set(node.id, { node, x, y: 270, layer: 'trunk' })
  })

  placeLayer('plotline', 92, 'branches', map, chapterXByIndex)
  placeLayer('milestone', 170, 'branches', map, chapterXByIndex)
  placeLayer('foreshadowing', 382, 'foreshadowing', map, chapterXByIndex)
  placeLayer('event', 470, 'events', map, chapterXByIndex)

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
  y: number,
  layer: AtlasLayer,
  map: Map<string, AtlasNodePosition>,
  chapterXByIndex: Map<number, number>,
) {
  const nodes = props.graph.nodes.filter((node) => node.type === type)
  const perChapterCount = new Map<number, number>()
  const fallbackSpacing = nodes.length > 1
    ? (canvasWidth - leftPadding - rightPadding) / (nodes.length - 1)
    : 0

  nodes.forEach((node, index) => {
    const baseX = node.chapterIndex !== undefined && chapterXByIndex.has(node.chapterIndex)
      ? Number(chapterXByIndex.get(node.chapterIndex))
      : nodes.length > 1
        ? leftPadding + index * fallbackSpacing
        : canvasWidth / 2
    const chapterKey = node.chapterIndex ?? -index - 1
    const slot = perChapterCount.get(chapterKey) ?? 0
    perChapterCount.set(chapterKey, slot + 1)
    const offset = type === 'plotline' ? 0 : (slot % 3 - 1) * 34 + Math.floor(slot / 3) * 18
    map.set(node.id, { node, x: clamp(baseX + offset, 56, canvasWidth - 56), y, layer })
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

  const middleY = source.y + (target.y - source.y) / 2
  const curveBias = edge.type === 'foreshadowing' ? 26 : 0
  return `M ${source.x} ${source.y} C ${source.x} ${middleY + curveBias}, ${target.x} ${middleY + curveBias}, ${target.x} ${target.y}`
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
</script>

<template>
  <section class="narrative-atlas-canvas" data-testid="narrative-atlas-canvas" aria-label="叙事图谱画布">
    <svg :viewBox="viewBox" role="img" aria-label="Athena Narrative Atlas">
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
        <line x1="64" y1="270" x2="976" y2="270" />
        <text x="72" y="72">故事线</text>
        <text x="72" y="250">章节</text>
        <text x="72" y="358">伏笔</text>
        <text x="72" y="448">事件</text>
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
  width: 100%;
  height: 100%;
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
