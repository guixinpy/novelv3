// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ModelTraceDrawer from './ModelTraceDrawer.vue'
import TraceSummary from './TraceSummary.vue'
import { api } from '../../api/client'
import { useModelTraceStore } from '../../stores/modelTraces'

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

function createPromptTraceDetail() {
  return {
    ...createTraceDetail(),
    prompt_metadata: {
      prompt_id: 'chapter.generate',
      prompt_version: 'v1',
      template_name: 'generate_chapter',
      template_hash: 'sha256:abcdef1234567890fedcba',
    },
    prompt_budget: {
      max_context_chars: 24000,
      included_blocks: 1,
      omitted_blocks: 2,
      omitted_block_keys: ['world-history', 'old-outline'],
      truncated_blocks: ['chapter-summary'],
    },
    context_blocks: [
      {
        key: 'chapter-summary',
        kind: 'summary',
        title: '前三章摘要',
        content: '主角抵达雾港，遇见旧友。',
        sources: [],
        char_count: 13,
        token_estimate: 9,
        original_char_count: 5000,
        truncated: true,
      },
    ],
    trace_metadata: {
      provider: 'deepseek',
      prompt_id: 'chapter.generate',
      prompt_version: 'v1',
      template_name: 'generate_chapter',
      template_hash: 'sha256:abcdef1234567890fedcba',
      budget: {
        max_context_chars: 24000,
        included_blocks: 1,
        omitted_blocks: 2,
        omitted_block_keys: ['world-history', 'old-outline'],
        truncated_blocks: ['chapter-summary'],
      },
    },
  }
}

function sectionText(selector: string) {
  const section = document.body.querySelector(selector)
  expect(section).not.toBeNull()
  return section?.textContent || ''
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

  it('渲染 typed prompt metadata，不需要用户读取 raw JSON', async () => {
    vi.mocked(api.getModelCallTrace).mockResolvedValue(createPromptTraceDetail())

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

    const summaryText = wrapper.findComponent(TraceSummary).text()
    expect(summaryText).toContain('Prompt')
    expect(summaryText).toContain('chapter.generate')
    expect(summaryText).toContain('v1')
    expect(summaryText).toContain('generate_chapter')
    expect(summaryText).toContain('sha256:abcdef12')

    wrapper.unmount()
  })

  it('渲染 omitted/truncated budget 和上下文块截断状态', async () => {
    vi.mocked(api.getModelCallTrace).mockResolvedValue(createPromptTraceDetail())

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

    const budgetText = sectionText('[aria-label="Prompt budget"]')
    expect(budgetText).toContain('Included 1')
    expect(budgetText).toContain('Omitted 2')
    expect(budgetText).toContain('world-history')
    expect(budgetText).toContain('old-outline')
    expect(budgetText).toContain('chapter-summary')
    const contextText = sectionText('[aria-label="上下文块"]')
    expect(contextText).toContain('已截断')
    expect(contextText).toContain('原始 5000')

    wrapper.unmount()
  })

  it('typed 字段缺失时从 trace_metadata fallback 渲染 prompt 信息', async () => {
    const detail = createPromptTraceDetail()
    delete (detail as any).prompt_metadata
    delete (detail as any).prompt_budget
    vi.mocked(api.getModelCallTrace).mockResolvedValue(detail)

    const wrapper = mount(ModelTraceDrawer, {
      props: {
        projectId: 'project-1',
        traceId: 'trace-legacy',
        open: true,
      },
      attachTo: document.body,
    })

    await flushPromises()
    await wrapper.vm.$nextTick()

    const summaryText = wrapper.findComponent(TraceSummary).text()
    expect(summaryText).toContain('chapter.generate')
    expect(summaryText).toContain('generate_chapter')
    const budgetText = sectionText('[aria-label="Prompt budget"]')
    expect(budgetText).toContain('world-history')
    expect(budgetText).toContain('chapter-summary')

    wrapper.unmount()
  })

  it('prompt metadata 增强后 raw messages viewer 仍渲染', async () => {
    vi.mocked(api.getModelCallTrace).mockResolvedValue(createPromptTraceDetail())

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

    const rawMessagesText = sectionText('[aria-label="Raw messages"]')
    expect(rawMessagesText).toContain('Raw Messages')
    expect(rawMessagesText).toContain('你是写作助手')
    expect(rawMessagesText).toContain('雾港钟声响起')

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

  it('只显示详情错误，不显示列表加载错误', async () => {
    vi.mocked(api.listModelCallTraces).mockRejectedValueOnce(new Error('list failed'))
    vi.mocked(api.getModelCallTrace).mockResolvedValue(createTraceDetail())

    const store = useModelTraceStore()
    await store.loadList('project-1')

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

    expect(document.body.textContent).not.toContain('list failed')
    expect(document.body.textContent).toContain('前三章摘要')

    wrapper.unmount()
  })

  it('context block content 缺失或非字符串时不崩', async () => {
    vi.mocked(api.getModelCallTrace).mockResolvedValue({
      ...createTraceDetail(),
      context_blocks: [
        {
          key: 'missing-content',
          kind: 'debug',
          title: '缺失内容',
          sources: [],
          char_count: 0,
          token_estimate: 0,
          truncated: false,
        },
        {
          key: 'object-content',
          kind: 'debug',
          title: '对象内容',
          content: { nested: 'value' },
          sources: [],
          char_count: 1,
          token_estimate: 1,
          truncated: false,
        },
      ],
    } as any)

    const wrapper = mount(ModelTraceDrawer, {
      props: {
        projectId: 'project-1',
        traceId: 'trace-malformed',
        open: true,
      },
      attachTo: document.body,
    })

    await flushPromises()
    await wrapper.vm.$nextTick()

    expect(document.body.textContent).toContain('缺失内容')
    expect(document.body.textContent).toContain('对象内容')
    expect(document.body.textContent).toContain('"nested": "value"')

    wrapper.unmount()
  })
})
