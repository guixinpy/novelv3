// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ModelTraceDrawer from './ModelTraceDrawer.vue'
import { api } from '../../api/client'

vi.mock('../../api/client', () => ({
  api: {
    listModelCallTraces: vi.fn(),
    getModelCallTrace: vi.fn(),
  },
}))

function flushPromises() {
  return new Promise((resolve) => setTimeout(resolve, 0))
}

function createTraceDetail() {
  return {
    id: 'trace-1',
    project_id: 'project-1',
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
    temperature: 0.7,
    max_tokens: 2048,
    messages: [
      { role: 'system', content: '你是写作助手。' },
      { role: 'user', content: '继续写第三章。' },
      { role: 'assistant', content: '雾港钟声响起。' },
    ],
    context_blocks: [
      {
        key: 'chapter-summary',
        kind: 'summary',
        title: '前三章摘要',
        content: '主角抵达雾港，遇见旧友。',
        sources: [
          {
            source_type: 'chapter',
            source_id: 'chapter-2',
            label: '第二章',
            chapter_index: 2,
            source_ref: 'chapter.2',
            title: '雾港',
            metadata: { confidence: 0.9 },
          },
        ],
        char_count: 13,
        token_estimate: 9,
        original_char_count: null,
        truncated: false,
      },
    ],
    trace_metadata: { provider: 'deepseek' },
  }
}

describe('ModelTraceDrawer', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.resetAllMocks()
  })

  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('open + traceId 时触发详情加载，并渲染摘要、上下文块和 raw messages', async () => {
    vi.mocked(api.getModelCallTrace).mockResolvedValue(createTraceDetail())

    const wrapper = mount(ModelTraceDrawer, {
      props: {
        projectId: 'project-1',
        traceId: 'trace-1',
        open: true,
      },
      attachTo: document.body,
    })

    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(api.getModelCallTrace).toHaveBeenCalledWith('project-1', 'trace-1')
    expect(document.body.textContent).toContain('hermes.chat')
    expect(document.body.textContent).toContain('前三章摘要')
    expect(document.body.textContent).toContain('主角抵达雾港')
    expect(document.body.textContent).toContain('第二章')
    expect(document.body.textContent).toContain('你是写作助手')
    expect(document.body.textContent).toContain('雾港钟声响起')

    wrapper.unmount()
  })

  it('无详情、加载中、错误态都不崩', async () => {
    let rejectDetail!: (reason?: unknown) => void
    vi.mocked(api.getModelCallTrace).mockReturnValue(new Promise((_, reject) => {
      rejectDetail = reject
    }))

    const wrapper = mount(ModelTraceDrawer, {
      props: {
        projectId: 'project-1',
        traceId: 'trace-err',
        open: true,
      },
      attachTo: document.body,
    })

    await wrapper.vm.$nextTick()
    expect(document.body.textContent).toContain('加载')

    rejectDetail(new Error('detail failed'))
    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(document.body.textContent).toContain('detail failed')

    await wrapper.setProps({ traceId: null })
    expect(document.body.textContent).not.toContain('detail failed')

    wrapper.unmount()
  })
})
