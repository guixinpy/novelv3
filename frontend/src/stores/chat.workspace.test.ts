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
    vi.clearAllMocks()
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
})
