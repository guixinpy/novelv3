import type { AthenaSection } from '../stores/ui'
import type { useAthenaStore } from '../stores/athena'
import type { useWorldModelStore } from '../stores/worldModel'

type AthenaStore = ReturnType<typeof useAthenaStore>
type WorldModelStore = ReturnType<typeof useWorldModelStore>

interface AthenaSectionLoaderOptions {
  getProjectId: () => string
  athena: AthenaStore
  worldModel: WorldModelStore
  entitySections: Set<string>
}

export function createAthenaSectionLoader(options: AthenaSectionLoaderOptions) {
  async function loadSectionData(section: AthenaSection) {
    const id = options.getProjectId()
    if (section === 'overview') {
      await options.worldModel.loadDashboard(id)
      if (!options.worldModel.dashboard?.project_profile && options.athena.ontology?.setup_summary) {
        await options.athena.loadSetupImportPreview(id).catch(() => undefined)
      }
    }
    if (options.entitySections.has(section) || section === 'relations' || section === 'rules') {
      if (!options.athena.ontology) await options.athena.loadOntology(id)
    }
    if (section === 'projection') {
      if (!options.worldModel.projection) await options.worldModel.loadOverview(id)
    }
    if (section === 'timeline') {
      if (!options.athena.timeline) await options.athena.loadTimeline(id)
    }
    if (section === 'knowledge') {
      if (!options.worldModel.projection) await options.worldModel.loadOverview(id)
    }
    if (section === 'retrieval') {
      await options.athena.loadRetrievalDiagnostics(id)
    }
    if (section === 'proposals') {
      if (!options.worldModel.loaded || !options.worldModel.proposalBundles.length) {
        await options.worldModel.loadSetupPanelData(id)
      }
    }
    if (section === 'consistency') {
      await options.athena.loadConsistencyIssues(id)
    }
    if (section === 'optimization') {
      await options.athena.loadOptimization(id)
    }
    if (section === 'outline' || section === 'storyline') {
      if (!options.athena.evolutionPlan) await options.athena.loadEvolutionPlan(id)
    }
  }

  return { loadSectionData }
}
