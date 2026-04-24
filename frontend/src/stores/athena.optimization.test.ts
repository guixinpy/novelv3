import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAthenaStore } from './athena'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getAthenaOptimization: vi.fn(),
  },
}))

describe('athena optimization store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('loads optimization state and resets it', async () => {
    vi.mocked(api.getAthenaOptimization).mockResolvedValue({
      rules: [
        {
          id: 'rule-1',
          rule_type: 'learned',
          condition: '用户反馈节奏太慢',
          action: '减少铺垫，加快场景推进',
          priority: 80,
          hit_count: 0,
          created_at: '2026-04-24T00:00:00Z',
        },
      ],
      style_config: { description_density: 2 },
      learning_logs: [
        {
          rule_id: 'rule-1',
          event_type: 'rule_learned',
          summary: '学到规则：用户反馈节奏太慢 → 减少铺垫，加快场景推进',
          created_at: '2026-04-24T00:00:00Z',
        },
      ],
    })
    const store = useAthenaStore()

    await store.loadOptimization('project-1')

    expect(api.getAthenaOptimization).toHaveBeenCalledWith('project-1')
    expect(store.optimization?.rules[0].condition).toBe('用户反馈节奏太慢')
    expect(store.optimization?.style_config.description_density).toBe(2)

    store.reset()
    expect(store.optimization).toBeNull()
  })
})
