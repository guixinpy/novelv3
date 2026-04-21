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
})
