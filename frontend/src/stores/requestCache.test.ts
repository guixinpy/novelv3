import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createRequestCache } from './requestCache'

describe('request cache', () => {
  beforeEach(() => {
    vi.useRealTimers()
  })

  it('dedupes in-flight requests by key', async () => {
    const cache = createRequestCache()
    const loader = vi.fn(async () => 'value')

    const [a, b] = await Promise.all([
      cache.dedupe('project:1', loader),
      cache.dedupe('project:1', loader),
    ])

    expect(a).toBe('value')
    expect(b).toBe('value')
    expect(loader).toHaveBeenCalledTimes(1)
  })

  it('does not cache failed requests as fresh', async () => {
    const cache = createRequestCache()

    await expect(cache.dedupe('project:1', async () => { throw new Error('boom') })).rejects.toThrow('boom')

    expect(cache.isFresh('project:1', 1000)).toBe(false)
  })

  it('marks successful requests fresh and supports invalidation', async () => {
    const cache = createRequestCache()

    await cache.dedupe('project:1:chapters', async () => [])

    expect(cache.isFresh('project:1:chapters', 1000)).toBe(true)
    cache.invalidate('project:1')
    expect(cache.isFresh('project:1:chapters', 1000)).toBe(false)
  })
})
