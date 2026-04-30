import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useUiStore } from './ui'

describe('ui store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('remembers Athena state per primary section', () => {
    const ui = useUiStore()

    ui.setAthenaState('project-1', {
      section: 'catalog',
      view: 'nodes',
      nodeType: 'locations',
      tool: null,
      panel: null,
    })
    ui.setAthenaState('project-1', {
      section: 'truth',
      view: 'knowledge',
      nodeType: 'all',
      tool: null,
      panel: null,
    })

    expect(ui.activeAthenaState).toMatchObject({ section: 'truth', view: 'knowledge' })
    expect(ui.getAthenaSectionState('project-1', 'catalog')).toEqual({
      section: 'catalog',
      view: 'nodes',
      nodeType: 'locations',
      tool: null,
      panel: null,
    })
  })

  it('returns default Athena state for untouched sections', () => {
    const ui = useUiStore()

    expect(ui.getAthenaSectionState('project-1', 'review')).toEqual({
      section: 'review',
      view: 'proposals',
      nodeType: 'all',
      tool: null,
      panel: null,
    })
  })

  it('isolates Athena navigation state per project', () => {
    const ui = useUiStore()

    ui.setAthenaState('project-1', {
      section: 'catalog',
      view: 'nodes',
      nodeType: 'locations',
      tool: null,
      panel: null,
    })
    ui.setAthenaState('project-2', {
      section: 'truth',
      view: 'projection',
      nodeType: 'all',
      tool: null,
      panel: null,
    })

    expect(ui.getActiveAthenaState('project-1')).toEqual({
      section: 'catalog',
      view: 'nodes',
      nodeType: 'locations',
      tool: null,
      panel: null,
    })
    expect(ui.getActiveAthenaState('project-2')).toEqual({
      section: 'truth',
      view: 'projection',
      nodeType: 'all',
      tool: null,
      panel: null,
    })
  })
})
