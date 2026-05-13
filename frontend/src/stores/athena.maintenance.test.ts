import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAthenaStore } from './athena'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getAthenaLongformMaintenanceDiagnostics: vi.fn(),
  },
}))

describe('athena longform maintenance store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads longform maintenance diagnostics and resets them with project state', async () => {
    vi.mocked(api.getAthenaLongformMaintenanceDiagnostics).mockResolvedValue({
      project_id: 'project-1',
      status: 'stale',
      chapter_count: 1000,
      stale_memory_count: 1,
      missing_memory_count: 0,
      stale_retrieval_count: 2,
      missing_retrieval_count: 0,
      stale_chapter_indexes: [512],
      missing_memory_chapter_indexes: [],
      stale_retrieval_chapter_indexes: [512, 780],
      missing_retrieval_chapter_indexes: [],
      latest_chapter_updated_at: '2026-05-13T00:00:00Z',
      latest_memory_updated_at: '2026-05-13T00:00:01Z',
      latest_retrieval_updated_at: '2026-05-12T23:59:59Z',
      latest_synced_chapter_index: 1000,
    })
    const store = useAthenaStore()

    await store.loadLongformMaintenanceDiagnostics('project-1')

    expect(api.getAthenaLongformMaintenanceDiagnostics).toHaveBeenCalledWith('project-1')
    expect(store.longformMaintenanceDiagnostics?.status).toBe('stale')
    expect(store.longformMaintenanceDiagnostics?.stale_retrieval_chapter_indexes).toEqual([512, 780])

    store.reset()
    expect(store.longformMaintenanceDiagnostics).toBeNull()
  })
})
