import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useModelTraceStore } from './modelTraces'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    listModelCallTraces: vi.fn(),
    getModelCallTrace: vi.fn(),
  },
}))

function createDeferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

function createTrace(id: string, projectId = 'project-1') {
  return {
    id,
    project_id: projectId,
    trace_type: 'hermes.chat',
    status: 'success',
    model: 'deepseek-chat',
    prompt_tokens: 120,
    completion_tokens: 45,
    latency_ms: 900,
    error_message: null,
    dialog_id: 'dialog-1',
    request_message_id: 'msg-request',
    response_message_id: 'msg-response',
    chapter_id: null,
    chapter_index: 3,
    created_at: '2026-04-28T10:00:00Z',
    updated_at: '2026-04-28T10:00:01Z',
  }
}

function createTraceDetail(id: string, projectId = 'project-1') {
  return {
    ...createTrace(id, projectId),
    temperature: 0.7,
    max_tokens: 2048,
    messages: [{ role: 'user', content: '继续写第三章' }],
    context_blocks: [
      {
        key: 'chapter-summary',
        kind: 'summary',
        title: '前三章摘要',
        content: '主角抵达雾港。',
        sources: [],
        char_count: 8,
        token_estimate: 6,
        original_char_count: null,
        truncated: false,
      },
    ],
    trace_metadata: { provider: 'deepseek' },
  }
}

describe('modelTraces store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('loadList() 会合并筛选条件、分页参数，并写入列表结果', async () => {
    vi.mocked(api.listModelCallTraces).mockResolvedValue({
      total: 1,
      items: [createTrace('trace-1')],
    })

    const store = useModelTraceStore()
    store.limit = 10
    store.offset = 20
    await store.loadList('project-1', {
      trace_type: 'hermes.chat',
      chapter_index: 3,
      dialog_id: 'dialog-1',
    })

    expect(api.listModelCallTraces).toHaveBeenCalledWith('project-1', {
      trace_type: 'hermes.chat',
      chapter_index: 3,
      dialog_id: 'dialog-1',
      limit: 10,
      offset: 20,
    })
    expect(store.items).toEqual([createTrace('trace-1')])
    expect(store.total).toBe(1)
    expect(store.filters).toEqual({
      trace_type: 'hermes.chat',
      chapter_index: 3,
      dialog_id: 'dialog-1',
    })
    expect(store.loadingList).toBe(false)
    expect(store.error).toBe('')
  })

  it('selectTrace() 和 openTrace() 会加载详情并记录选中 trace', async () => {
    vi.mocked(api.getModelCallTrace)
      .mockResolvedValueOnce(createTraceDetail('trace-1'))
      .mockResolvedValueOnce(createTraceDetail('trace-2'))

    const store = useModelTraceStore()
    await store.selectTrace('project-1', 'trace-1')
    expect(store.selectedTraceId).toBe('trace-1')
    expect(store.selectedTrace?.id).toBe('trace-1')

    await store.openTrace('project-1', 'trace-2')
    expect(api.getModelCallTrace).toHaveBeenLastCalledWith('project-1', 'trace-2')
    expect(store.selectedTraceId).toBe('trace-2')
    expect(store.selectedTrace?.id).toBe('trace-2')
    expect(store.loadingDetail).toBe(false)
  })

  it('closeTrace() 只关闭详情，reset() 清空全部状态', async () => {
    vi.mocked(api.listModelCallTraces).mockResolvedValue({
      total: 1,
      items: [createTrace('trace-1')],
    })
    vi.mocked(api.getModelCallTrace).mockResolvedValue(createTraceDetail('trace-1'))

    const store = useModelTraceStore()
    await store.loadList('project-1', { trace_type: 'hermes.chat' })
    await store.selectTrace('project-1', 'trace-1')

    store.closeTrace()
    expect(store.selectedTraceId).toBeNull()
    expect(store.selectedTrace).toBeNull()
    expect(store.items).toHaveLength(1)

    store.reset()
    expect(store.items).toEqual([])
    expect(store.total).toBe(0)
    expect(store.error).toBe('')
    expect(store.filters).toEqual({})
    expect(store.limit).toBe(20)
    expect(store.offset).toBe(0)
  })

  it('closeTrace() 会让 pending detail 请求失效，迟到结果不能重新写回详情', async () => {
    const pendingDetail = createDeferred<ReturnType<typeof createTraceDetail>>()
    vi.mocked(api.getModelCallTrace).mockReturnValue(pendingDetail.promise)

    const store = useModelTraceStore()
    const detailPromise = store.selectTrace('project-1', 'trace-pending')

    expect(store.selectedTraceId).toBe('trace-pending')
    expect(store.loadingDetail).toBe(true)

    store.closeTrace()
    expect(store.selectedTraceId).toBeNull()
    expect(store.selectedTrace).toBeNull()
    expect(store.loadingDetail).toBe(false)

    pendingDetail.resolve(createTraceDetail('trace-pending'))
    await detailPromise

    expect(store.selectedTraceId).toBeNull()
    expect(store.selectedTrace).toBeNull()
    expect(store.loadingDetail).toBe(false)
  })

  it('list 和 detail 错误状态相互隔离', async () => {
    vi.mocked(api.listModelCallTraces).mockRejectedValueOnce(new Error('list failed'))
    vi.mocked(api.getModelCallTrace).mockRejectedValueOnce(new Error('detail failed'))

    const store = useModelTraceStore()
    await store.loadList('project-1')

    expect(store.listError).toBe('list failed')
    expect(store.detailError).toBe('')

    await store.selectTrace('project-1', 'trace-failed')

    expect(store.listError).toBe('list failed')
    expect(store.detailError).toBe('detail failed')
    expect(store.error).toBe('detail failed')
  })

  it('迟到的旧项目列表和详情请求不能覆盖当前项目状态', async () => {
    const oldList = createDeferred<{ total: number; items: ReturnType<typeof createTrace>[] }>()
    const newList = createDeferred<{ total: number; items: ReturnType<typeof createTrace>[] }>()
    const oldDetail = createDeferred<ReturnType<typeof createTraceDetail>>()
    const newDetail = createDeferred<ReturnType<typeof createTraceDetail>>()

    vi.mocked(api.listModelCallTraces)
      .mockReturnValueOnce(oldList.promise)
      .mockReturnValueOnce(newList.promise)
    vi.mocked(api.getModelCallTrace)
      .mockReturnValueOnce(oldDetail.promise)
      .mockReturnValueOnce(newDetail.promise)

    const store = useModelTraceStore()
    const oldListPromise = store.loadList('project-old')
    const oldDetailPromise = store.selectTrace('project-old', 'old-trace')
    const newListPromise = store.loadList('project-new')
    const newDetailPromise = store.selectTrace('project-new', 'new-trace')

    newList.resolve({ total: 1, items: [createTrace('new-trace', 'project-new')] })
    newDetail.resolve(createTraceDetail('new-trace', 'project-new'))
    await newListPromise
    await newDetailPromise

    oldList.resolve({ total: 1, items: [createTrace('old-trace', 'project-old')] })
    oldDetail.resolve(createTraceDetail('old-trace', 'project-old'))
    await oldListPromise
    await oldDetailPromise

    expect(store.items).toEqual([createTrace('new-trace', 'project-new')])
    expect(store.selectedTraceId).toBe('new-trace')
    expect(store.selectedTrace?.project_id).toBe('project-new')
    expect(store.loadingList).toBe(false)
    expect(store.loadingDetail).toBe(false)
  })
})
