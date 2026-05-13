<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
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

interface PanStart {
  x: number
  y: number
  scrollLeft: number
  scrollTop: number
}

const canvasWidth = 1360
const minimumCanvasHeight = 560
const canvasTopPadding = 96
const chapterSpacing = 92
const eventNodeSpacing = 56
const nodePadding = 72
const rectNodeHalfWidth = 56
const rectNodeHalfHeight = 20
const rectNodeWidth = rectNodeHalfWidth * 2
const rectNodeHeight = rectNodeHalfHeight * 2
const foreshadowingLaneCount = 2
const foreshadowingLaneSpacing = rectNodeWidth + 32
const chapterSpineX = 420
const foreshadowingTrackX = 300
const plotlineTrackX = 650
const milestoneTrackX = 900
const eventTrackX = 1200
const minZoom = 0.5
const maxZoom = 1.8
const zoomStep = 0.1

const canvasRef = ref<HTMLElement | null>(null)
const zoom = ref(1)
const isSpacePanning = ref(false)
const isDraggingCanvas = ref(false)
const panStart = ref<PanStart | null>(null)

const chapterNodes = computed(() =>
  props.graph.nodes
    .filter((node) => node.type === 'chapter')
    .slice()
    .sort((left, right) => Number(left.chapterIndex ?? 0) - Number(right.chapterIndex ?? 0)),
)

const stackRowsByChapter = computed(() => {
  const rightSideCounts = new Map<number, number>()
  const foreshadowingCounts = new Map<number, number>()

  props.graph.nodes.forEach((node) => {
    if (node.chapterIndex === undefined) return
    const chapterIndex = Number(node.chapterIndex)
    if (node.type === 'event' || node.type === 'milestone') {
      rightSideCounts.set(chapterIndex, (rightSideCounts.get(chapterIndex) ?? 0) + 1)
    }
    if (node.type === 'foreshadowing') {
      foreshadowingCounts.set(chapterIndex, (foreshadowingCounts.get(chapterIndex) ?? 0) + 1)
    }
  })

  const counts = new Map<number, number>()
  const chapterIndexes = new Set([...rightSideCounts.keys(), ...foreshadowingCounts.keys()])
  chapterIndexes.forEach((chapterIndex) => {
    counts.set(chapterIndex, Math.max(
      rightSideCounts.get(chapterIndex) ?? 0,
      Math.ceil((foreshadowingCounts.get(chapterIndex) ?? 0) / foreshadowingLaneCount),
    ))
  })

  return counts
})

const chapterLayout = computed(() => {
  const yByIndex = new Map<number, number>()
  let nextChapterY = canvasTopPadding

  chapterNodes.value.forEach((node) => {
    if (node.chapterIndex !== undefined) {
      const chapterIndex = Number(node.chapterIndex)
      yByIndex.set(chapterIndex, nextChapterY)
      nextChapterY += chapterRowHeight(stackRowsByChapter.value.get(chapterIndex) ?? 0)
      return
    }

    nextChapterY += chapterSpacing
  })

  return {
    height: Math.max(minimumCanvasHeight, nextChapterY + nodePadding),
    yByIndex,
  }
})

const canvasHeight = computed(() => chapterLayout.value.height)

const viewBox = computed(() => `0 0 ${canvasWidth} ${canvasHeight.value}`)
const scaledCanvasWidth = computed(() => Math.round(canvasWidth * zoom.value))
const scaledCanvasHeight = computed(() => Math.round(canvasHeight.value * zoom.value))
const zoomPercent = computed(() => Math.round(zoom.value * 100))

const positions = computed(() => {
  const map = new Map<string, AtlasNodePosition>()
  const chapterYByIndex = chapterLayout.value.yByIndex

  chapterNodes.value.forEach((node, index) => {
    const y = node.chapterIndex !== undefined
      ? chapterYByIndex.get(Number(node.chapterIndex)) ?? canvasTopPadding + index * chapterSpacing
      : canvasTopPadding + index * chapterSpacing
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

  const anchors = edgeAnchorPoints(edge, source, target)
  const middleX = anchors.source.x + (anchors.target.x - anchors.source.x) / 2
  const curveBias = edgeCurveBias(edge, anchors.source, anchors.target)
  return `M ${anchors.source.x} ${anchors.source.y} C ${middleX + curveBias} ${anchors.source.y}, ${middleX + curveBias} ${anchors.target.y}, ${anchors.target.x} ${anchors.target.y}`
}

function edgeHandlePoint(item: AtlasEdgePosition) {
  if (item.edge.type === 'trunk') {
    return {
      x: item.source.x + (item.target.x - item.source.x) / 2,
      y: item.source.y + (item.target.y - item.source.y) / 2,
    }
  }

  const anchors = edgeAnchorPoints(item.edge, item.source, item.target)
  const middleX = anchors.source.x + (anchors.target.x - anchors.source.x) / 2
  const curveBias = edgeCurveBias(item.edge, anchors.source, anchors.target)

  return cubicPoint(
    { x: anchors.source.x, y: anchors.source.y },
    { x: middleX + curveBias, y: anchors.source.y },
    { x: middleX + curveBias, y: anchors.target.y },
    { x: anchors.target.x, y: anchors.target.y },
    0.5,
  )
}

function edgeAnchorPoints(edge: NarrativeAtlasEdge, source: AtlasNodePosition, target: AtlasNodePosition) {
  if (edge.type === 'trunk') return { source, target }

  const direction = Math.sign(target.x - source.x)
  if (direction === 0) return { source, target }

  return {
    source: {
      x: source.x + direction * nodeHorizontalRadius(source.node),
      y: source.y,
    },
    target: {
      x: target.x - direction * nodeHorizontalRadius(target.node),
      y: target.y,
    },
  }
}

function nodeHorizontalRadius(node: NarrativeAtlasNode) {
  return node.type === 'chapter' ? 28 : rectNodeHalfWidth
}

function edgeCurveBias(
  edge: NarrativeAtlasEdge,
  source: { x: number; y: number },
  target: { x: number; y: number },
) {
  if (edge.type === 'foreshadowing') return target.x < source.x ? -28 : 28
  if (edge.type === 'event_anchor') return 36
  return 20
}

function cubicPoint(
  start: { x: number; y: number },
  controlA: { x: number; y: number },
  controlB: { x: number; y: number },
  end: { x: number; y: number },
  t: number,
) {
  const inverse = 1 - t
  const startWeight = inverse ** 3
  const controlAWeight = 3 * inverse ** 2 * t
  const controlBWeight = 3 * inverse * t ** 2
  const endWeight = t ** 3

  return {
    x: start.x * startWeight + controlA.x * controlAWeight + controlB.x * controlBWeight + end.x * endWeight,
    y: start.y * startWeight + controlA.y * controlAWeight + controlB.y * controlBWeight + end.y * endWeight,
  }
}

function selectNode(node: NarrativeAtlasNode) {
  emit('select', { kind: 'node', id: node.id })
}

function selectEdge(edge: NarrativeAtlasEdge) {
  emit('select', { kind: 'edge', id: edge.id })
}

function handleWheel(event: WheelEvent) {
  event.preventDefault()
  const canvas = canvasRef.value
  const previousZoom = zoom.value
  const nextZoom = clamp(
    Number((previousZoom + (event.deltaY < 0 ? zoomStep : -zoomStep)).toFixed(2)),
    minZoom,
    maxZoom,
  )
  if (nextZoom === previousZoom) return

  const rect = canvas?.getBoundingClientRect()
  const pointerX = rect ? event.clientX - rect.left : 0
  const pointerY = rect ? event.clientY - rect.top : 0
  const contentX = canvas ? (canvas.scrollLeft + pointerX) / previousZoom : 0
  const contentY = canvas ? (canvas.scrollTop + pointerY) / previousZoom : 0

  zoom.value = nextZoom

  if (!canvas) return
  void nextTick(() => {
    canvas.scrollLeft = Math.max(0, contentX * nextZoom - pointerX)
    canvas.scrollTop = Math.max(0, contentY * nextZoom - pointerY)
  })
}

function resetZoom() {
  zoom.value = 1
}

function handleCanvasMouseDown(event: MouseEvent) {
  if (!isSpacePanning.value || event.button !== 0) return
  const canvas = canvasRef.value
  if (!canvas) return
  event.preventDefault()
  isDraggingCanvas.value = true
  panStart.value = {
    x: event.clientX,
    y: event.clientY,
    scrollLeft: canvas.scrollLeft,
    scrollTop: canvas.scrollTop,
  }
}

function handleMouseMove(event: MouseEvent) {
  if (!isDraggingCanvas.value || !panStart.value || !canvasRef.value) return
  event.preventDefault()
  canvasRef.value.scrollLeft = panStart.value.scrollLeft - (event.clientX - panStart.value.x)
  canvasRef.value.scrollTop = panStart.value.scrollTop - (event.clientY - panStart.value.y)
}

function endCanvasDrag() {
  isDraggingCanvas.value = false
  panStart.value = null
}

function handleKeyDown(event: KeyboardEvent) {
  if (event.code !== 'Space' || isInteractiveTarget(event.target)) return
  event.preventDefault()
  isSpacePanning.value = true
}

function handleKeyUp(event: KeyboardEvent) {
  if (event.code !== 'Space') return
  isSpacePanning.value = false
  endCanvasDrag()
}

function isInteractiveTarget(target: EventTarget | null) {
  if (!(target instanceof HTMLElement)) return false
  return Boolean(target.closest('button, input, textarea, select, [role="button"]'))
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

function chapterRowHeight(eventCount: number) {
  return Math.max(chapterSpacing, Math.max(1, eventCount) * eventNodeSpacing + 36)
}

function slotOffset(type: NarrativeAtlasNode['type'], slot: number) {
  if (type === 'foreshadowing') {
    return {
      x: -(slot % foreshadowingLaneCount) * foreshadowingLaneSpacing,
      y: Math.floor(slot / foreshadowingLaneCount) * eventNodeSpacing,
    }
  }

  if (type === 'event') return { x: 0, y: slot * eventNodeSpacing }
  if (type === 'milestone') return { x: 0, y: slot * eventNodeSpacing }
  if (type === 'plotline') return { x: (slot % 2) * 126, y: Math.floor(slot / 2) * 42 }

  return { x: 0, y: 0 }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown)
  window.addEventListener('keyup', handleKeyUp)
  window.addEventListener('mousemove', handleMouseMove)
  window.addEventListener('mouseup', endCanvasDrag)
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeyDown)
  window.removeEventListener('keyup', handleKeyUp)
  window.removeEventListener('mousemove', handleMouseMove)
  window.removeEventListener('mouseup', endCanvasDrag)
})
</script>

<template>
  <section
    ref="canvasRef"
    class="narrative-atlas-canvas"
    :class="{
      'narrative-atlas-canvas--space-panning': isSpacePanning,
      'narrative-atlas-canvas--dragging': isDraggingCanvas,
    }"
    data-testid="narrative-atlas-canvas"
    :data-atlas-zoom="zoomPercent"
    :data-atlas-panning="String(isDraggingCanvas)"
    aria-label="叙事图谱画布"
    @wheel="handleWheel"
    @mousedown="handleCanvasMouseDown"
  >
    <div class="narrative-atlas-canvas__toolbar" aria-label="图谱视图控制">
      <span>{{ zoomPercent }}%</span>
      <button type="button" @click="resetZoom">重置</button>
    </div>
    <svg :viewBox="viewBox" :width="scaledCanvasWidth" :height="scaledCanvasHeight" role="img" aria-label="Athena Narrative Atlas">
      <defs>
        <marker
          v-for="layer in ['trunk', 'branches', 'foreshadowing', 'events']"
          :id="`atlas-arrow-${layer}`"
          :key="layer"
          markerUnits="userSpaceOnUse"
          markerWidth="6"
          markerHeight="6"
          refX="5.2"
          refY="3"
          viewBox="0 0 6 6"
          orient="auto"
        >
          <path
            d="M 0.8 1.2 L 5.2 3 L 0.8 4.8 z"
            :class="['narrative-atlas-canvas__marker', `narrative-atlas-canvas__marker--${layer}`]"
          />
        </marker>
      </defs>

      <g class="narrative-atlas-canvas__grid" aria-hidden="true">
        <line :x1="chapterSpineX" y1="56" :x2="chapterSpineX" :y2="canvasHeight - 56" />
        <text :x="foreshadowingTrackX - 40" y="52">伏笔</text>
        <text :x="chapterSpineX - 34" y="52">章节</text>
        <text :x="plotlineTrackX - 34" y="52">故事线</text>
        <text :x="milestoneTrackX - 34" y="52">里程碑</text>
        <text :x="eventTrackX - 24" y="52">事件</text>
      </g>

      <g class="narrative-atlas-canvas__edges">
        <template
          v-for="item in visibleEdges"
          :key="item.edge.id"
        >
          <path
            :class="[edgeClass(item.edge), 'narrative-atlas-canvas__edge-hitbox']"
            :d="item.path"
            :data-atlas-edge-hitbox-id="item.edge.id"
            aria-hidden="true"
            @click="selectEdge(item.edge)"
          />
          <path
            :class="[edgeClass(item.edge), 'narrative-atlas-canvas__edge-line']"
            :d="item.path"
            :data-atlas-edge-line-id="item.edge.id"
            aria-hidden="true"
            :marker-end="`url(#atlas-arrow-${item.layer})`"
          />
        </template>
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
          <rect
            v-else
            :x="-rectNodeHalfWidth"
            :y="-rectNodeHalfHeight"
            :width="rectNodeWidth"
            :height="rectNodeHeight"
            rx="6"
          />
          <text text-anchor="middle" dominant-baseline="middle">
            {{ displayNodeLabel(item.node) }}
          </text>
          <title>{{ nodeTitle(item.node) }}</title>
        </g>
      </g>

      <g class="narrative-atlas-canvas__edge-handles">
        <circle
          v-for="item in visibleEdges"
          :key="`handle:${item.edge.id}`"
          :class="[edgeClass(item.edge), 'narrative-atlas-canvas__edge-handle']"
          :cx="edgeHandlePoint(item).x"
          :cy="edgeHandlePoint(item).y"
          r="11"
          :data-atlas-layer="item.layer"
          :data-atlas-edge-id="item.edge.id"
          :aria-label="edgeTitle(item.edge)"
          :aria-pressed="isEdgeSelected(item.edge)"
          role="button"
          tabindex="0"
          @click.stop="selectEdge(item.edge)"
          @keydown.enter.prevent="selectEdge(item.edge)"
          @keydown.space.prevent="selectEdge(item.edge)"
        />
      </g>
    </svg>
  </section>
</template>

<style scoped>
.narrative-atlas-canvas {
  position: relative;
  min-width: 0;
  height: 100%;
  overflow: auto;
  background:
    linear-gradient(180deg, rgba(79, 70, 229, 0.04), transparent 220px),
    var(--color-bg-primary);
  cursor: default;
  overscroll-behavior: contain;
}

.narrative-atlas-canvas svg {
  display: block;
  min-width: 720px;
  width: auto;
  height: auto;
  max-width: none;
}

.narrative-atlas-canvas--space-panning {
  cursor: grab;
}

.narrative-atlas-canvas--dragging {
  cursor: grabbing;
  user-select: none;
}

.narrative-atlas-canvas__toolbar {
  position: sticky;
  top: var(--space-2);
  left: var(--space-2);
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  margin: var(--space-2);
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.92);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  box-shadow: var(--shadow-sm);
}

.narrative-atlas-canvas__toolbar button {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--color-brand);
  font: inherit;
  cursor: pointer;
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
  stroke-linecap: round;
  cursor: pointer;
  outline: none;
}

.narrative-atlas-canvas__edge-hitbox,
.narrative-atlas-canvas__edge-line {
  fill: none;
  stroke-linecap: round;
}

.narrative-atlas-canvas__edge-hitbox {
  stroke: rgba(15, 23, 42, 0.01);
  stroke-width: 18;
  pointer-events: stroke;
}

.narrative-atlas-canvas__edge-handle {
  fill: rgba(15, 23, 42, 0.01);
  stroke: transparent;
  stroke-width: 1.5;
  cursor: pointer;
  outline: none;
}

.narrative-atlas-canvas__edge-line {
  stroke: var(--color-text-tertiary);
  stroke-width: 2;
  pointer-events: none;
}

.narrative-atlas-canvas__edge:focus-visible,
.narrative-atlas-canvas__edge-handle:focus-visible,
.narrative-atlas-canvas__node:focus-visible {
  outline: 2px solid var(--color-brand);
  outline-offset: 4px;
}

.narrative-atlas-canvas__edge-handle:hover,
.narrative-atlas-canvas__edge-handle:focus-visible {
  fill: rgba(79, 70, 229, 0.16);
  stroke: rgba(79, 70, 229, 0.5);
}

.narrative-atlas-canvas__edge--trunk.narrative-atlas-canvas__edge-line {
  stroke: #475569;
  stroke-width: 3;
}

.narrative-atlas-canvas__edge--branch.narrative-atlas-canvas__edge-line {
  stroke: var(--color-brand);
  stroke-width: 1.5;
  opacity: 0.62;
}

.narrative-atlas-canvas__edge--foreshadowing.narrative-atlas-canvas__edge-line {
  stroke: var(--color-warning);
  stroke-dasharray: 7 6;
}

.narrative-atlas-canvas__edge--event_anchor.narrative-atlas-canvas__edge-line {
  stroke: var(--color-success);
  stroke-dasharray: 3 5;
}

.narrative-atlas-canvas__edge--selected.narrative-atlas-canvas__edge-line {
  stroke-width: 4;
  opacity: 1;
  filter: drop-shadow(0 2px 3px rgba(26, 26, 26, 0.18));
}

.narrative-atlas-canvas__edge--selected.narrative-atlas-canvas__edge-handle {
  fill: rgba(79, 70, 229, 0.22);
  stroke: var(--color-brand);
}

.narrative-atlas-canvas__marker {
  fill: currentColor;
  fill-opacity: 0.7;
}

.narrative-atlas-canvas__marker--trunk {
  fill: #475569;
}

.narrative-atlas-canvas__marker--branches {
  fill: var(--color-brand);
  fill-opacity: 0.58;
}

.narrative-atlas-canvas__marker--foreshadowing {
  fill: var(--color-warning);
}

.narrative-atlas-canvas__marker--events {
  fill: var(--color-success);
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
