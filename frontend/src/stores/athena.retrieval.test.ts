import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAthenaStore } from './athena'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getAthenaRetrievalDiagnostics: vi.fn(),
    searchAthenaRetrieval: vi.fn(),
    reindexAthenaRetrieval: vi.fn(),
  },
}))

describe('athena retrieval store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads retrieval diagnostics', async () => {
    vi.mocked(api.getAthenaRetrievalDiagnostics).mockResolvedValue({
      project_id: 'project-1',
      embedding_provider: 'local',
      embedding_model: 'hash-bigram-v1',
      vector_dimension: 96,
      total_documents: 3,
      total_chunks: 4,
      total_terms: 27,
      total_embeddings: 4,
      documents_by_source_type: { chapter: 2, world_fact: 1 },
    })
    const store = useAthenaStore()

    await store.loadRetrievalDiagnostics('project-1')

    expect(store.retrievalDiagnostics?.total_chunks).toBe(4)
    expect(api.getAthenaRetrievalDiagnostics).toHaveBeenCalledWith('project-1')
  })

  it('searches retrieval evidence and keeps ordered results', async () => {
    vi.mocked(api.searchAthenaRetrieval).mockResolvedValue({
      query: '旧灯塔',
      total: 1,
      items: [
        {
          chunk_id: 'chunk-1',
          document_id: 'doc-1',
          source_type: 'world_fact',
          source_ref: 'claim:1',
          title: 'rule.old_lighthouse.recall_constraint',
          chapter_index: 2,
          score: 0.88,
          lexical_score: 0.7,
          vector_score: 0.9,
          snippet: '旧灯塔熄灭时，亡者不能被直接召回。',
          metadata: { claim_id: 'claim.old_lighthouse.recall_ban' },
        },
      ],
    })
    const store = useAthenaStore()

    await store.searchRetrieval('project-1', '旧灯塔')

    expect(store.retrievalSearch?.items[0].source_type).toBe('world_fact')
    expect(api.searchAthenaRetrieval).toHaveBeenCalledWith('project-1', { q: '旧灯塔' })
  })

  it('reindexes retrieval and refreshes diagnostics', async () => {
    vi.mocked(api.reindexAthenaRetrieval).mockResolvedValue({
      status: 'completed',
      project_id: 'project-1',
      chapter_index: null,
      indexed: { documents: 3, chunks: 4, terms: 27, embeddings: 4 },
    })
    vi.mocked(api.getAthenaRetrievalDiagnostics).mockResolvedValue({
      project_id: 'project-1',
      embedding_provider: 'local',
      embedding_model: 'hash-bigram-v1',
      vector_dimension: 96,
      total_documents: 3,
      total_chunks: 4,
      total_terms: 27,
      total_embeddings: 4,
      documents_by_source_type: { chapter: 2, world_fact: 1 },
    })
    const store = useAthenaStore()

    await store.reindexRetrieval('project-1')

    expect(store.retrievalLastIndexResult?.indexed.documents).toBe(3)
    expect(api.getAthenaRetrievalDiagnostics).toHaveBeenCalledWith('project-1')
  })
})
