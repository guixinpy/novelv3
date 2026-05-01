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

function transformPoint(transform: string) {
  const match = /translate\(([-\d.]+),\s*([-\d.]+)\)/.exec(transform)
  if (!match) throw new Error(`Unexpected transform: ${transform}`)
  return { x: Number(match[1]), y: Number(match[2]) }
}

describe('NarrativeAtlasCanvas', () => {
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
})
