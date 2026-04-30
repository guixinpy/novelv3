import { describe, expect, it, vi } from 'vitest'
import { createAthenaSectionLoader } from './athenaSectionLoader'

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
  }
  const worldModel = {
    dashboard: null as any,
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
  }
  return {
    athena,
    worldModel,
    loader: createAthenaSectionLoader({
      getProjectId: () => 'project-1',
      athena: athena as any,
      worldModel: worldModel as any,
      entitySections: new Set(['characters']),
    }),
  }
}

describe('createAthenaSectionLoader', () => {
  it('does not request setup import preview when setup draft is missing', async () => {
    const { athena, loader } = createLoaderMocks(null)

    await loader.loadSectionData('overview')

    expect(athena.loadSetupImportPreview).not.toHaveBeenCalled()
  })

  it('requests setup import preview when setup draft exists and profile is missing', async () => {
    const { athena, loader } = createLoaderMocks({ characters: [] })

    await loader.loadSectionData('overview')

    expect(athena.loadSetupImportPreview).toHaveBeenCalledWith('project-1')
  })

  it('does not reload proposal workbench when an empty proposal page is already loaded', async () => {
    const athena = {}
    const worldModel = {
      loaded: true,
      proposalBundles: [],
      loadSetupPanelData: vi.fn(async () => undefined),
    }
    const loader = createAthenaSectionLoader({
      getProjectId: () => 'project-1',
      athena: athena as any,
      worldModel: worldModel as any,
      entitySections: new Set(['characters']),
    })

    await loader.loadSectionData('proposals')

    expect(worldModel.loadSetupPanelData).not.toHaveBeenCalled()
  })
})
