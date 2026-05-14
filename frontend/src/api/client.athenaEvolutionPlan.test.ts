import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './client'

describe('athena evolution plan api client', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('getAthenaEvolutionPlan() serializes window parameters', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ outline: null, storyline: null }),
    } as Response)

    await api.getAthenaEvolutionPlan('project-1', {
      mode: 'window',
      chapter_offset: 100,
      chapter_limit: 50,
      plotline_offset: 10,
      plotline_limit: 20,
      milestone_offset: 40,
      milestone_limit: 80,
      foreshadowing_offset: 200,
      foreshadowing_limit: 100,
    })

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/projects/project-1/athena/evolution/plan?mode=window&chapter_offset=100&chapter_limit=50&plotline_offset=10&plotline_limit=20&milestone_offset=40&milestone_limit=80&foreshadowing_offset=200&foreshadowing_limit=100',
      expect.objectContaining({
        headers: { 'Content-Type': 'application/json' },
      }),
    )
  })
})
