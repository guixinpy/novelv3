import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useAthenaStore } from './athena'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    sendAthenaChat: vi.fn(),
    getAthenaMessages: vi.fn(),
    getAthenaEvolutionProposals: vi.fn(),
    getAthenaOntology: vi.fn(),
    getAthenaState: vi.fn(),
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

function message(content: string) {
  return {
    id: content,
    role: 'assistant' as const,
    content,
    message_type: null,
    meta: null,
    pending_action: null,
    diagnosis: null,
    action_result: null,
    trace_id: null,
    created_at: '2026-04-26T00:00:00Z',
  }
}

function proposalBundle(projectId: string, id: string) {
  return {
    id,
    project_id: projectId,
    project_profile_version_id: `profile-${projectId}`,
    profile_version: 1,
    parent_bundle_id: null,
    bundle_status: 'pending',
    title: id,
    summary: '',
    created_by: 'athena.dialog',
    created_at: '2026-04-26T00:00:00Z',
    updated_at: '2026-04-26T00:00:00Z',
  }
}

describe('athena chat store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  it('refreshes proposals after Athena chat creates a proposal', async () => {
    vi.mocked(api.sendAthenaChat).mockResolvedValue({
      message: '已创建待审提案',
      pending_action: null,
      ui_hint: null,
      refresh_targets: ['proposals'],
      project_diagnosis: {
        missing_items: [],
        completed_items: [],
        suggested_next_step: null,
      },
    })
    vi.mocked(api.getAthenaMessages).mockResolvedValue([])
    vi.mocked(api.getAthenaEvolutionProposals).mockResolvedValue({
      items: [
        {
          id: 'bundle-1',
          project_id: 'project-1',
          project_profile_version_id: 'profile-1',
          profile_version: 1,
          parent_bundle_id: null,
          bundle_status: 'pending',
          title: 'Athena 对话待审世界更新',
          summary: '',
          created_by: 'athena.dialog',
          created_at: '2026-04-26T00:00:00Z',
          updated_at: '2026-04-26T00:00:00Z',
        },
      ],
      total: 1,
      offset: 0,
      limit: 20,
    })
    const store = useAthenaStore()

    await store.sendChat('project-1', '请更新世界模型')

    expect(api.sendAthenaChat).toHaveBeenCalledWith('project-1', '请更新世界模型')
    expect(api.getAthenaMessages).toHaveBeenCalledWith('project-1', { limit: 80 })
    expect(api.getAthenaEvolutionProposals).toHaveBeenCalledWith('project-1', undefined)
    expect(store.proposals?.total).toBe(1)
  })

  it('keeps newer project chat state when an older sendChat resolves later', async () => {
    const sendA = createDeferred<any>()
    const sendB = createDeferred<any>()
    const messagesA = createDeferred<any[]>()
    const messagesB = createDeferred<any[]>()
    const proposalsA = createDeferred<any>()
    vi.mocked(api.sendAthenaChat)
      .mockReturnValueOnce(sendA.promise)
      .mockReturnValueOnce(sendB.promise)
    vi.mocked(api.getAthenaMessages)
      .mockReturnValueOnce(messagesB.promise)
      .mockReturnValueOnce(messagesA.promise)
    vi.mocked(api.getAthenaEvolutionProposals).mockReturnValueOnce(proposalsA.promise)
    const store = useAthenaStore()

    const sendAPromise = store.sendChat('A', 'A text')
    const sendBPromise = store.sendChat('B', 'B text')

    sendB.resolve({
      message: 'B done',
      pending_action: null,
      ui_hint: null,
      refresh_targets: [],
      project_diagnosis: { missing_items: [], completed_items: [], suggested_next_step: null },
    })
    messagesB.resolve([message('B history')])
    await sendBPromise
    expect(store.messages).toEqual([message('B history')])
    expect(store.chatLoading).toBe(false)

    sendA.resolve({
      message: 'A done',
      pending_action: null,
      ui_hint: null,
      refresh_targets: ['proposals'],
      project_diagnosis: { missing_items: [], completed_items: [], suggested_next_step: null },
    })
    messagesA.resolve([message('A stale history')])
    proposalsA.resolve({
      items: [
        {
          id: 'bundle-A',
          project_id: 'A',
          project_profile_version_id: 'profile-A',
          profile_version: 1,
          parent_bundle_id: null,
          bundle_status: 'pending',
          title: 'stale',
          summary: '',
          created_by: 'athena.dialog',
          created_at: '2026-04-26T00:00:00Z',
          updated_at: '2026-04-26T00:00:00Z',
        },
      ],
      total: 1,
      offset: 0,
      limit: 20,
    })
    await sendAPromise

    expect(store.messages).toEqual([message('B history')])
    expect(store.proposals).toBeNull()
    expect(store.chatLoading).toBe(false)
  })

  it('keeps loaded project messages when loadMessages switches projects during sendChat', async () => {
    const sendA = createDeferred<any>()
    const messagesB = createDeferred<any[]>()
    const messagesA = createDeferred<any[]>()
    const proposalsA = createDeferred<any>()
    vi.mocked(api.sendAthenaChat).mockReturnValueOnce(sendA.promise)
    vi.mocked(api.getAthenaMessages)
      .mockReturnValueOnce(messagesB.promise)
      .mockReturnValueOnce(messagesA.promise)
    vi.mocked(api.getAthenaEvolutionProposals).mockReturnValueOnce(proposalsA.promise)
    const store = useAthenaStore()

    const sendAPromise = store.sendChat('A', 'A text')
    const loadBPromise = store.loadMessages('B')

    messagesB.resolve([message('B history')])
    await loadBPromise
    expect(store.messages).toEqual([message('B history')])
    expect(store.chatLoading).toBe(true)

    sendA.resolve({
      message: 'A done',
      pending_action: null,
      ui_hint: null,
      refresh_targets: ['proposals'],
      project_diagnosis: { missing_items: [], completed_items: [], suggested_next_step: null },
    })
    messagesA.resolve([message('A stale history')])
    proposalsA.resolve({
      items: [proposalBundle('A', 'bundle-A')],
      total: 1,
      offset: 0,
      limit: 20,
    })
    await sendAPromise

    expect(store.messages).toEqual([message('B history')])
    expect(store.proposals).toBeNull()
    expect(store.chatLoading).toBe(false)
  })

  it('keeps same-project sendChat refresh active when loadMessages runs during sendChat', async () => {
    const sendA = createDeferred<any>()
    const loadMessagesA = createDeferred<any[]>()
    const sendMessagesA = createDeferred<any[]>()
    const proposalsA = createDeferred<any>()
    vi.mocked(api.sendAthenaChat).mockReturnValueOnce(sendA.promise)
    vi.mocked(api.getAthenaMessages)
      .mockReturnValueOnce(loadMessagesA.promise)
      .mockReturnValueOnce(sendMessagesA.promise)
    vi.mocked(api.getAthenaEvolutionProposals).mockReturnValueOnce(proposalsA.promise)
    const store = useAthenaStore()

    const sendAPromise = store.sendChat('A', 'A text')
    const loadAPromise = store.loadMessages('A')

    loadMessagesA.resolve([message('A interim history')])
    await loadAPromise
    expect(store.messages).toEqual([message('A interim history')])
    expect(store.chatLoading).toBe(true)

    sendA.resolve({
      message: 'A done',
      pending_action: null,
      ui_hint: null,
      refresh_targets: ['proposals'],
      project_diagnosis: { missing_items: [], completed_items: [], suggested_next_step: null },
    })
    sendMessagesA.resolve([message('A send history')])
    proposalsA.resolve({
      items: [proposalBundle('A', 'bundle-A')],
      total: 1,
      offset: 0,
      limit: 20,
    })
    await sendAPromise

    expect(store.messages).toEqual([message('A send history')])
    expect(store.proposals?.items).toEqual([proposalBundle('A', 'bundle-A')])
    expect(store.chatLoading).toBe(false)
  })

  it('prevents same-project loadMessages from overwriting a completed sendChat refresh', async () => {
    const sendA = createDeferred<any>()
    const loadMessagesA = createDeferred<any[]>()
    const sendMessagesA = createDeferred<any[]>()
    vi.mocked(api.sendAthenaChat).mockReturnValueOnce(sendA.promise)
    vi.mocked(api.getAthenaMessages)
      .mockReturnValueOnce(loadMessagesA.promise)
      .mockReturnValueOnce(sendMessagesA.promise)
    const store = useAthenaStore()

    const sendAPromise = store.sendChat('A', 'A text')
    const loadAPromise = store.loadMessages('A')

    sendA.resolve({
      message: 'A done',
      pending_action: null,
      ui_hint: null,
      refresh_targets: [],
      project_diagnosis: { missing_items: [], completed_items: [], suggested_next_step: null },
    })
    sendMessagesA.resolve([message('A send history')])
    await sendAPromise
    expect(store.messages).toEqual([message('A send history')])

    loadMessagesA.resolve([message('A stale load history')])
    await loadAPromise

    expect(store.messages).toEqual([message('A send history')])
    expect(store.chatLoading).toBe(false)
  })

  it('keeps newer project messages when an older loadMessages resolves later', async () => {
    const messagesA = createDeferred<any[]>()
    const messagesB = createDeferred<any[]>()
    vi.mocked(api.getAthenaMessages)
      .mockReturnValueOnce(messagesA.promise)
      .mockReturnValueOnce(messagesB.promise)
    const store = useAthenaStore()

    const loadAPromise = store.loadMessages('A')
    const loadBPromise = store.loadMessages('B')

    messagesB.resolve([message('B history')])
    await loadBPromise
    expect(store.messages).toEqual([message('B history')])

    messagesA.resolve([message('A stale history')])
    await loadAPromise

    expect(store.messages).toEqual([message('B history')])
  })
})
