import type { useAthenaStore } from '../stores/athena'
import type { useWorldModelStore } from '../stores/worldModel'
import type { AthenaRouteState } from './athenaNavigation'

type AthenaStore = ReturnType<typeof useAthenaStore>
type WorldModelStore = ReturnType<typeof useWorldModelStore>

interface AthenaSectionLoaderOptions {
  getProjectId: () => string
  athena: AthenaStore
  worldModel: WorldModelStore
}

export function createAthenaSectionLoader(options: AthenaSectionLoaderOptions) {
  async function loadRouteData(routeState: AthenaRouteState) {
    const id = options.getProjectId()
    if (routeState.section === 'overview') {
      await options.worldModel.loadDashboard(id)
      if (!options.worldModel.dashboard?.project_profile && options.athena.ontology?.setup_summary) {
        await options.athena.loadSetupImportPreview(id).catch(() => undefined)
      }
      if (routeState.panel === 'optimization') {
        await options.athena.loadOptimization(id)
      }
    }
    if (routeState.section === 'catalog') {
      if (!options.athena.ontology) await options.athena.loadOntology(id)
      if (!options.worldModel.projection) await options.worldModel.loadOverview(id)
      if (routeState.tool === 'retrieval') await options.athena.loadRetrievalDiagnostics(id)
    }
    if (routeState.section === 'truth') {
      if (!options.worldModel.projection) await options.worldModel.loadOverview(id)
    }
    if (routeState.section === 'narrative' && routeState.view === 'timeline') {
      if (!options.athena.timeline) await options.athena.loadTimeline(id)
    }
    if (
      routeState.section === 'narrative'
      && (routeState.view === 'storyline' || routeState.view === 'chapters' || routeState.view === 'foreshadowing')
    ) {
      if (!options.athena.evolutionPlan) await options.athena.loadEvolutionPlan(id)
    }
    if (
      routeState.section === 'review'
      && (routeState.view === 'proposals' || routeState.view === 'impact' || routeState.view === 'history')
    ) {
      if (!options.worldModel.loaded) {
        await options.worldModel.loadSetupPanelData(id)
      }
    }
    if (routeState.section === 'review' && routeState.view === 'conflicts') {
      await options.athena.loadConsistencyIssues(id)
    }
  }

  return { loadRouteData }
}
