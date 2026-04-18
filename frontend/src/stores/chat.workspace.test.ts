import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useChatStore } from './chat'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    getMessages: vi.fn(),
    getDiagnosis: vi.fn(),
    resolveAction: vi.fn(),
    sendChat: vi.fn(),
  },
}))

describe('chat workspace polling', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    vi.resetAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('confirm 后轮询不会因为中途出现其他新消息而提前断开，直到消费到最终完成消息', async () => {
    const store = useChatStore()
    store.projectId = 'project-1'
    store.pendingAction = {
      id: 'action-1',
      type: 'preview_outline',
      description: '生成大纲',
      params: { project_id: 'project-1' },
      requires_confirmation: true,
    }
    store.messages = [
      { role: 'assistant', content: '准备开始。' },
    ]

    vi.mocked(api.resolveAction).mockResolvedValue({
      dialog_state: 'RUNNING',
      message: '操作已确认，正在生成中...',
      action_result: {
        type: 'generate_outline',
        status: 'generating',
        data: { status: 'generating' },
      },
      ui_hint: null,
      refresh_targets: [],
    })
    vi.mocked(api.getDiagnosis).mockResolvedValue({
      missing_items: [],
      completed_items: [],
      suggested_next_step: null,
    })
    vi.mocked(api.getMessages)
      .mockResolvedValueOnce([
        {
          role: 'system',
          content: '操作已确认，正在生成中...',
          action_result: { type: 'generate_outline', status: 'generating' },
          created_at: '2026-04-17T10:00:00Z',
        },
        {
          role: 'user',
          content: '继续聊别的',
          action_result: null,
          created_at: '2026-04-17T10:00:01Z',
        },
        {
          role: 'assistant',
          content: '可以，先继续聊。',
          action_result: null,
          created_at: '2026-04-17T10:00:02Z',
        },
      ])
      .mockResolvedValueOnce([
        {
          role: 'system',
          content: '操作已确认，正在生成中...',
          action_result: { type: 'generate_outline', status: 'generating' },
          created_at: '2026-04-17T10:00:00Z',
        },
        {
          role: 'user',
          content: '继续聊别的',
          action_result: null,
          created_at: '2026-04-17T10:00:01Z',
        },
        {
          role: 'assistant',
          content: '可以，先继续聊。',
          action_result: null,
          created_at: '2026-04-17T10:00:02Z',
        },
        {
          role: 'system',
          content: '大纲生成完成。',
          action_result: { type: 'generate_outline', status: 'success' },
          created_at: '2026-04-17T10:00:03Z',
        },
      ])

    await store.resolveAction('confirm')

    await vi.advanceTimersByTimeAsync(3000)
    expect(api.getMessages).toHaveBeenCalledTimes(1)
    expect(store.messages.some((message) => message.content === '继续聊别的')).toBe(true)
    expect(
      store.messages.some((message) => (message.action_result as { status?: string } | null)?.status === 'success'),
    ).toBe(false)

    await vi.advanceTimersByTimeAsync(3000)
    expect(api.getMessages).toHaveBeenCalledTimes(2)
    expect(
      store.messages.some((message) => (message.action_result as { status?: string } | null)?.status === 'success'),
    ).toBe(true)
  })

  it('后台任务 running 期间 send/quick action 会被 guard 拒绝', async () => {
    const store = useChatStore()
    store.projectId = 'project-1'
    store.pendingAction = {
      id: 'action-1',
      type: 'preview_setup',
      description: '生成设定',
      params: { project_id: 'project-1' },
      requires_confirmation: true,
    }
    store.messages = [
      { role: 'assistant', content: '准备开始。' },
    ]

    vi.mocked(api.resolveAction).mockResolvedValue({
      dialog_state: 'RUNNING',
      message: '操作已确认，正在生成中...',
      action_result: {
        type: 'generate_setup',
        status: 'generating',
        data: { status: 'generating' },
      },
      ui_hint: null,
      refresh_targets: [],
    })
    vi.mocked(api.getDiagnosis).mockResolvedValue({
      missing_items: [],
      completed_items: [],
      suggested_next_step: null,
    })
    vi.mocked(api.getMessages).mockResolvedValue([])

    await store.resolveAction('confirm')

    expect(store.loading).toBe(true)
    await expect(store.sendText('继续补充')).resolves.toBe(null)
    await expect(store.sendButtonAction('preview_outline')).resolves.toBe(null)
    expect(api.sendChat).not.toHaveBeenCalled()
  })

  it('init(A) 后快速 init(B)，A 的迟到历史和诊断不能覆盖 B', async () => {
    const store = useChatStore()

    let resolveHistoryA!: (value: any[]) => void
    let resolveHistoryB!: (value: any[]) => void
    let resolveDiagnosisA!: (value: any) => void
    let resolveDiagnosisB!: (value: any) => void

    vi.mocked(api.getMessages).mockImplementation((projectId: string) => new Promise((resolve) => {
      if (projectId === 'A') {
        resolveHistoryA = resolve
      } else {
        resolveHistoryB = resolve
      }
    }))

    vi.mocked(api.getDiagnosis).mockImplementation((projectId: string) => new Promise((resolve) => {
      if (projectId === 'A') {
        resolveDiagnosisA = resolve
      } else {
        resolveDiagnosisB = resolve
      }
    }))

    store.init('A')
    store.init('B')

    resolveHistoryB([
      {
        role: 'assistant',
        content: 'B 的历史消息',
        action_result: null,
        created_at: '2026-04-17T10:01:00Z',
      },
    ])
    resolveDiagnosisB({
      missing_items: ['content'],
      completed_items: ['setup'],
      suggested_next_step: 'preview_outline',
    })
    await Promise.resolve()
    await Promise.resolve()

    expect(store.projectId).toBe('B')
    expect(store.messages).toEqual([
      {
        role: 'assistant',
        content: 'B 的历史消息',
        message_type: null,
        meta: null,
        pending_action: null,
        diagnosis: null,
        action_result: null,
      },
    ])
    expect(store.diagnosis).toEqual({
      missing_items: ['content'],
      completed_items: ['setup'],
      suggested_next_step: 'preview_outline',
    })

    resolveHistoryA([
      {
        role: 'assistant',
        content: 'A 的迟到消息',
        action_result: null,
        created_at: '2026-04-17T10:00:00Z',
      },
    ])
    resolveDiagnosisA({
      missing_items: [],
      completed_items: ['setup', 'storyline'],
      suggested_next_step: null,
    })
    await Promise.resolve()
    await Promise.resolve()

    expect(store.projectId).toBe('B')
    expect(store.messages).toEqual([
      {
        role: 'assistant',
        content: 'B 的历史消息',
        message_type: null,
        meta: null,
        pending_action: null,
        diagnosis: null,
        action_result: null,
      },
    ])
    expect(store.diagnosis).toEqual({
      missing_items: ['content'],
      completed_items: ['setup'],
      suggested_next_step: 'preview_outline',
    })
  })

  it('项目 A 的 sendText 响应慢，切到 B 后不能把 A 的响应写回当前 store', async () => {
    const store = useChatStore()

    vi.mocked(api.getMessages).mockImplementation((projectId: string) => {
      if (projectId === 'B') {
        return Promise.resolve([
          {
            role: 'assistant',
            content: 'B 的历史消息',
            action_result: null,
            created_at: '2026-04-17T11:00:00Z',
          },
        ])
      }
      return Promise.resolve([])
    })
    vi.mocked(api.getDiagnosis).mockImplementation((projectId: string) => {
      if (projectId === 'B') {
        return Promise.resolve({
          missing_items: ['content'],
          completed_items: ['setup'],
          suggested_next_step: 'preview_outline',
        })
      }
      return Promise.resolve({
        missing_items: [],
        completed_items: [],
        suggested_next_step: null,
      })
    })

    let resolveSendA!: (value: any) => void
    vi.mocked(api.sendChat).mockImplementation(({ project_id }: { project_id: string }) => new Promise((resolve) => {
      if (project_id === 'A') {
        resolveSendA = resolve
      }
    }))

    store.init('A')
    await Promise.resolve()
    await Promise.resolve()

    const sendPromise = store.sendText('A 项目的问题')
    store.init('B')
    await Promise.resolve()
    await Promise.resolve()

    resolveSendA({
      message: 'A 的迟到回复',
      pending_action: null,
      ui_hint: null,
      refresh_targets: [],
      project_diagnosis: {
        missing_items: [],
        completed_items: ['setup', 'storyline'],
        suggested_next_step: null,
      },
    })

    await expect(sendPromise).resolves.toBe(null)
    expect(store.projectId).toBe('B')
    expect(store.messages).toEqual([
      {
        role: 'assistant',
        content: 'B 的历史消息',
        message_type: null,
        meta: null,
        pending_action: null,
        diagnosis: null,
        action_result: null,
      },
    ])
    expect(store.diagnosis).toEqual({
      missing_items: ['content'],
      completed_items: ['setup'],
      suggested_next_step: 'preview_outline',
    })
  })

  it('项目 A 的 resolveAction(confirm) 响应慢，切到 B 后不能在 B 上写回或启动错误轮询', async () => {
    const store = useChatStore()

    vi.mocked(api.getMessages).mockResolvedValue([])
    vi.mocked(api.getDiagnosis).mockResolvedValue({
      missing_items: [],
      completed_items: [],
      suggested_next_step: null,
    })

    store.init('A')
    await Promise.resolve()
    await Promise.resolve()

    store.pendingAction = {
      id: 'action-A',
      type: 'preview_setup',
      description: '生成设定',
      params: { project_id: 'A' },
      requires_confirmation: true,
    }

    let resolveActionA!: (value: any) => void
    vi.mocked(api.resolveAction).mockImplementation(({ action_id }: { action_id: string }) => new Promise((resolve) => {
      if (action_id === 'action-A') {
        resolveActionA = resolve
      }
    }))

    const resolvePromise = store.resolveAction('confirm')
    store.init('B')
    await Promise.resolve()
    await Promise.resolve()

    resolveActionA({
      dialog_state: 'RUNNING',
      message: '操作已确认，正在生成中...',
      action_result: {
        type: 'generate_setup',
        status: 'generating',
        data: { status: 'generating' },
      },
      ui_hint: null,
      refresh_targets: [],
    })

    await expect(resolvePromise).resolves.toBe(null)
    expect(store.projectId).toBe('B')
    expect(store.messages).toEqual([
      { role: 'assistant', content: '你好，我是墨舟，你的长篇写作助手。有什么想聊的？' },
    ])

    await vi.advanceTimersByTimeAsync(3000)
    expect(api.getMessages).toHaveBeenCalledTimes(2)
  })

  it('轮询超时后会恢复可交互状态，不会永久锁死聊天区', async () => {
    const store = useChatStore()
    store.projectId = 'project-1'
    store.pendingAction = {
      id: 'action-timeout',
      type: 'preview_outline',
      description: '生成大纲',
      params: { project_id: 'project-1' },
      requires_confirmation: true,
    }
    store.messages = [
      { role: 'assistant', content: '准备开始。' },
    ]

    vi.mocked(api.resolveAction).mockResolvedValue({
      dialog_state: 'RUNNING',
      message: '操作已确认，正在生成中...',
      action_result: {
        type: 'generate_outline',
        status: 'generating',
        data: { status: 'generating' },
      },
      ui_hint: null,
      refresh_targets: [],
    })
    vi.mocked(api.getDiagnosis).mockResolvedValue({
      missing_items: [],
      completed_items: [],
      suggested_next_step: null,
    })
    vi.mocked(api.getMessages).mockResolvedValue([])

    await store.resolveAction('confirm')
    expect(store.loading).toBe(true)

    await vi.advanceTimersByTimeAsync(3000 * 30)

    expect(store.loading).toBe(false)
    expect(
      store.messages.some((message) => message.content.includes('后台任务状态获取超时')),
    ).toBe(true)
  })

  it('轮询持续异常后也会恢复可交互状态', async () => {
    const store = useChatStore()
    store.projectId = 'project-1'
    store.pendingAction = {
      id: 'action-error',
      type: 'preview_setup',
      description: '生成设定',
      params: { project_id: 'project-1' },
      requires_confirmation: true,
    }
    store.messages = [
      { role: 'assistant', content: '准备开始。' },
    ]

    vi.mocked(api.resolveAction).mockResolvedValue({
      dialog_state: 'RUNNING',
      message: '操作已确认，正在生成中...',
      action_result: {
        type: 'generate_setup',
        status: 'generating',
        data: { status: 'generating' },
      },
      ui_hint: null,
      refresh_targets: [],
    })
    vi.mocked(api.getDiagnosis).mockResolvedValue({
      missing_items: [],
      completed_items: [],
      suggested_next_step: null,
    })
    vi.mocked(api.getMessages).mockRejectedValue(new Error('network down'))

    await store.resolveAction('confirm')
    expect(store.loading).toBe(true)

    await vi.advanceTimersByTimeAsync(3000 * 30)

    expect(store.loading).toBe(false)
    expect(
      store.messages.some((message) => message.content.includes('后台任务状态获取超时')),
    ).toBe(true)
  })

  it('init() 会等待 history/diagnosis 收口，并恢复待确认 pendingAction', async () => {
    const store = useChatStore()

    let resolveHistory!: (value: any[]) => void
    let resolveDiagnosis!: (value: any) => void

    vi.mocked(api.getMessages).mockImplementation(() => new Promise((resolve) => {
      resolveHistory = resolve
    }))
    vi.mocked(api.getDiagnosis).mockImplementation(() => new Promise((resolve) => {
      resolveDiagnosis = resolve
    }))

    let settled = false
    const initPromise = store.init('project-1').then(() => {
      settled = true
    })

    await Promise.resolve()
    expect(settled).toBe(false)

    resolveHistory([
      {
        role: 'assistant',
        content: '已收到你的请求。确认要执行吗？',
        pending_action: {
          id: 'pending-1',
          type: 'preview_setup',
          description: '生成设定',
          params: { project_id: 'project-1' },
          requires_confirmation: true,
        },
        action_result: null,
        created_at: '2026-04-18T00:00:00Z',
      },
    ])
    await Promise.resolve()
    expect(settled).toBe(false)

    resolveDiagnosis({
      missing_items: ['setup'],
      completed_items: [],
      suggested_next_step: 'preview_setup',
    })
    await initPromise

    expect(settled).toBe(true)
    expect(store.messages).toEqual([
      {
        role: 'assistant',
        content: '已收到你的请求。确认要执行吗？',
        message_type: null,
        meta: null,
        pending_action: {
          id: 'pending-1',
          type: 'preview_setup',
          description: '生成设定',
          params: { project_id: 'project-1' },
          requires_confirmation: true,
        },
        diagnosis: null,
        action_result: null,
      },
    ])
    expect(store.pendingAction).toEqual({
      id: 'pending-1',
      type: 'preview_setup',
      description: '生成设定',
      params: { project_id: 'project-1' },
      requires_confirmation: true,
    })
  })

  it('init() 遇到 generating action_result 时会恢复 loading 和轮询', async () => {
    const store = useChatStore()

    vi.mocked(api.getMessages)
      .mockResolvedValueOnce([
        {
          role: 'system',
          content: '操作已确认，正在生成中...',
          action_result: { type: 'generate_setup', status: 'generating' },
          created_at: '2026-04-18T02:00:00Z',
        },
      ])
      .mockResolvedValueOnce([
        {
          role: 'system',
          content: '操作已确认，正在生成中...',
          action_result: { type: 'generate_setup', status: 'generating' },
          created_at: '2026-04-18T02:00:00Z',
        },
        {
          role: 'system',
          content: '设定生成完成。',
          action_result: { type: 'generate_setup', status: 'success' },
          created_at: '2026-04-18T02:00:03Z',
        },
      ])
    vi.mocked(api.getDiagnosis).mockResolvedValue({
      missing_items: [],
      completed_items: ['setup'],
      suggested_next_step: 'preview_storyline',
    })

    await store.init('project-1')

    expect(store.loading).toBe(true)
    expect(store.pendingAction).toBe(null)
    expect(
      store.messages.some((message) => (message.action_result as { status?: string } | null)?.status === 'generating'),
    ).toBe(true)

    await vi.advanceTimersByTimeAsync(3000)

    expect(api.getMessages).toHaveBeenCalledTimes(2)
    expect(store.loading).toBe(false)
    expect(
      store.messages.some((message) => (message.action_result as { status?: string } | null)?.status === 'success'),
    ).toBe(true)
  })

  it('sendCommand(compact) 成功后会重新 loadHistory，而不是只 append 一条消息', async () => {
    const store = useChatStore()
    store.projectId = 'project-1'
    store.messages = [
      { role: 'assistant', content: '旧消息' },
    ]

    vi.mocked(api.sendChat).mockResolvedValue({
      message: '已压缩历史',
      pending_action: null,
      ui_hint: null,
      refresh_targets: [],
      project_diagnosis: {
        missing_items: [],
        completed_items: ['setup'],
        suggested_next_step: null,
      },
    })
    vi.mocked(api.getMessages).mockResolvedValue([
      {
        role: 'system',
        content: '压缩后的历史',
        message_type: 'summary',
        meta: { title: '会话摘要（4条）', compacted_count: 4 },
        created_at: '2026-04-18T01:00:00Z',
      },
    ])

    await store.sendCommand('compact', '', '/compact')

    expect(api.sendChat).toHaveBeenCalledWith({
      project_id: 'project-1',
      input_type: 'command',
      command_name: 'compact',
      command_args: '',
    })
    expect(api.getMessages).toHaveBeenCalledWith('project-1')
    expect(store.messages).toEqual([
      {
        role: 'system',
        content: '压缩后的历史',
        message_type: 'summary',
        meta: { title: '会话摘要（4条）', compacted_count: 4 },
        pending_action: null,
        diagnosis: null,
        action_result: null,
      },
    ])
  })

  it('sendCommand(setup) 会追加 assistant 回执并恢复 pendingAction', async () => {
    const store = useChatStore()
    store.projectId = 'project-1'

    vi.mocked(api.sendChat).mockResolvedValue({
      message: '收到，先给你一版人物与世界设定。',
      pending_action: {
        id: 'pending-setup-1',
        type: 'preview_setup',
        description: '生成设定',
        params: { project_id: 'project-1' },
        requires_confirmation: true,
      },
      ui_hint: null,
      refresh_targets: [],
      project_diagnosis: {
        missing_items: ['storyline'],
        completed_items: ['setup'],
        suggested_next_step: 'preview_storyline',
      },
    })

    await store.sendCommand('setup', '主角是植物学家', '/setup 主角是植物学家')

    expect(api.sendChat).toHaveBeenCalledWith({
      project_id: 'project-1',
      input_type: 'command',
      command_name: 'setup',
      command_args: '主角是植物学家',
    })
    expect(api.getMessages).not.toHaveBeenCalled()
    expect(store.pendingAction).toEqual({
      id: 'pending-setup-1',
      type: 'preview_setup',
      description: '生成设定',
      params: { project_id: 'project-1' },
      requires_confirmation: true,
    })
    expect(store.messages.slice(-2)).toEqual([
      { role: 'user', content: '/setup 主角是植物学家' },
      {
        role: 'assistant',
        content: '收到，先给你一版人物与世界设定。',
        message_type: null,
        meta: null,
        pending_action: {
          id: 'pending-setup-1',
          type: 'preview_setup',
          description: '生成设定',
          params: { project_id: 'project-1' },
          requires_confirmation: true,
        },
        diagnosis: {
          missing_items: ['storyline'],
          completed_items: ['setup'],
          suggested_next_step: 'preview_storyline',
        },
      },
    ])
    expect(store.loading).toBe(false)
  })

  it('sendCommand(compact) 执行成功但历史刷新失败时，会显式提示刷新失败', async () => {
    const store = useChatStore()
    store.projectId = 'project-1'
    store.messages = [
      { role: 'assistant', content: '旧上下文消息' },
    ]

    vi.mocked(api.sendChat).mockResolvedValue({
      message: '已压缩历史',
      pending_action: null,
      ui_hint: null,
      refresh_targets: [],
      project_diagnosis: {
        missing_items: [],
        completed_items: ['setup'],
        suggested_next_step: null,
      },
    })
    vi.mocked(api.getMessages).mockRejectedValue(new Error('history unavailable'))

    await store.sendCommand('compact', '', '/compact')

    expect(store.messages.slice(-1)).toEqual([
      {
        role: 'system',
        content: '命令已执行，但历史刷新失败，请手动刷新。',
      },
    ])
  })

  it('sendCommand(clear) 执行成功但历史刷新失败时，会显式提示刷新失败', async () => {
    const store = useChatStore()
    store.projectId = 'project-1'
    store.messages = [
      { role: 'assistant', content: '旧上下文消息' },
    ]

    vi.mocked(api.sendChat).mockResolvedValue({
      message: '已清空会话',
      pending_action: null,
      ui_hint: null,
      refresh_targets: [],
      project_diagnosis: {
        missing_items: [],
        completed_items: ['setup'],
        suggested_next_step: null,
      },
    })
    vi.mocked(api.getMessages).mockRejectedValue(new Error('history unavailable'))

    await store.sendCommand('clear', '', '/clear')

    expect(store.messages.slice(-1)).toEqual([
      {
        role: 'system',
        content: '命令已执行，但历史刷新失败，请手动刷新。',
      },
    ])
  })
})
