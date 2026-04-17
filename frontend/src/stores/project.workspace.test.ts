import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectStore } from './project'
import { api } from '../api/client'
import {
  beginHydration,
  createHydrationTracker,
  markHydratedTarget,
} from '../views/projectDetailHydration'

vi.mock('../api/client', () => ({
  api: {
    getProject: vi.fn(),
    getSetup: vi.fn(),
    getStoryline: vi.fn(),
    getOutline: vi.fn(),
    getTopology: vi.fn(),
    listChapters: vi.fn(),
    listVersions: vi.fn(),
    getPreferences: vi.fn(),
    listProjects: vi.fn(),
    createProject: vi.fn(),
    generateSetup: vi.fn(),
    generateChapter: vi.fn(),
    getChapter: vi.fn(),
    generateStoryline: vi.fn(),
    generateOutline: vi.fn(),
    updatePreferences: vi.fn(),
    resetPreferences: vi.fn(),
    createVersion: vi.fn(),
    rollbackVersion: vi.fn(),
    exportProject: vi.fn(),
  },
}))

describe('project workspace state', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('resetProjectScopedState() 会清掉跨项目残留的版本筛选和详情缓存', () => {
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

  it('项目 A 的迟到 loadSetup/loadVersions 响应不会覆盖项目 B，也不会把 versionsNodeType 写回', async () => {
    const store = useProjectStore()

    let resolveSetupA!: (value: any) => void
    let resolveVersionsA!: (value: any[]) => void

    vi.mocked(api.getSetup).mockImplementation((projectId: string) => new Promise((resolve) => {
      if (projectId === 'A') {
        resolveSetupA = resolve
      } else {
        resolve({ id: 'setup-b', title: 'B 设定' })
      }
    }))

    vi.mocked(api.listVersions).mockImplementation((projectId: string, nodeType?: string) => new Promise((resolve) => {
      if (projectId === 'A') {
        resolveVersionsA = resolve
      } else {
        resolve([{ id: `version-b-${nodeType || 'all'}`, node_type: nodeType || 'all' }])
      }
    }))

    store.resetProjectScopedState('A')
    const setupAPromise = store.loadSetup('A')
    const versionsAPromise = store.loadVersions('A', 'outline')

    store.resetProjectScopedState('B')
    await store.loadSetup('B')
    await store.loadVersions('B')

    expect(store.setup).toEqual({ id: 'setup-b', title: 'B 设定' })
    expect(store.versions).toEqual([{ id: 'version-b-all', node_type: 'all' }])
    expect(store.versionsNodeType).toBe(undefined)

    resolveSetupA({ id: 'setup-a', title: 'A 设定' })
    resolveVersionsA([{ id: 'version-a-outline', node_type: 'outline' }])
    await setupAPromise
    await versionsAPromise

    expect(store.setup).toEqual({ id: 'setup-b', title: 'B 设定' })
    expect(store.versions).toEqual([{ id: 'version-b-all', node_type: 'all' }])
    expect(store.versionsNodeType).toBe(undefined)
  })

  it('refreshTargets() 只返回成功刷新的 targets，失败的不应回传', async () => {
    const store = useProjectStore()

    vi.mocked(api.getSetup).mockResolvedValue({ id: 'setup-a', title: 'A 设定' })
    vi.mocked(api.listVersions).mockRejectedValue(new Error('boom'))

    const successTargets = await store.refreshTargets('A', ['setup', 'versions'])

    expect(successTargets).toEqual(['setup'])
    expect(store.setup).toEqual({ id: 'setup-a', title: 'A 设定' })
    expect(store.versions).toEqual([])
    expect(store.versionsNodeType).toBe(undefined)
  })

  it('旧 hydration snapshot 不能再把 target 写进当前项目集合', () => {
    const tracker = createHydrationTracker()

    const snapshotA = beginHydration(tracker, 'A')
    expect(markHydratedTarget(tracker, snapshotA, 'project')).toBe(true)
    expect([...tracker.targets]).toEqual(['project'])

    const snapshotB = beginHydration(tracker, 'B')
    expect(markHydratedTarget(tracker, snapshotA, 'setup')).toBe(false)
    expect(markHydratedTarget(tracker, snapshotB, 'versions')).toBe(true)
    expect([...tracker.targets]).toEqual(['versions'])
  })
})
