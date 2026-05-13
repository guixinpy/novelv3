// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import NarrativeAtlasCanvas from './NarrativeAtlasCanvas.vue'
import type { NarrativeAtlasGraph } from './narrativeAtlasGraph'

function longChapterGraph(chapterCount: number): NarrativeAtlasGraph {
  const nodes = Array.from({ length: chapterCount }, (_, index) => {
    const chapterIndex = index + 1
    return {
      id: `chapter:${chapterIndex}`,
      type: 'chapter' as const,
      label: `第${chapterIndex}章`,
      chapterIndex,
    }
  })
  const edges = nodes.slice(1).map((node, index) => ({
    id: `trunk:${nodes[index].id}->${node.id}`,
    type: 'trunk' as const,
    source: nodes[index].id,
    target: node.id,
  }))

  return { nodes, edges, warnings: [] }
}

function sameChapterEventGraph(eventCount: number, chapterCount = 1): NarrativeAtlasGraph {
  const graph = longChapterGraph(chapterCount)
  const chapter = graph.nodes[graph.nodes.length - 1]
  const chapterIndex = Number(chapter.chapterIndex)
  const events = Array.from({ length: eventCount }, (_, index) => ({
    id: `event:chapter-${chapterIndex}-${index + 1}`,
    type: 'event' as const,
    label: `第${chapterIndex}章事件${index + 1}`,
    chapterIndex,
  }))
  const edges = events.map((event) => ({
    id: `event_anchor:${chapter.id}->${event.id}`,
    type: 'event_anchor' as const,
    source: chapter.id,
    target: event.id,
  }))

  return { nodes: [...graph.nodes, ...events], edges: [...graph.edges, ...edges], warnings: [] }
}

function adjacentChapterEventGraph(): NarrativeAtlasGraph {
  const graph = longChapterGraph(2)
  const eventCounts = new Map([
    [1, 3],
    [2, 1],
  ])
  const events = graph.nodes.flatMap((chapter) => {
    const chapterIndex = Number(chapter.chapterIndex)
    return Array.from({ length: eventCounts.get(chapterIndex) ?? 0 }, (_, index) => ({
      id: `event:chapter-${chapterIndex}-${index + 1}`,
      type: 'event' as const,
      label: `第${chapterIndex}章事件${index + 1}`,
      chapterIndex,
    }))
  })
  const edges = events.map((event) => ({
    id: `event_anchor:chapter:${event.chapterIndex}->${event.id}`,
    type: 'event_anchor' as const,
    source: `chapter:${event.chapterIndex}`,
    target: event.id,
  }))

  return { nodes: [...graph.nodes, ...events], edges: [...graph.edges, ...edges], warnings: [] }
}

function milestoneAndEventTrackGraph(): NarrativeAtlasGraph {
  const graph = longChapterGraph(1)
  const plotline = {
    id: 'plotline:main',
    type: 'plotline' as const,
    label: '主线',
  }
  const milestones = [1, 2, 3].map((index) => ({
    id: `milestone:main:${index}`,
    type: 'milestone' as const,
    label: `里程碑${index}`,
    chapterIndex: 1,
  }))
  const event = {
    id: 'event:chapter-1',
    type: 'event' as const,
    label: '真实事件',
    chapterIndex: 1,
  }
  const edges = [
    ...milestones.map((milestone) => ({
      id: `branch:${plotline.id}->${milestone.id}`,
      type: 'branch' as const,
      source: plotline.id,
      target: milestone.id,
    })),
    {
      id: `event_anchor:chapter:1->${event.id}`,
      type: 'event_anchor' as const,
      source: 'chapter:1',
      target: event.id,
    },
  ]

  return { nodes: [...graph.nodes, plotline, ...milestones, event], edges: [...graph.edges, ...edges], warnings: [] }
}

function sameChapterForeshadowingGraph(): NarrativeAtlasGraph {
  const graph = longChapterGraph(1)
  const foreshadowing = [1, 2].map((index) => ({
    id: `foreshadowing:chapter-1-${index}`,
    type: 'foreshadowing' as const,
    label: `第一章伏笔${index}`,
    chapterIndex: 1,
  }))

  return { nodes: [...graph.nodes, ...foreshadowing], edges: graph.edges, warnings: [] }
}

function transformPoint(transform: string) {
  const match = /translate\(([-\d.]+),\s*([-\d.]+)\)/.exec(transform)
  if (!match) throw new Error(`Unexpected transform: ${transform}`)
  return { x: Number(match[1]), y: Number(match[2]) }
}

function eventBox(point: { x: number; y: number }) {
  return {
    left: point.x - 56,
    right: point.x + 56,
    top: point.y - 20,
    bottom: point.y + 20,
  }
}

function boxesOverlap(left: ReturnType<typeof eventBox>, right: ReturnType<typeof eventBox>) {
  return left.left < right.right
    && left.right > right.left
    && left.top < right.bottom
    && left.bottom > right.top
}

function cubicEndpoints(path: string) {
  const match = /^M\s+([-\d.]+)\s+([-\d.]+)\s+C\s+[-\d.]+\s+[-\d.]+,\s+[-\d.]+\s+[-\d.]+,\s+([-\d.]+)\s+([-\d.]+)$/.exec(path)
  if (!match) throw new Error(`Unexpected cubic path: ${path}`)
  return {
    start: { x: Number(match[1]), y: Number(match[2]) },
    end: { x: Number(match[3]), y: Number(match[4]) },
  }
}

describe('NarrativeAtlasCanvas', () => {
  it('zooms with mouse wheel and supports space-drag panning', async () => {
    const wrapper = mount(NarrativeAtlasCanvas, {
      props: {
        graph: longChapterGraph(20),
        layers: { trunk: true, branches: true, foreshadowing: true, events: true },
        selected: null,
      },
      attachTo: document.body,
    })
    const canvas = wrapper.get('[data-testid="narrative-atlas-canvas"]')
    const canvasElement = canvas.element as HTMLElement

    canvasElement.dispatchEvent(new WheelEvent('wheel', { deltaY: -120, clientX: 420, clientY: 220 }))
    await wrapper.vm.$nextTick()
    expect(canvas.attributes('data-atlas-zoom')).toBe('110')

    canvasElement.scrollLeft = 80
    canvasElement.scrollTop = 80
    window.dispatchEvent(new KeyboardEvent('keydown', { code: 'Space' }))
    canvasElement.dispatchEvent(new MouseEvent('mousedown', { button: 0, clientX: 320, clientY: 220 }))
    await wrapper.vm.$nextTick()
    expect(canvas.attributes('data-atlas-panning')).toBe('true')

    window.dispatchEvent(new MouseEvent('mousemove', { clientX: 280, clientY: 180 }))
    expect(canvasElement.scrollLeft).toBeGreaterThan(80)
    expect(canvasElement.scrollTop).toBeGreaterThan(80)

    window.dispatchEvent(new MouseEvent('mouseup'))
    window.dispatchEvent(new KeyboardEvent('keyup', { code: 'Space' }))
    await wrapper.vm.$nextTick()
    expect(canvas.attributes('data-atlas-panning')).toBe('false')

    wrapper.unmount()
  })

  it('renders wide transparent edge hitboxes for reliable selection', async () => {
    const wrapper = mount(NarrativeAtlasCanvas, {
      props: {
        graph: longChapterGraph(2),
        layers: { trunk: true, branches: true, foreshadowing: true, events: true },
        selected: null,
      },
    })
    const hitbox = wrapper.get('[data-atlas-edge-hitbox-id="trunk:chapter:1->chapter:2"]')
    const edge = wrapper.get('[data-atlas-edge-id="trunk:chapter:1->chapter:2"]')

    await edge.trigger('click')

    expect(hitbox.classes()).toContain('narrative-atlas-canvas__edge-hitbox')
    expect(edge.classes()).toContain('narrative-atlas-canvas__edge-handle')
    expect(wrapper.find('.narrative-atlas-canvas__edge-line').exists()).toBe(true)
    expect(wrapper.emitted('select')).toEqual([[{ kind: 'edge', id: 'trunk:chapter:1->chapter:2' }]])
  })

  it('uses vertical chapter spine and dynamic height for long stories', () => {
    const wrapper = mount(NarrativeAtlasCanvas, {
      props: {
        graph: longChapterGraph(20),
        layers: { trunk: true, branches: true, foreshadowing: true, events: true },
        selected: null,
      },
    })

    const svg = wrapper.get('svg')
    const height = Number(svg.attributes('height'))
    const viewBox = svg.attributes('viewBox') ?? svg.attributes('viewbox') ?? ''
    const viewBoxParts = viewBox.split(' ')
    const chapter1 = transformPoint(wrapper.get('[data-atlas-node-id="chapter:1"]').attributes('transform') ?? '')
    const chapter10 = transformPoint(wrapper.get('[data-atlas-node-id="chapter:10"]').attributes('transform') ?? '')
    const chapter20 = transformPoint(wrapper.get('[data-atlas-node-id="chapter:20"]').attributes('transform') ?? '')

    expect(height).toBeGreaterThan(560)
    expect(viewBoxParts[viewBoxParts.length - 1]).toBe(String(height))
    expect(chapter1.x).toBe(chapter10.x)
    expect(chapter10.x).toBe(chapter20.x)
    expect(chapter1.y).toBeLessThan(chapter10.y)
    expect(chapter10.y).toBeLessThan(chapter20.y)
  })

  it('keeps same-chapter event nodes from overlapping', () => {
    const wrapper = mount(NarrativeAtlasCanvas, {
      props: {
        graph: sameChapterEventGraph(4, 20),
        layers: { trunk: true, branches: true, foreshadowing: true, events: true },
        selected: null,
      },
    })
    const height = Number(wrapper.get('svg').attributes('height'))
    const eventYs = [1, 2, 3, 4]
      .map((index) => transformPoint(
        wrapper.get(`[data-atlas-node-id="event:chapter-20-${index}"]`).attributes('transform') ?? '',
      ).y)
      .sort((left, right) => left - right)

    for (let index = 1; index < eventYs.length; index += 1) {
      expect(eventYs[index] - eventYs[index - 1]).toBeGreaterThanOrEqual(52)
    }
    expect(Math.max(...eventYs)).toBeLessThanOrEqual(height - 48)
  })

  it('keeps adjacent chapter event stacks from overlapping', () => {
    const wrapper = mount(NarrativeAtlasCanvas, {
      props: {
        graph: adjacentChapterEventGraph(),
        layers: { trunk: true, branches: true, foreshadowing: true, events: true },
        selected: null,
      },
    })
    const boxes = [
      'event:chapter-1-1',
      'event:chapter-1-2',
      'event:chapter-1-3',
      'event:chapter-2-1',
    ].map((nodeId) => eventBox(transformPoint(
      wrapper.get(`[data-atlas-node-id="${nodeId}"]`).attributes('transform') ?? '',
    )))

    for (let leftIndex = 0; leftIndex < boxes.length; leftIndex += 1) {
      for (let rightIndex = leftIndex + 1; rightIndex < boxes.length; rightIndex += 1) {
        expect(boxesOverlap(boxes[leftIndex], boxes[rightIndex])).toBe(false)
      }
    }
  })

  it('keeps milestones on their own lane instead of spilling into the event lane', () => {
    const wrapper = mount(NarrativeAtlasCanvas, {
      props: {
        graph: milestoneAndEventTrackGraph(),
        layers: { trunk: true, branches: true, foreshadowing: true, events: true },
        selected: null,
      },
    })
    const milestoneXs = [1, 2, 3].map((index) => transformPoint(
      wrapper.get(`[data-atlas-node-id="milestone:main:${index}"]`).attributes('transform') ?? '',
    ).x)
    const eventX = transformPoint(wrapper.get('[data-atlas-node-id="event:chapter-1"]').attributes('transform') ?? '').x

    expect(wrapper.text()).toContain('里程碑')
    expect(Math.max(...milestoneXs)).toBeLessThan(eventX - 160)
  })

  it('keeps plotline and milestone nodes separated and routes branch edges outside node bodies', () => {
    const wrapper = mount(NarrativeAtlasCanvas, {
      props: {
        graph: milestoneAndEventTrackGraph(),
        layers: { trunk: true, branches: true, foreshadowing: true, events: true },
        selected: null,
      },
    })
    const plotlinePoint = transformPoint(wrapper.get('[data-atlas-node-id="plotline:main"]').attributes('transform') ?? '')
    const milestonePoint = transformPoint(wrapper.get('[data-atlas-node-id="milestone:main:1"]').attributes('transform') ?? '')
    const plotlineBox = eventBox(plotlinePoint)
    const milestoneBox = eventBox(milestonePoint)
    const edgePath = wrapper
      .get('[data-atlas-edge-hitbox-id="branch:plotline:main->milestone:main:1"]')
      .attributes('d') ?? ''
    const endpoints = cubicEndpoints(edgePath)

    expect(milestoneBox.left - plotlineBox.right).toBeGreaterThanOrEqual(72)
    expect(endpoints.start.x).toBeGreaterThan(plotlinePoint.x)
    expect(endpoints.end.x).toBeLessThan(milestonePoint.x)
  })

  it('keeps same-chapter foreshadowing nodes visually separated', () => {
    const wrapper = mount(NarrativeAtlasCanvas, {
      props: {
        graph: sameChapterForeshadowingGraph(),
        layers: { trunk: true, branches: true, foreshadowing: true, events: true },
        selected: null,
      },
    })
    const boxes = [1, 2].map((index) => eventBox(transformPoint(
      wrapper.get(`[data-atlas-node-id="foreshadowing:chapter-1-${index}"]`).attributes('transform') ?? '',
    )))

    const horizontalGap = boxes[0].left > boxes[1].left
      ? boxes[0].left - boxes[1].right
      : boxes[1].left - boxes[0].right

    expect(boxesOverlap(boxes[0], boxes[1])).toBe(false)
    expect(horizontalGap).toBeGreaterThanOrEqual(24)
  })

  it('uses compact layer-specific arrow markers for edge lines', () => {
    const wrapper = mount(NarrativeAtlasCanvas, {
      props: {
        graph: milestoneAndEventTrackGraph(),
        layers: { trunk: true, branches: true, foreshadowing: true, events: true },
        selected: null,
      },
    })

    const branchLine = wrapper.get('[data-atlas-edge-line-id="branch:plotline:main->milestone:main:1"]')
    const branchMarker = wrapper.get('#atlas-arrow-branches')

    expect(branchLine.attributes('marker-end')).toBe('url(#atlas-arrow-branches)')
    expect(branchMarker.attributes('markerUnits')).toBe('userSpaceOnUse')
    expect(Number(branchMarker.attributes('markerWidth'))).toBeLessThanOrEqual(6)
  })
})
