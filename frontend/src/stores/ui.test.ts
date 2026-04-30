import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useUiStore } from './ui'

describe('ui store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('remembers Athena state per primary section', () => {
    const ui = useUiStore()

    ui.setAthenaState({
      section: 'catalog',
      view: 'nodes',
      nodeType: 'locations',
      tool: null,
      panel: null,
    })
    ui.setAthenaState({
      section: 'truth',
      view: 'knowledge',
      nodeType: 'all',
      tool: null,
      panel: null,
    })

    expect(ui.activeAthenaState).toMatchObject({ section: 'truth', view: 'knowledge' })
    expect(ui.getAthenaSectionState('catalog')).toEqual({
      section: 'catalog',
      view: 'nodes',
      nodeType: 'locations',
      tool: null,
      panel: null,
    })
  })

  it('returns default Athena state for untouched sections', () => {
    const ui = useUiStore()

    expect(ui.getAthenaSectionState('review')).toEqual({
      section: 'review',
      view: 'proposals',
      nodeType: 'all',
      tool: null,
      panel: null,
    })
  })
})
