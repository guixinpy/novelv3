import { describe, expect, it } from 'vitest'
import {
  buildAthenaRoute,
  isCanonicalAthenaRoute,
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
      nodeType: 'all',
      isLegacy: true,
    })
    expect(resolveAthenaRoute('consistency', {})).toMatchObject({
      section: 'review',
      view: 'conflicts',
      nodeType: 'all',
      isLegacy: true,
    })
  })

  it('scopes legacy node filters to catalog nodes', () => {
    expect(resolveAthenaRoute('relations', {})).toMatchObject({
      section: 'catalog',
      view: 'graph',
      nodeType: 'all',
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

  it('does not leak node type filters outside catalog nodes', () => {
    expect(resolveAthenaRoute('truth', { view: 'projection', type: 'characters' })).toMatchObject({
      section: 'truth',
      view: 'projection',
      nodeType: 'all',
      isLegacy: false,
    })
    expect(resolveAthenaRoute('catalog', { view: 'rules', type: 'characters' })).toMatchObject({
      section: 'catalog',
      view: 'rules',
      nodeType: 'all',
      isLegacy: false,
    })
  })

  it('normalizes invalid canonical route query values', () => {
    expect(resolveAthenaRoute('truth', { view: 'rules', type: 'bad', tool: ['inspect'], panel: '' })).toEqual({
      section: 'truth',
      view: 'projection',
      nodeType: 'all',
      tool: null,
      panel: null,
      isLegacy: false,
    })
  })

  it('scopes tool and panel query values to their real surfaces', () => {
    expect(resolveAthenaRoute('catalog', { view: 'nodes', tool: 'retrieval', panel: 'optimization' })).toMatchObject({
      section: 'catalog',
      view: 'nodes',
      tool: 'retrieval',
      panel: null,
    })
    expect(resolveAthenaRoute('overview', { tool: 'retrieval', panel: 'optimization' })).toMatchObject({
      section: 'overview',
      view: 'dashboard',
      tool: null,
      panel: 'optimization',
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

  it('canonicalizes route state before building locations', () => {
    const state: AthenaRouteState = {
      section: 'truth',
      view: 'rules',
      nodeType: 'characters',
      tool: null,
      panel: null,
      isLegacy: false,
    }

    expect(buildAthenaRoute('project-1', state)).toEqual({
      path: '/projects/project-1/athena/truth',
      query: { view: 'projection' },
    })
  })

  it('does not include view for overview routes', () => {
    const state: AthenaRouteState = {
      section: 'overview',
      view: 'rules',
      nodeType: 'characters',
      tool: null,
      panel: null,
      isLegacy: false,
    }

    expect(buildAthenaRoute('project-1', state)).toEqual({
      path: '/projects/project-1/athena/overview',
      query: {},
    })
  })

  it('preserves scoped tool and panel while building routes', () => {
    expect(buildAthenaRoute('project-1', {
      section: 'catalog',
      view: 'nodes',
      nodeType: 'all',
      tool: 'retrieval',
      panel: null,
    })).toEqual({
      path: '/projects/project-1/athena/catalog',
      query: { view: 'nodes', tool: 'retrieval' },
    })
    expect(buildAthenaRoute('project-1', {
      section: 'overview',
      view: 'dashboard',
      nodeType: 'all',
      tool: null,
      panel: 'optimization',
    })).toEqual({
      path: '/projects/project-1/athena/overview',
      query: { panel: 'optimization' },
    })
  })

  it('drops valid tool and panel values outside their scoped surfaces', () => {
    expect(buildAthenaRoute('project-1', {
      section: 'review',
      view: 'history',
      nodeType: 'characters',
      tool: 'retrieval',
      panel: 'optimization',
    })).toEqual({
      path: '/projects/project-1/athena/review',
      query: { view: 'history' },
    })
  })

  it('detects canonical route locations', () => {
    const state = resolveAthenaRoute('catalog', { view: 'nodes', type: 'locations' })

    expect(isCanonicalAthenaRoute(
      'project-1',
      state,
      '/projects/project-1/athena/catalog',
      { view: 'nodes', type: 'locations' },
    )).toBe(true)
  })

  it('detects dirty canonicalized route locations', () => {
    const defaultState = resolveAthenaRoute(undefined, {})
    const invalidState = resolveAthenaRoute('bad', { view: 'rules', type: 'characters' })

    expect(isCanonicalAthenaRoute(
      'project-1',
      defaultState,
      '/projects/project-1/athena',
      {},
    )).toBe(false)
    expect(isCanonicalAthenaRoute(
      'project-1',
      invalidState,
      '/projects/project-1/athena/bad',
      { view: 'rules', type: 'characters' },
    )).toBe(false)
  })
})
