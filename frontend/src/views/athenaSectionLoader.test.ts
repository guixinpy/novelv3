import { describe, expect, it, vi } from 'vitest'
import { createAthenaSectionLoader } from './athenaSectionLoader'
import type { AthenaRouteState } from './athenaNavigation'

function createLoaderMocks(setupSummary: unknown) {
  const athena = {
    ontology: {
      entities: {},
      relations: [],
      rules: [],
      setup_summary: setupSummary,
      profile_version: null,
    },
    loadSetupImportPreview: vi.fn(async () => undefined),
    loadOntology: vi.fn(async () => {
      athena.ontology = {
        entities: {},
        relations: [],
        rules: [],
        setup_summary: null,
        profile_version: 1,
      } as any
    }),
    loadRetrievalDiagnostics: vi.fn(async () => undefined),
    loadTimeline: vi.fn(async () => undefined),
    loadEvolutionPlan: vi.fn(async () => undefined),
    loadConsistencyIssues: vi.fn(async () => undefined),
    loadOptimization: vi.fn(async () => undefined),
    loadLongformMaintenanceDiagnostics: vi.fn(async () => undefined),
    timeline: null as any,
    evolutionPlan: null as any,
  }
  const worldModel = {
    dashboard: null as any,
    projection: null as any,
    factClaimsLoaded: false,
    proposalBundlesLoaded: false,
    proposalBundles: [] as any[],
    selectedBundleDetail: null as any,
    loaded: false,
    loadDashboard: vi.fn(async () => {
      worldModel.dashboard = {
        project_profile: null,
        metrics: {
          entity_count: 0,
          fact_count: 0,
          presence_count: 0,
          event_count: 0,
          pending_bundle_count: 0,
          pending_item_count: 0,
        },
        next_action: { action: 'import_setup', label: '导入 Setup' },
      }
    }),
    loadOverview: vi.fn(async () => {
      worldModel.projection = { entities: {}, relations: {}, presence: {}, occurred_events: {}, event_links: {}, facts: {} }
    }),
    loadFactClaims: vi.fn(async () => {
      worldModel.factClaimsLoaded = true
    }),
    loadSetupPanelData: vi.fn(async () => {
      worldModel.loaded = true
      worldModel.proposalBundlesLoaded = true
    }),
  }
  return {
    athena,
    worldModel,
    loader: createAthenaSectionLoader({
      getProjectId: () => 'project-1',
      athena: athena as any,
      worldModel: worldModel as any,
    }),
  }
}

function routeState(overrides: Partial<AthenaRouteState>): AthenaRouteState {
  return {
    section: 'overview',
    view: 'dashboard',
    nodeType: 'all',
    tool: null,
    panel: null,
    isLegacy: false,
    ...overrides,
  }
}

describe('createAthenaSectionLoader', () => {
  it('does not request setup import preview when setup draft is missing', async () => {
    const { athena, loader } = createLoaderMocks(null)

    await loader.loadRouteData(routeState({ section: 'overview', view: 'dashboard' }))

    expect(athena.loadSetupImportPreview).not.toHaveBeenCalled()
  })

  it('requests setup import preview when setup draft exists and profile is missing', async () => {
    const { athena, loader } = createLoaderMocks({ characters: [] })

    await loader.loadRouteData(routeState({ section: 'overview', view: 'dashboard' }))

    expect(athena.loadSetupImportPreview).toHaveBeenCalledWith('project-1')
  })

  it('loads longform maintenance diagnostics with the overview dashboard', async () => {
    const { athena, loader } = createLoaderMocks(null)

    await loader.loadRouteData(routeState({ section: 'overview', view: 'dashboard' }))

    expect(athena.loadLongformMaintenanceDiagnostics).toHaveBeenCalledWith('project-1')
  })

  it('loads catalog ontology and projection only when they are missing', async () => {
    const { athena, worldModel, loader } = createLoaderMocks(null)
    athena.ontology = null as any

    await loader.loadRouteData(routeState({ section: 'catalog', view: 'nodes' }))
    await loader.loadRouteData(routeState({ section: 'catalog', view: 'graph' }))

    expect(athena.loadOntology).toHaveBeenCalledTimes(1)
    expect(athena.loadOntology).toHaveBeenCalledWith('project-1')
    expect(worldModel.loadOverview).toHaveBeenCalledTimes(1)
    expect(worldModel.loadOverview).toHaveBeenCalledWith('project-1')
  })

  it('loads retrieval diagnostics for the catalog retrieval tool', async () => {
    const { athena, loader } = createLoaderMocks(null)

    await loader.loadRouteData(routeState({ section: 'catalog', view: 'nodes', tool: 'retrieval' }))

    expect(athena.loadRetrievalDiagnostics).toHaveBeenCalledWith('project-1')
  })

  it('loads truth projection data without loading fact claims for projection and knowledge views', async () => {
    const { worldModel, loader } = createLoaderMocks(null)

    await loader.loadRouteData(routeState({ section: 'truth', view: 'projection' }))
    await loader.loadRouteData(routeState({ section: 'truth', view: 'knowledge' }))

    expect(worldModel.loadOverview).toHaveBeenCalledTimes(1)
    expect(worldModel.loadOverview).toHaveBeenCalledWith('project-1')
    expect(worldModel.loadFactClaims).not.toHaveBeenCalled()
  })

  it('loads fact claims for fact and disclosure truth views', async () => {
    const { worldModel, loader } = createLoaderMocks(null)
    worldModel.projection = { entities: {}, relations: {}, presence: {}, occurred_events: {}, event_links: {}, facts: {} }

    await loader.loadRouteData(routeState({ section: 'truth', view: 'facts' }))
    await loader.loadRouteData(routeState({ section: 'truth', view: 'disclosure' }))

    expect(worldModel.loadOverview).not.toHaveBeenCalled()
    expect(worldModel.loadFactClaims).toHaveBeenCalledTimes(1)
  })

  it('loads narrative data by active view family', async () => {
    const { athena, loader } = createLoaderMocks(null)

    await loader.loadRouteData(routeState({ section: 'narrative', view: 'timeline' }))
    await loader.loadRouteData(routeState({ section: 'narrative', view: 'storyline' }))

    expect(athena.loadTimeline).toHaveBeenCalledWith('project-1')
    expect(athena.loadEvolutionPlan).toHaveBeenCalledWith('project-1')
  })

  it('does not load full evolution plan for timeline when timeline events are available', async () => {
    const { athena, loader } = createLoaderMocks(null)
    athena.timeline = null as any
    athena.loadTimeline = vi.fn(async () => {
      athena.timeline = {
        events: [{ id: 'event-1', chapter_index: 1, description: '已存在时间线事件' }],
        anchors: [],
      } as any
    })

    await loader.loadRouteData(routeState({ section: 'narrative', view: 'timeline' }))

    expect(athena.loadTimeline).toHaveBeenCalledWith('project-1')
    expect(athena.loadEvolutionPlan).not.toHaveBeenCalled()
  })

  it('loads timeline and evolution plan for the narrative graph view', async () => {
    const { athena, loader } = createLoaderMocks(null)

    await loader.loadRouteData(routeState({ section: 'narrative', view: 'graph' }))

    expect(athena.loadTimeline).toHaveBeenCalledWith('project-1')
    expect(athena.loadEvolutionPlan).toHaveBeenCalledWith('project-1')
  })

  it('loads a bounded chapter plan window for the narrative chapters view', async () => {
    const { athena, loader } = createLoaderMocks(null)

    await loader.loadRouteData(routeState({ section: 'narrative', view: 'chapters' }))

    expect(athena.loadEvolutionPlan).toHaveBeenCalledWith('project-1', {
      mode: 'window',
      chapter_offset: 0,
      chapter_limit: 50,
      plotline_limit: 1,
      foreshadowing_limit: 1,
    })
  })

  it('reloads the full evolution plan for graph view when a windowed plan is already present', async () => {
    const { athena, loader } = createLoaderMocks(null)
    athena.evolutionPlan = {
      outline: {
        chapters: [{ chapter_index: 1 }],
        chapters_total: 1000,
        chapters_offset: 0,
        chapters_limit: 50,
      },
      storyline: null,
    } as any

    await loader.loadRouteData(routeState({ section: 'narrative', view: 'graph' }))

    expect(athena.loadEvolutionPlan).toHaveBeenCalledWith('project-1')
  })

  it('loads review data by active view family', async () => {
    const { athena, worldModel, loader } = createLoaderMocks(null)

    await loader.loadRouteData(routeState({ section: 'review', view: 'proposals' }))
    await loader.loadRouteData(routeState({ section: 'review', view: 'conflicts' }))

    expect(worldModel.loadSetupPanelData).toHaveBeenCalledWith('project-1')
    expect(athena.loadConsistencyIssues).toHaveBeenCalledWith('project-1')
  })

  it('preserves legacy optimization panel loading on overview routes', async () => {
    const { athena, loader } = createLoaderMocks(null)

    await loader.loadRouteData(routeState({ section: 'overview', view: 'dashboard', panel: 'optimization' }))

    expect(athena.loadOptimization).toHaveBeenCalledWith('project-1')
  })

  it('does not reload proposal workbench when review data is already loaded', async () => {
    const athena = {}
    const worldModel = {
      loaded: true,
      proposalBundlesLoaded: true,
      proposalBundles: [],
      factClaimsLoaded: true,
      loadSetupPanelData: vi.fn(async () => undefined),
    }
    const loader = createAthenaSectionLoader({
      getProjectId: () => 'project-1',
      athena: athena as any,
      worldModel: worldModel as any,
    })

    await loader.loadRouteData(routeState({ section: 'review', view: 'proposals' }))

    expect(worldModel.loadSetupPanelData).not.toHaveBeenCalled()
  })

  it('reloads review insight views when bundle list exists but selected detail is missing', async () => {
    const worldModel = {
      loaded: true,
      proposalBundlesLoaded: true,
      proposalBundles: [{ id: 'bundle-1' }],
      selectedBundleDetail: null,
      factClaimsLoaded: true,
      loadSetupPanelData: vi.fn(async () => undefined),
    }
    const loader = createAthenaSectionLoader({
      getProjectId: () => 'project-1',
      athena: {} as any,
      worldModel: worldModel as any,
    })

    await loader.loadRouteData(routeState({ section: 'review', view: 'impact' }))

    expect(worldModel.loadSetupPanelData).toHaveBeenCalledWith('project-1')
  })

  it('loads proposal data for review views even when overview was already loaded', async () => {
    const worldModel = {
      loaded: true,
      proposalBundlesLoaded: false,
      loadSetupPanelData: vi.fn(async () => undefined),
    }
    const loader = createAthenaSectionLoader({
      getProjectId: () => 'project-1',
      athena: {} as any,
      worldModel: worldModel as any,
    })

    await loader.loadRouteData(routeState({ section: 'review', view: 'impact' }))

    expect(worldModel.loadSetupPanelData).toHaveBeenCalledWith('project-1')
  })
})
