import type { useAthenaStore } from '../stores/athena'
import type { useWorldModelStore } from '../stores/worldModel'
import type { AthenaRouteState } from './athenaNavigation'

type AthenaStore = ReturnType<typeof useAthenaStore>
type WorldModelStore = ReturnType<typeof useWorldModelStore>
const CHAPTER_PLAN_WINDOW_LIMIT = 50
const GRAPH_CHAPTER_WINDOW_LIMIT = 80
const GRAPH_RELATION_WINDOW_LIMIT = 500
const STORYLINE_PLOTLINE_WINDOW_LIMIT = 20
const STORYLINE_MILESTONE_WINDOW_LIMIT = 80
const FORESHADOWING_PLAN_WINDOW_LIMIT = 100

interface AthenaSectionLoaderOptions {
  getProjectId: () => string
  athena: AthenaStore
  worldModel: WorldModelStore
}

export function createAthenaSectionLoader(options: AthenaSectionLoaderOptions) {
  function chapterPlanWindowQuery(offset = 0) {
    return {
      mode: 'window' as const,
      chapter_offset: offset,
      chapter_limit: CHAPTER_PLAN_WINDOW_LIMIT,
      plotline_limit: 1,
      foreshadowing_limit: 1,
    }
  }

  function graphPlanWindowQuery(offset = 0) {
    return {
      mode: 'window' as const,
      chapter_offset: offset,
      chapter_limit: GRAPH_CHAPTER_WINDOW_LIMIT,
      plotline_limit: STORYLINE_PLOTLINE_WINDOW_LIMIT,
      milestone_limit: GRAPH_RELATION_WINDOW_LIMIT,
      foreshadowing_limit: GRAPH_RELATION_WINDOW_LIMIT,
    }
  }

  function foreshadowingPlanWindowQuery(offset = 0) {
    return {
      mode: 'window' as const,
      chapter_limit: 1,
      plotline_limit: 1,
      foreshadowing_offset: offset,
      foreshadowing_limit: FORESHADOWING_PLAN_WINDOW_LIMIT,
    }
  }

  function storylinePlanWindowQuery(milestoneOffset = 0) {
    return {
      mode: 'window' as const,
      chapter_limit: 1,
      plotline_limit: STORYLINE_PLOTLINE_WINDOW_LIMIT,
      milestone_offset: milestoneOffset,
      milestone_limit: STORYLINE_MILESTONE_WINDOW_LIMIT,
      foreshadowing_limit: 1,
    }
  }

  function timelineHasEvents() {
    return Array.isArray(options.athena.timeline?.events) && options.athena.timeline.events.length > 0
  }

  async function loadRouteData(routeState: AthenaRouteState) {
    const id = options.getProjectId()
    if (routeState.section === 'overview') {
      await options.worldModel.loadDashboard(id)
      await options.athena.loadLongformMaintenanceDiagnostics(id).catch(() => undefined)
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
      if (
        (routeState.view === 'facts' || routeState.view === 'disclosure')
        && !options.worldModel.factClaimsLoaded
      ) {
        await options.worldModel.loadFactClaims(id)
      }
    }
    if (routeState.section === 'narrative' && routeState.view === 'timeline') {
      if (!options.athena.timeline) await options.athena.loadTimeline(id)
      if (!timelineHasEvents() && !options.athena.evolutionPlan) await options.athena.loadEvolutionPlan(id)
    }
    if (routeState.section === 'narrative' && routeState.view === 'graph') {
      if (!options.athena.timeline) await options.athena.loadTimeline(id)
      await options.athena.loadEvolutionPlan(id, graphPlanWindowQuery())
    }
    if (routeState.section === 'narrative' && routeState.view === 'chapters') {
      await options.athena.loadEvolutionPlan(id, chapterPlanWindowQuery())
    }
    if (routeState.section === 'narrative' && routeState.view === 'foreshadowing') {
      await options.athena.loadEvolutionPlan(id, foreshadowingPlanWindowQuery())
    }
    if (routeState.section === 'narrative' && routeState.view === 'storyline') {
      await options.athena.loadEvolutionPlan(id, storylinePlanWindowQuery())
    }
    if (
      routeState.section === 'review'
      && (routeState.view === 'proposals' || routeState.view === 'impact' || routeState.view === 'history')
    ) {
      if (
        !options.worldModel.proposalBundlesLoaded
        || (
          (routeState.view === 'impact' || routeState.view === 'history')
          && options.worldModel.proposalBundles.length > 0
          && !options.worldModel.selectedBundleDetail
        )
      ) {
        await options.worldModel.loadSetupPanelData(id)
      }
    }
    if (routeState.section === 'review' && routeState.view === 'conflicts') {
      await options.athena.loadConsistencyIssues(id)
    }
  }

  return { loadRouteData }
}
