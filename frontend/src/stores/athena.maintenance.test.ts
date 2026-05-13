import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAthenaStore } from './athena'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getAthenaLongformMaintenanceDiagnostics: vi.fn(),
    repairAthenaLongformMaintenance: vi.fn(),
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

  it('repairs longform maintenance and applies remaining diagnostics', async () => {
    vi.mocked(api.repairAthenaLongformMaintenance).mockResolvedValue({
      project_id: 'project-1',
      status: 'completed',
      repaired_memory_count: 1,
      repaired_retrieval_count: 3,
      refreshed_chapter_indexes: [512],
      synced_scope_keys: ['chapter:512', 'arc:501-520', 'global'],
      has_more: false,
      remaining_issue_count: 0,
      remaining: {
        project_id: 'project-1',
        status: 'current',
        chapter_count: 1000,
        stale_memory_count: 0,
        missing_memory_count: 0,
        stale_retrieval_count: 0,
        missing_retrieval_count: 0,
        stale_chapter_indexes: [],
        missing_memory_chapter_indexes: [],
        stale_retrieval_chapter_indexes: [],
        missing_retrieval_chapter_indexes: [],
        latest_chapter_updated_at: '2026-05-13T00:00:00Z',
        latest_memory_updated_at: '2026-05-13T00:00:01Z',
        latest_retrieval_updated_at: '2026-05-13T00:00:02Z',
        latest_synced_chapter_index: 1000,
      },
    })
    const store = useAthenaStore()

    await store.repairLongformMaintenance('project-1')

    expect(api.repairAthenaLongformMaintenance).toHaveBeenCalledWith('project-1')
    expect(store.longformMaintenanceRepairResult?.refreshed_chapter_indexes).toEqual([512])
    expect(store.longformMaintenanceDiagnostics?.status).toBe('current')
  })
})
