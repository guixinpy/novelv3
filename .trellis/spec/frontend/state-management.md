# State Management

> How state is managed in this project.

---

## Overview

- **Global state**: Pinia 2.2 (Composition API syntax — `defineStore('name', () => {...})`)
- **Server state**: No dedicated library (no TanStack Query, no SWR)
- **Caching**: Custom `requestCache` store for dedup + freshness
- **Stale update prevention**: Request snapshot pattern

---

## Store Pattern

All stores use the Composition API syntax:

```typescript
// stores/project.ts
export const useProjectStore = defineStore('project', () => {
  // State: refs
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)

  // Actions: async functions
  async function loadProjects() {
    loading.value = true
    try {
      projects.value = await api.listProjects()
    } catch {
      // silently handle recoverable errors
    } finally {
      loading.value = false
    }
  }

  async function selectProject(id: string) {
    currentProject.value = await api.getProject(id)
  }

  return { projects, currentProject, loading, loadProjects, selectProject }
})
```

---

## Store Categories

| Store | Domain | Key State |
|-------|--------|-----------|
| `project` | Projects CRUD | projects list, current project |
| `chat` | Hermes chat | messages, sessions, streaming state |
| `athena` | World-building | overview, sections, modules |
| `worldModel` | World model | entities, profiles, events |
| `manuscript` | Manuscript editing | content, revisions, selections |
| `modelTraces` | AI call traces | trace data, filters |
| `workspace` | Workspace meta | active workspace, preferences |
| `projectWorkspace` | Project workspace | workspace context per project |
| `requestCache` | Generic cache | dedup tokens, freshness TTL |
| `ui` | UI state | panels, modals, toasts |

---

## Caching Pattern (requestCache)

Prevents duplicate in-flight requests and caches fresh data:

```typescript
// stores/requestCache.ts
export const useRequestCacheStore = defineStore('requestCache', () => {
  const cache = ref<Map<string, { data: any; timestamp: number }>>(new Map())
  const inflight = ref<Map<string, Promise<any>>>(new Map())
  const TTL_MS = 30_000

  function dedupe<T>(key: string, fetcher: () => Promise<T>): Promise<T> {
    if (inflight.value.has(key)) return inflight.value.get(key)!
    const promise = fetcher().finally(() => inflight.value.delete(key))
    inflight.value.set(key, promise)
    return promise
  }

  function isFresh(key: string): boolean {
    const entry = cache.value.get(key)
    return entry ? (Date.now() - entry.timestamp) < TTL_MS : false
  }

  return { cache, inflight, dedupe, isFresh }
})
```

---

## Snapshot Pattern (Stale Update Prevention)

Prevents out-of-order responses from overwriting newer data:

```typescript
// In a store action
let _lastRequest = 0

async function fetchData(projectId: string) {
  const requestId = ++_lastRequest
  const result = await api.getData(projectId)
  if (requestId !== _lastRequest) return  // stale, discard
  data.value = result
}
```

This is captured in helper functions like `captureProjectRequest()` and
`isLatestProjectRequest()` in relevant stores.

---

## Pagination Pattern

```typescript
const items = ref<Item[]>([])
const offset = ref(0)
const hasMore = ref(true)
const PAGE_LIMIT = 50

async function loadMore(projectId: string) {
  if (!hasMore.value) return
  const batch = await api.listItems(projectId, { _offset: offset.value, _limit: PAGE_LIMIT })
  items.value.push(...batch.items)
  offset.value += batch.items.length
  hasMore.value = batch._has_more
}
```

All paginated endpoints use `_offset`, `_limit`, `_has_more` query parameter names
(underscore prefix convention shared with the backend).

---

## Common Mistakes

1. **No stale update protection** — Without the snapshot pattern, a slow response
   can overwrite newer data. Always use request versioning for critical data.
2. **Over-fetching on mount** — Check `isFresh()` before fetching; avoid
   redundant requests.
3. **Mutating store state outside actions** — Always go through store actions,
   not direct assignment from components.
4. **Forgetting `catch {}`** — Network errors in async actions should be caught
   to prevent unhandled promise rejections.
5. **Global state for local UI** — Component-local `ref()` is preferred over
   store state for toggle/accordion/selection that only affects one component.
