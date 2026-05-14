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
  shouldHydratePanelTarget,
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
    store.chaptersTotal = 10
    store.chaptersOffset = 2
    store.chaptersLimit = 5
    store.chaptersHasMore = true
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
    expect(store.chaptersTotal).toBe(0)
    expect(store.chaptersOffset).toBe(0)
    expect(store.chaptersLimit).toBe(0)
    expect(store.chaptersHasMore).toBe(false)
    expect(store.chaptersLatestIndex).toBe(null)
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

  it('同项目并发 loadSetup 会去重，loadVersions 不同筛选仍由新请求结果赢', async () => {
    const store = useProjectStore()

    let resolveSetup!: (value: any) => void
    let resolveOldVersions!: (value: any[]) => void
    let resolveNewVersions!: (value: any[]) => void

    vi.mocked(api.getSetup).mockImplementation(() => new Promise((resolve) => {
      resolveSetup = resolve
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

    expect(api.getSetup).toHaveBeenCalledTimes(1)
    resolveSetup({ id: 'setup-deduped', title: '去重设定' })
    resolveNewVersions([{ id: 'version-new-all', node_type: 'all' }])
    await newSetupPromise
    await newVersionsPromise

    resolveOldVersions([{ id: 'version-old-outline', node_type: 'outline' }])
    await oldSetupPromise
    await oldVersionsPromise

    expect(store.setup).toEqual({ id: 'setup-deduped', title: '去重设定' })
    expect(store.versions).toEqual([{ id: 'version-new-all', node_type: 'all' }])
    expect(store.versionsNodeType).toBe(undefined)
  })

  it('同项目并发 loadProject 会复用同一个 in-flight 请求', async () => {
    const store = useProjectStore()

    let resolveProject!: (value: any) => void
    vi.mocked(api.getProject).mockImplementation(() => new Promise((resolve) => {
      resolveProject = resolve
    }))

    const first = store.loadProject('A')
    const second = store.loadProject('A')

    expect(api.getProject).toHaveBeenCalledTimes(1)
    resolveProject({ id: 'A', name: '项目 A' })
    await first
    await second

    expect(store.currentProject).toEqual({ id: 'A', name: '项目 A' })
  })

  it('同项目 fresh 数据再次 loadProject/loadChapters 不重复请求', async () => {
    const store = useProjectStore()

    vi.mocked(api.getProject).mockResolvedValue({ id: 'A', name: '项目 A' })
    vi.mocked(api.listChapters).mockResolvedValue({
      chapters: [{ id: 'chapter-1', chapter_index: 1, title: '第一章', word_count: 0, status: 'generated' }],
    })

    await store.loadProject('A')
    await store.loadChapters('A')
    await store.loadProject('A')
    await store.loadChapters('A')

    expect(api.getProject).toHaveBeenCalledTimes(1)
    expect(api.listChapters).toHaveBeenCalledTimes(1)
    expect(store.currentProject).toEqual({ id: 'A', name: '项目 A' })
    expect(store.chapters).toEqual([{ id: 'chapter-1', chapter_index: 1, title: '第一章', word_count: 0, status: 'generated' }])
  })

  it('loadChapters(force) 会绕过 fresh 缓存刷新章节列表', async () => {
    const store = useProjectStore()

    store.applyWorkspaceBootstrap({
      project: { id: 'A', name: '项目 A' },
      diagnosis: { missing_items: [], completed_items: [], suggested_next_step: null },
      chapters: [],
      versions: [],
      dialogs: { hermes: { messages: [] }, athena: { messages: [] } },
    } as any)
    vi.mocked(api.listChapters).mockResolvedValue({
      chapters: [{ id: 'chapter-1', chapter_index: 1, title: '第一章', word_count: 0, status: 'generated' }],
      total: 250,
      offset: 0,
      limit: 200,
      has_more: true,
      latest_chapter_index: 250,
    })

    await store.loadChapters('A', true)

    expect(api.listChapters).toHaveBeenCalledTimes(1)
    expect(store.chapters).toEqual([{ id: 'chapter-1', chapter_index: 1, title: '第一章', word_count: 0, status: 'generated' }])
    expect(store.chaptersTotal).toBe(250)
    expect(store.chaptersOffset).toBe(0)
    expect(store.chaptersLimit).toBe(200)
    expect(store.chaptersHasMore).toBe(true)
    expect(store.chaptersLatestIndex).toBe(250)
  })

  it('loadMoreChapters() 会从已加载数量继续追加下一页章节', async () => {
    const store = useProjectStore()
    const firstPage = Array.from({ length: 200 }, (_, index) => ({
      id: `chapter-${index + 1}`,
      chapter_index: index + 1,
      title: `第${index + 1}章`,
      word_count: 1000,
      status: 'generated',
    }))
    const secondPage = Array.from({ length: 50 }, (_, index) => ({
      id: `chapter-${index + 201}`,
      chapter_index: index + 201,
      title: `第${index + 201}章`,
      word_count: 1000,
      status: 'generated',
    }))

    store.applyWorkspaceBootstrap({
      project: { id: 'A', name: '项目 A' },
      diagnosis: { missing_items: [], completed_items: ['content'], suggested_next_step: null },
      chapters: firstPage,
      chapters_total: 250,
      chapters_offset: 0,
      chapters_limit: 200,
      chapters_has_more: true,
      versions: [],
      dialogs: { hermes: { messages: [] }, athena: { messages: [] } },
    } as any)
    vi.mocked(api.listChapters).mockResolvedValue({
      chapters: secondPage,
      total: 250,
      offset: 200,
      limit: 200,
      has_more: false,
      latest_chapter_index: 250,
    })

    await store.loadMoreChapters('A')

    expect(api.listChapters).toHaveBeenCalledWith('A', { offset: 200, limit: 200 })
    expect(store.chapters).toHaveLength(250)
    expect(store.chapters[199].chapter_index).toBe(200)
    expect(store.chapters[200].chapter_index).toBe(201)
    expect(store.chaptersTotal).toBe(250)
    expect(store.chaptersOffset).toBe(200)
    expect(store.chaptersLimit).toBe(200)
    expect(store.chaptersHasMore).toBe(false)
    expect(store.chaptersLatestIndex).toBe(250)
  })

  it('loadMoreVersions() 会从已加载数量继续追加下一页版本', async () => {
    const store = useProjectStore()
    const firstPage = [
      { id: 'version-1', node_type: 'chapter', node_id: 'chapter-1', version_number: 3 },
      { id: 'version-2', node_type: 'chapter', node_id: 'chapter-1', version_number: 2 },
    ]
    const secondPage = [
      { id: 'version-3', node_type: 'chapter', node_id: 'chapter-1', version_number: 1 },
    ]

    vi.mocked(api.listVersions).mockResolvedValueOnce({
      versions: firstPage,
      total: 3,
      offset: 0,
      limit: 2,
      has_more: true,
    })
    vi.mocked(api.listVersions).mockResolvedValueOnce({
      versions: secondPage,
      total: 3,
      offset: 2,
      limit: 2,
      has_more: false,
    })

    await store.loadVersions('A', 'chapter')
    await store.loadMoreVersions('A')

    expect(api.listVersions).toHaveBeenNthCalledWith(1, 'A', 'chapter', { offset: 0, limit: 50 })
    expect(api.listVersions).toHaveBeenNthCalledWith(2, 'A', 'chapter', { offset: 2, limit: 2 })
    expect(store.versions).toEqual([...firstPage, ...secondPage])
    expect(store.versionsTotal).toBe(3)
    expect(store.versionsOffset).toBe(2)
    expect(store.versionsLimit).toBe(2)
    expect(store.versionsHasMore).toBe(false)
  })

  it('refreshTargets(content) 会强制刷新章节，避免任务完成后沿用旧列表', async () => {
    const store = useProjectStore()

    store.applyWorkspaceBootstrap({
      project: { id: 'A', name: '项目 A' },
      diagnosis: { missing_items: [], completed_items: [], suggested_next_step: null },
      chapters: [],
      versions: [],
      dialogs: { hermes: { messages: [] }, athena: { messages: [] } },
    } as any)
    vi.mocked(api.listChapters).mockResolvedValue({
      chapters: [{ id: 'chapter-1', chapter_index: 1, title: '第一章', word_count: 0, status: 'generated' }],
    })

    const successTargets = await store.refreshTargets('A', ['content'])

    expect(successTargets).toEqual(['content'])
    expect(api.listChapters).toHaveBeenCalledTimes(1)
    expect(store.chapters).toEqual([{ id: 'chapter-1', chapter_index: 1, title: '第一章', word_count: 0, status: 'generated' }])
  })

  it('workspace bootstrap 会填充项目冷启动数据并标记为 fresh', async () => {
    const store = useProjectStore()

    store.applyWorkspaceBootstrap({
      project: { id: 'A', name: '项目 A' },
      diagnosis: { missing_items: [], completed_items: ['content'], suggested_next_step: null },
      setup: { id: 'setup-1', project_id: 'A', status: 'generated' },
      storyline: { id: 'storyline-1', project_id: 'A', status: 'generated' },
      outline: { id: 'outline-1', project_id: 'A', status: 'generated' },
      chapters: [{ id: 'chapter-1', chapter_index: 1, title: '第一章', word_count: 120, status: 'generated' }],
      chapters_total: 250,
      chapters_offset: 0,
      chapters_limit: 200,
      chapters_has_more: true,
      chapters_latest_index: 250,
      versions: [{ id: 'version-1', node_type: 'chapter', node_id: 'chapter-1', version_number: 1 }],
      dialogs: { hermes: { messages: [] }, athena: { messages: [] } },
    } as any)

    await store.loadProject('A')
    await store.loadSetup('A')
    await store.loadStoryline('A')
    await store.loadOutline('A')
    await store.loadChapters('A')
    await store.loadVersions('A')

    expect(api.getProject).not.toHaveBeenCalled()
    expect(api.getSetup).not.toHaveBeenCalled()
    expect(api.getStoryline).not.toHaveBeenCalled()
    expect(api.getOutline).not.toHaveBeenCalled()
    expect(api.listChapters).not.toHaveBeenCalled()
    expect(api.listVersions).not.toHaveBeenCalled()
    expect(store.currentProject).toEqual({ id: 'A', name: '项目 A' })
    expect(store.setup).toEqual({ id: 'setup-1', project_id: 'A', status: 'generated' })
    expect(store.storyline).toEqual({ id: 'storyline-1', project_id: 'A', status: 'generated' })
    expect(store.outline).toEqual({ id: 'outline-1', project_id: 'A', status: 'generated' })
    expect(store.chapters).toEqual([{ id: 'chapter-1', chapter_index: 1, title: '第一章', word_count: 120, status: 'generated' }])
    expect(store.chaptersTotal).toBe(250)
    expect(store.chaptersLimit).toBe(200)
    expect(store.chaptersHasMore).toBe(true)
    expect(store.chaptersLatestIndex).toBe(250)
    expect(store.versions).toEqual([{ id: 'version-1', node_type: 'chapter', node_id: 'chapter-1', version_number: 1 }])
  })

  it('workspace bootstrap 的 partial outline 不会被标记为完整大纲缓存', async () => {
    const store = useProjectStore()
    vi.mocked(api.getOutline).mockResolvedValue({
      id: 'outline-full',
      project_id: 'A',
      status: 'generated',
      total_chapters: 1000,
      chapters: [{ chapter_index: 201, title: '第201章', summary: '继续推进' }],
    })

    store.applyWorkspaceBootstrap({
      project: { id: 'A', name: '项目 A' },
      diagnosis: { missing_items: [], completed_items: ['outline'], suggested_next_step: null },
      setup: null,
      storyline: null,
      outline: { id: 'outline-1', project_id: 'A', status: 'generated', total_chapters: 1000, chapters: [] },
      outline_partial: true,
      chapters: [],
      versions: [],
      dialogs: { hermes: { messages: [] }, athena: { messages: [] } },
    } as any)

    await store.loadOutline('A')

    expect(api.getOutline).toHaveBeenCalledWith('A')
    expect(store.outline).toEqual({
      id: 'outline-full',
      project_id: 'A',
      status: 'generated',
      total_chapters: 1000,
      chapters: [{ chapter_index: 201, title: '第201章', summary: '继续推进' }],
    })
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

  it('exportProject() 遇到失败响应时抛出后端错误且不下载错误内容', async () => {
    const store = useProjectStore()
    const originalCreateObjectURL = URL.createObjectURL
    const originalRevokeObjectURL = URL.revokeObjectURL
    const originalDocument = globalThis.document
    const createObjectURL = vi.fn(() => 'blob:failed-export')
    const revokeObjectURL = vi.fn()
    const click = vi.fn()
    Object.defineProperty(URL, 'createObjectURL', { value: createObjectURL, configurable: true })
    Object.defineProperty(URL, 'revokeObjectURL', { value: revokeObjectURL, configurable: true })
    Object.defineProperty(globalThis, 'document', {
      value: { createElement: vi.fn(() => ({ href: '', download: '', click })) },
      configurable: true,
    })
    vi.mocked(api.exportProject).mockResolvedValue({
      ok: false,
      json: async () => ({ detail: 'export failed' }),
      blob: async () => new Blob(['{"detail":"export failed"}'], { type: 'application/json' }),
    } as Response)

    try {
      await expect(store.exportProject('A', 'markdown')).rejects.toThrow('export failed')
      expect(createObjectURL).not.toHaveBeenCalled()
      expect(revokeObjectURL).not.toHaveBeenCalled()
    } finally {
      Object.defineProperty(URL, 'createObjectURL', { value: originalCreateObjectURL, configurable: true })
      Object.defineProperty(URL, 'revokeObjectURL', { value: originalRevokeObjectURL, configurable: true })
      Object.defineProperty(globalThis, 'document', { value: originalDocument, configurable: true })
    }
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

  it('Hermes 面板切换不加载诊断中未完成的可选资源', () => {
    const diagnosis = (completedItems: string[]): ProjectDiagnosis => ({
      completed_items: completedItems,
      missing_items: [],
      suggested_next_step: null,
    })

    expect(shouldHydratePanelTarget('setup', diagnosis([]))).toBe(false)
    expect(shouldHydratePanelTarget('storyline', diagnosis(['setup']))).toBe(false)
    expect(shouldHydratePanelTarget('setup', diagnosis(['setup']))).toBe(true)
    expect(shouldHydratePanelTarget('content', diagnosis([]))).toBe(true)
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
