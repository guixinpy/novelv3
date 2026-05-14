import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAthenaStore } from './athena'
import { useWorldModelStore } from './worldModel'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getAthenaOntology: vi.fn(),
    getAthenaMessages: vi.fn(),
    getAthenaEvolutionPlan: vi.fn(),
    runAthenaConsistencyCheck: vi.fn(),
    getConsistencyIssues: vi.fn(),
    analyzeAthenaChapter: vi.fn(),
  },
}))

function ontology(version = 1) {
  return {
    entities: { characters: [{ id: `char-${version}`, name: `角色 ${version}` }] },
    relations: [],
    rules: [],
    setup_summary: null,
    profile_version: version,
  }
}

function message(id: string) {
  return {
    id,
    role: 'assistant' as const,
    content: id,
    message_type: null,
    meta: null,
    pending_action: null,
    diagnosis: null,
    action_result: null,
    trace_id: null,
    created_at: '2026-04-29T00:00:00Z',
  }
}

function createDeferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('athena project scope', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('同项目激活不会清掉已加载的 ontology 和 messages', () => {
    const store = useAthenaStore()

    expect(store.ensureProject('project-1')).toBe(true)
    store.ontology = ontology()
    store.messages = [message('history')]

    expect(store.ensureProject('project-1')).toBe(false)

    expect(store.ontology).toEqual(ontology())
    expect(store.messages).toEqual([message('history')])
  })

  it('切换项目会清掉 Athena 项目作用域状态', () => {
    const store = useAthenaStore()

    store.ensureProject('project-1')
    store.ontology = ontology()
    store.messages = [message('history')]
    store.projection = { project_id: 'project-1' } as any

    expect(store.ensureProject('project-2')).toBe(true)

    expect(store.ontology).toBeNull()
    expect(store.messages).toEqual([])
    expect(store.projection).toBeNull()
  })

  it('切换 Athena 项目会同步清掉 worldModel 旧错误和提案状态', () => {
    const store = useAthenaStore()
    const worldModel = useWorldModelStore()

    store.ensureProject('project-1')
    worldModel.resetProjectScopedState('project-1')
    worldModel.error = 'old world error'
    worldModel.proposalBundles = [{
      id: 'bundle-old',
      project_id: 'project-1',
      project_profile_version_id: 'profile-1',
      profile_version: 1,
      parent_bundle_id: null,
      bundle_status: 'pending',
      title: '旧项目提案',
      summary: '',
      created_by: 'athena',
      created_at: '2026-04-29T00:00:00Z',
      updated_at: '2026-04-29T00:00:00Z',
    }]
    worldModel.dashboard = {
      project_profile: null,
      metrics: {
        entity_count: 0,
        fact_count: 0,
        presence_count: 0,
        event_count: 0,
        pending_bundle_count: 1,
        pending_item_count: 1,
      },
      next_action: { action: 'review_proposals', label: '处理待审世界模型提案' },
    }

    expect(store.ensureProject('project-2')).toBe(true)

    expect(worldModel.error).toBe('')
    expect(worldModel.proposalBundles).toEqual([])
    expect(worldModel.dashboard).toBeNull()
  })

  it('同项目 fresh 的 ontology 和 messages 再次加载不会重复请求', async () => {
    vi.mocked(api.getAthenaOntology).mockResolvedValue(ontology())
    vi.mocked(api.getAthenaMessages).mockResolvedValue([message('history')])
    const store = useAthenaStore()

    await store.loadOntology('project-1')
    await store.loadMessages('project-1')
    await store.loadOntology('project-1')
    await store.loadMessages('project-1')

    expect(api.getAthenaOntology).toHaveBeenCalledTimes(1)
    expect(api.getAthenaMessages).toHaveBeenCalledTimes(1)
    expect(api.getAthenaMessages).toHaveBeenCalledWith('project-1', { limit: 80 })
    expect(store.ontology).toEqual(ontology())
    expect(store.messages).toEqual([message('history')])
  })

  it('区分窗口化和完整叙事规划缓存', async () => {
    vi.mocked(api.getAthenaEvolutionPlan)
      .mockResolvedValueOnce({
        outline: { chapters: [{ index: 101 }], chapters_total: 1000 },
        storyline: null,
      } as any)
      .mockResolvedValueOnce({
        outline: { chapters: [{ index: 1 }, { index: 2 }] },
        storyline: null,
      } as any)
    const store = useAthenaStore()
    const windowParams = {
      mode: 'window' as const,
      chapter_offset: 100,
      chapter_limit: 50,
    }

    await store.loadEvolutionPlan('project-1', windowParams)
    await store.loadEvolutionPlan('project-1')

    expect(api.getAthenaEvolutionPlan).toHaveBeenCalledTimes(2)
    expect(api.getAthenaEvolutionPlan).toHaveBeenNthCalledWith(1, 'project-1', windowParams)
    expect(api.getAthenaEvolutionPlan).toHaveBeenNthCalledWith(2, 'project-1')
    expect(store.evolutionPlan).toEqual({
      outline: { chapters: [{ index: 1 }, { index: 2 }] },
      storyline: null,
    })
  })

  it('首次加载叙事规划后写入当前项目状态', async () => {
    vi.mocked(api.getAthenaEvolutionPlan).mockResolvedValue({
      outline: { chapters: [{ chapter_index: 1 }] },
      storyline: null,
    } as any)
    const store = useAthenaStore()

    await store.loadEvolutionPlan('project-1')

    expect(store.evolutionPlan).toEqual({
      outline: { chapters: [{ chapter_index: 1 }] },
      storyline: null,
    })
  })

  it('区分不同故事线节点窗口缓存', async () => {
    vi.mocked(api.getAthenaEvolutionPlan)
      .mockResolvedValueOnce({
        outline: null,
        storyline: { plotlines: [{ milestones: [{ chapter_index: 1 }] }] },
      } as any)
      .mockResolvedValueOnce({
        outline: null,
        storyline: { plotlines: [{ milestones: [{ chapter_index: 81 }] }] },
      } as any)
    const store = useAthenaStore()
    const firstWindow = {
      mode: 'window' as const,
      plotline_offset: 0,
      plotline_limit: 1,
      milestone_offset: 0,
      milestone_limit: 80,
    }
    const secondWindow = {
      ...firstWindow,
      milestone_offset: 80,
    }

    await store.loadEvolutionPlan('project-1', firstWindow)
    await store.loadEvolutionPlan('project-1', secondWindow)

    expect(api.getAthenaEvolutionPlan).toHaveBeenCalledTimes(2)
    expect(api.getAthenaEvolutionPlan).toHaveBeenNthCalledWith(1, 'project-1', firstWindow)
    expect(api.getAthenaEvolutionPlan).toHaveBeenNthCalledWith(2, 'project-1', secondWindow)
  })

  it('较慢的旧叙事规划请求不会覆盖较新的请求结果', async () => {
    const windowPlan = createDeferred<unknown>()
    const fullPlan = createDeferred<unknown>()
    vi.mocked(api.getAthenaEvolutionPlan)
      .mockReturnValueOnce(windowPlan.promise as any)
      .mockReturnValueOnce(fullPlan.promise as any)
    const store = useAthenaStore()
    const windowParams = {
      mode: 'window' as const,
      chapter_offset: 100,
      chapter_limit: 50,
    }
    const fullValue = {
      outline: { chapters: [{ index: 1 }, { index: 2 }] },
      storyline: null,
    }
    const windowValue = {
      outline: { chapters: [{ index: 101 }], chapters_total: 1000 },
      storyline: null,
    }

    const oldLoad = store.loadEvolutionPlan('project-1', windowParams)
    const newLoad = store.loadEvolutionPlan('project-1')

    fullPlan.resolve(fullValue)
    await newLoad
    expect(store.evolutionPlan).toEqual(fullValue)

    windowPlan.resolve(windowValue)
    await oldLoad
    expect(store.evolutionPlan).toEqual(fullValue)
  })

  it('prevents stale same-project cached loads from overwriting state after reset', async () => {
    let resolveOld!: (value: ReturnType<typeof ontology>) => void
    let resolveNew!: (value: ReturnType<typeof ontology>) => void
    vi.mocked(api.getAthenaOntology)
      .mockReturnValueOnce(new Promise((resolve) => { resolveOld = resolve }))
      .mockReturnValueOnce(new Promise((resolve) => { resolveNew = resolve }))
    const store = useAthenaStore()

    const oldLoad = store.loadOntology('project-1')
    store.reset('project-1')
    const newLoad = store.loadOntology('project-1')

    resolveNew(ontology(2))
    await newLoad
    expect(store.ontology).toEqual(ontology(2))

    resolveOld(ontology(1))
    await oldLoad
    expect(store.ontology).toEqual(ontology(2))
  })

  it('prevents stale same-project consistency checks from overwriting issues after reset', async () => {
    const oldCheck = createDeferred<unknown>()
    const newCheck = createDeferred<unknown>()
    vi.mocked(api.runAthenaConsistencyCheck)
      .mockReturnValueOnce(oldCheck.promise)
      .mockReturnValueOnce(newCheck.promise)
    vi.mocked(api.getConsistencyIssues)
      .mockResolvedValueOnce([{ severity: 'error', description: 'new issue' }])
      .mockResolvedValueOnce([{ severity: 'error', description: 'old issue' }])
    const store = useAthenaStore()

    const oldRun = store.runConsistencyCheck('project-1', 1)
    store.reset('project-1')
    const newRun = store.runConsistencyCheck('project-1', 2)

    newCheck.resolve({})
    await newRun
    expect(store.consistencyIssues).toEqual([{ severity: 'error', description: 'new issue' }])

    oldCheck.resolve({})
    await oldRun
    expect(store.consistencyIssues).toEqual([{ severity: 'error', description: 'new issue' }])
  })

  it('tracks loading while a consistency check is running', async () => {
    const check = createDeferred<unknown>()
    vi.mocked(api.runAthenaConsistencyCheck).mockReturnValue(check.promise)
    vi.mocked(api.getConsistencyIssues).mockResolvedValue([])
    const store = useAthenaStore()

    const pending = store.runConsistencyCheck('project-1', 1)

    expect(store.loading).toBe(true)

    check.resolve({})
    await pending

    expect(store.loading).toBe(false)
  })

  it('records the latest successful consistency check when no issues are found', async () => {
    vi.mocked(api.runAthenaConsistencyCheck).mockResolvedValue({ issues: [] })
    vi.mocked(api.getConsistencyIssues).mockResolvedValue([])
    const store = useAthenaStore()

    await store.runConsistencyCheck('project-1', 20)

    expect(store.lastConsistencyCheck).toEqual({ chapterIndex: 20, issueCount: 0 })
  })

  it('records analyze-chapter results so the UI can explain no-op analysis', async () => {
    vi.mocked(api.analyzeAthenaChapter).mockResolvedValue({
      status: 'skipped',
      reason: 'duplicates',
      chapter_index: 20,
      task_id: null,
      proposal_bundle_id: 'bundle-20',
      created: { proposal_items: 0 },
      skipped: { duplicates: 7 },
    })
    vi.mocked(api.getAthenaOntology).mockResolvedValue(ontology())
    const store = useAthenaStore()

    await store.analyzeChapter('project-1', 20)

    expect(store.lastAnalyzeChapterResult).toEqual({
      status: 'skipped',
      reason: 'duplicates',
      chapter_index: 20,
      task_id: null,
      proposal_bundle_id: 'bundle-20',
      created: { proposal_items: 0 },
      skipped: { duplicates: 7 },
    })
  })
})
