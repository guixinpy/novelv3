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
})
