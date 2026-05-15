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

  it('getOutline() reads the bounded evolution-plan outline window', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ outline: { id: 'outline-1', chapters: [], chapters_total: 1000 }, storyline: null }),
    } as Response)

    const outline = await api.getOutline('project-1')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/projects/project-1/athena/evolution/plan?mode=window',
      expect.objectContaining({
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    expect(outline).toEqual({ id: 'outline-1', chapters: [], chapters_total: 1000 })
  })

  it('getStoryline() reads the bounded evolution-plan storyline window', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ outline: null, storyline: { id: 'storyline-1', plotlines: [], plotlines_total: 60 } }),
    } as Response)

    const storyline = await api.getStoryline('project-1')

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/projects/project-1/athena/evolution/plan?mode=window',
      expect.objectContaining({
        headers: { 'Content-Type': 'application/json' },
      }),
    )
    expect(storyline).toEqual({ id: 'storyline-1', plotlines: [], plotlines_total: 60 })
  })
})
