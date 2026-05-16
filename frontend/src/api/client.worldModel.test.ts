import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './client'

describe('world model api client', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('getWorldModelOverview() 和 listWorldProposalBundles() 命中预期路径', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ([]),
    } as Response)

    await api.getWorldModelOverview('project-1')
    await api.listWorldProposalBundles('project-1')

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/v1/projects/project-1/world-model',
      expect.objectContaining({
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      '/api/v1/projects/project-1/world-model/proposal-bundles',
      expect.objectContaining({
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  })

  it('getWorldModelOverview() serializes projection window params', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ([]),
    } as Response)

    await api.getWorldModelOverview('project-1', {
      entity_offset: 20,
      entity_limit: 40,
      relation_offset: 10,
      relation_limit: 30,
      presence_offset: 5,
      presence_limit: 25,
      event_offset: 100,
      event_limit: 50,
      fact_subject_offset: 200,
      fact_subject_limit: 60,
    })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/projects/project-1/world-model?entity_offset=20&entity_limit=40&relation_offset=10&relation_limit=30&presence_offset=5&presence_limit=25&event_offset=100&event_limit=50&fact_subject_offset=200&fact_subject_limit=60',
      expect.objectContaining({
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  })

  it('getAthenaOntology() serializes ontology window params', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ entities: {}, relations: [], rules: [] }),
    } as Response)

    await api.getAthenaOntology('project-1', {
      entity_offset: 20,
      entity_limit: 80,
      relation_offset: 10,
      relation_limit: 120,
      rule_offset: 5,
      rule_limit: 40,
    } as any)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/projects/project-1/athena/ontology?entity_offset=20&entity_limit=80&relation_offset=10&relation_limit=120&rule_offset=5&rule_limit=40',
      expect.objectContaining({
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  })

  it('getAthenaCharacterGraph() serializes topology window params', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ nodes: [], edges: [] }),
    } as Response)

    await api.getAthenaCharacterGraph('project-1', {
      node_offset: 10,
      node_limit: 20,
      edge_offset: 30,
      edge_limit: 40,
    })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/projects/project-1/athena/ontology/character-graph?node_offset=10&node_limit=20&edge_offset=30&edge_limit=40',
      expect.objectContaining({
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  })

  it('getAthenaOptimization() serializes rule window params', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ rules: [], style_config: {}, learning_logs: [] }),
    } as Response)

    await api.getAthenaOptimization('project-1', {
      rules_offset: 100,
      rules_limit: 50,
    })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/projects/project-1/athena/optimization?rules_offset=100&rules_limit=50',
      expect.objectContaining({
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  })

  it('getWorldProposalReviewQueue() serializes queue window params', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ total_items: 0, clusters: [] }),
    } as Response)

    await api.getWorldProposalReviewQueue('project-1', {
      offset: 40,
      limit: 20,
    })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/projects/project-1/world-model/proposal-review-queue?offset=40&limit=20',
      expect.objectContaining({
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  })
})
