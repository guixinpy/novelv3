import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAthenaStore } from './athena'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    sendAthenaChat: vi.fn(),
    getAthenaMessages: vi.fn(),
    getAthenaEvolutionProposals: vi.fn(),
    getAthenaOntology: vi.fn(),
    getAthenaState: vi.fn(),
  },
}))

describe('athena chat store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('refreshes proposals after Athena chat creates a proposal', async () => {
    vi.mocked(api.sendAthenaChat).mockResolvedValue({
      message: '已创建待审提案',
      pending_action: null,
      ui_hint: null,
      refresh_targets: ['proposals'],
      project_diagnosis: {
        missing_items: [],
        completed_items: [],
        suggested_next_step: null,
      },
    })
    vi.mocked(api.getAthenaMessages).mockResolvedValue([])
    vi.mocked(api.getAthenaEvolutionProposals).mockResolvedValue({
      items: [
        {
          id: 'bundle-1',
          project_id: 'project-1',
          project_profile_version_id: 'profile-1',
          profile_version: 1,
          parent_bundle_id: null,
          bundle_status: 'pending',
          title: 'Athena 对话待审世界更新',
          summary: '',
          created_by: 'athena.dialog',
          created_at: '2026-04-26T00:00:00Z',
          updated_at: '2026-04-26T00:00:00Z',
        },
      ],
      total: 1,
      offset: 0,
      limit: 20,
    })
    const store = useAthenaStore()

    await store.sendChat('project-1', '请更新世界模型')

    expect(api.sendAthenaChat).toHaveBeenCalledWith('project-1', '请更新世界模型')
    expect(api.getAthenaMessages).toHaveBeenCalledWith('project-1')
    expect(api.getAthenaEvolutionProposals).toHaveBeenCalledWith('project-1', undefined)
    expect(store.proposals?.total).toBe(1)
  })
})
