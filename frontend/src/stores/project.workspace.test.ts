import { describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectStore } from './project'

describe('project workspace state', () => {
  it('resetProjectScopedState() 会清掉跨项目残留的版本筛选和详情缓存', () => {
    setActivePinia(createPinia())
    const store = useProjectStore()

    store.currentProject = { id: 'project-a' }
    store.setup = { id: 'setup-a' }
    store.storyline = { id: 'storyline-a' }
    store.outline = { id: 'outline-a' }
    store.chapter = { id: 'chapter-a' }
    store.topology = { id: 'topology-a' }
    store.chapters = [{ id: 'chapter-a' }]
    store.versions = [{ id: 'version-a' }]
    store.preferences = { id: 'preferences-a' }
    store.versionsNodeType = 'outline'

    store.resetProjectScopedState()

    expect(store.currentProject).toBe(null)
    expect(store.setup).toBe(null)
    expect(store.storyline).toBe(null)
    expect(store.outline).toBe(null)
    expect(store.chapter).toBe(null)
    expect(store.topology).toBe(null)
    expect(store.chapters).toEqual([])
    expect(store.versions).toEqual([])
    expect(store.preferences).toBe(null)
    expect(store.versionsNodeType).toBe(undefined)
  })
})
