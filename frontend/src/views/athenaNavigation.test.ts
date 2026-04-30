import { describe, expect, it } from 'vitest'
import {
  buildAthenaRoute,
  resolveAthenaRoute,
  type AthenaRouteState,
} from './athenaNavigation'

describe('athenaNavigation', () => {
  it('resolves the default Athena route to overview', () => {
    expect(resolveAthenaRoute(undefined, {})).toEqual({
      section: 'overview',
      view: 'dashboard',
      nodeType: 'all',
      tool: null,
      panel: null,
      isLegacy: false,
    })
  })

  it('maps legacy entity routes to catalog node filters', () => {
    expect(resolveAthenaRoute('characters', {})).toMatchObject({
      section: 'catalog',
      view: 'nodes',
      nodeType: 'characters',
      isLegacy: true,
    })
    expect(resolveAthenaRoute('locations', {})).toMatchObject({
      section: 'catalog',
      view: 'nodes',
      nodeType: 'locations',
      isLegacy: true,
    })
  })

  it('maps legacy truth and review routes to new sections', () => {
    expect(resolveAthenaRoute('projection', {})).toMatchObject({
      section: 'truth',
      view: 'projection',
      isLegacy: true,
    })
    expect(resolveAthenaRoute('consistency', {})).toMatchObject({
      section: 'review',
      view: 'conflicts',
      isLegacy: true,
    })
  })

  it('uses query view and filters for canonical routes', () => {
    expect(resolveAthenaRoute('catalog', { view: 'rules' })).toMatchObject({
      section: 'catalog',
      view: 'rules',
      nodeType: 'all',
      isLegacy: false,
    })
    expect(resolveAthenaRoute('catalog', { view: 'nodes', type: 'factions' })).toMatchObject({
      section: 'catalog',
      view: 'nodes',
      nodeType: 'factions',
      isLegacy: false,
    })
  })

  it('normalizes invalid canonical route query values', () => {
    expect(resolveAthenaRoute('truth', { view: 'rules', type: 'bad', tool: ['inspect'], panel: '' })).toEqual({
      section: 'truth',
      view: 'projection',
      nodeType: 'all',
      tool: 'inspect',
      panel: null,
      isLegacy: false,
    })
  })

  it('builds canonical route locations', () => {
    const state: AthenaRouteState = {
      section: 'catalog',
      view: 'nodes',
      nodeType: 'characters',
      tool: null,
      panel: null,
      isLegacy: false,
    }

    expect(buildAthenaRoute('project-1', state)).toEqual({
      path: '/projects/project-1/athena/catalog',
      query: { view: 'nodes', type: 'characters' },
    })
  })
})
