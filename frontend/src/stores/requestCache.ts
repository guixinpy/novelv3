import { defineStore } from 'pinia'

interface RequestCacheState {
  inFlight: Map<string, Promise<unknown>>
  freshAt: Map<string, number>
}

export function createRequestCache(now = () => Date.now()) {
  const state: RequestCacheState = {
    inFlight: new Map(),
    freshAt: new Map(),
  }

  async function dedupe<T>(key: string, loader: () => Promise<T>): Promise<T> {
    const existing = state.inFlight.get(key) as Promise<T> | undefined
    if (existing) return existing

    const promise = loader()
      .then((value) => {
        state.freshAt.set(key, now())
        return value
      })
      .finally(() => {
        state.inFlight.delete(key)
      })

    state.inFlight.set(key, promise)
    return promise
  }

  function markFresh(key: string) {
    state.freshAt.set(key, now())
  }

  function isFresh(key: string, ttlMs: number) {
    const freshAt = state.freshAt.get(key)
    return freshAt !== undefined && now() - freshAt <= ttlMs
  }

  function invalidate(prefix: string) {
    for (const key of [...state.freshAt.keys()]) {
      if (key.startsWith(prefix)) state.freshAt.delete(key)
    }
    for (const key of [...state.inFlight.keys()]) {
      if (key.startsWith(prefix)) state.inFlight.delete(key)
    }
  }

  return {
    dedupe,
    markFresh,
    isFresh,
    invalidate,
  }
}

export const useRequestCacheStore = defineStore('requestCache', () => createRequestCache())
