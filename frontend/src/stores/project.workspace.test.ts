import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectStore } from './project'
import { api } from '../api/client'
import type { ProjectDiagnosis } from '../api/types'
import {
  beginHydration,
  createHydrationTracker,
  getInitialProjectHydrationTargets,
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

  it('同项目并发 loadSetup/loadVersions 时，新请求结果必须赢，旧响应不能回写覆盖', async () => {
    const store = useProjectStore()

    let resolveOldSetup!: (value: any) => void
    let resolveNewSetup!: (value: any) => void
    let resolveOldVersions!: (value: any[]) => void
    let resolveNewVersions!: (value: any[]) => void

    vi.mocked(api.getSetup).mockImplementation(() => new Promise((resolve) => {
      if (!resolveOldSetup) {
        resolveOldSetup = resolve
      } else {
        resolveNewSetup = resolve
      }
    }))

    vi.mocked(api.listVersions).mockImplementation((_projectId: string, nodeType?: string) => new Promise((resolve) => {
      if (nodeType === 'outline') {
        resolveOldVersions = resolve
      } else {
        resolveNewVersions = resolve
      }
    }))

    store.resetProjectScopedState('A')
    const oldSetupPromise = store.loadSetup('A')
    const newSetupPromise = store.loadSetup('A')
    const oldVersionsPromise = store.loadVersions('A', 'outline')
    const newVersionsPromise = store.loadVersions('A')

    resolveNewSetup({ id: 'setup-new', title: '新设定' })
    resolveNewVersions([{ id: 'version-new-all', node_type: 'all' }])
    await newSetupPromise
    await newVersionsPromise

    resolveOldSetup({ id: 'setup-old', title: '旧设定' })
    resolveOldVersions([{ id: 'version-old-outline', node_type: 'outline' }])
    await oldSetupPromise
    await oldVersionsPromise

    expect(store.setup).toEqual({ id: 'setup-new', title: '新设定' })
    expect(store.versions).toEqual([{ id: 'version-new-all', node_type: 'all' }])
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

  it('Hermes 初始水合只加载诊断中已完成的可选资源，避免新项目刷新打出 404', () => {
    const diagnosis = (completedItems: string[]): ProjectDiagnosis => ({
      completed_items: completedItems,
      missing_items: [],
      suggested_next_step: null,
    })

    expect(getInitialProjectHydrationTargets(diagnosis([]))).toEqual([])
    expect(getInitialProjectHydrationTargets(diagnosis(['setup']))).toEqual(['setup'])
    expect(getInitialProjectHydrationTargets(diagnosis(['setup', 'storyline', 'outline']))).toEqual([
      'setup',
      'storyline',
      'outline',
    ])
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
