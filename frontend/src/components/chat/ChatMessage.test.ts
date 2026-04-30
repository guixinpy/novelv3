// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ChatMessage from './ChatMessage.vue'

describe('ChatMessage', () => {
  it('emits openTrace when clicking assistant trace button', async () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          content: '这是带模型调用上下文的回复。',
          trace_id: 'trace-1',
        },
        isLatest: false,
        loading: false,
      },
    })

    await wrapper.get('[data-testid="open-trace"]').trigger('click')

    expect(wrapper.emitted('openTrace')).toEqual([['trace-1']])
  })

  it('does not render trace button without trace id', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          content: '这是普通回复。',
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.find('[data-testid="open-trace"]').exists()).toBe(false)
  })

  it('does not render trace button for user messages', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'user',
          content: '用户消息不显示上下文按钮。',
          trace_id: 'trace-user',
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.find('[data-testid="open-trace"]').exists()).toBe(false)
  })

  it('emits openTrace for system action messages with trace id', async () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          content: '设定生成完成。',
          trace_id: 'trace-system',
          action_result: { type: 'generate_setup', status: 'success' },
        },
        isLatest: false,
        loading: false,
      },
    })

    await wrapper.get('[data-testid="open-trace"]').trigger('click')

    expect(wrapper.emitted('openTrace')).toEqual([['trace-system']])
  })

  it('renders chapter generation action results with a user-facing label', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '第1章正文生成完成。',
          action_result: { type: 'generate_chapter', status: 'success' },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('生成正文执行成功')
    expect(wrapper.text()).not.toContain('generate_chapter')
  })

  it('renders generating action progress without repeating the action verb', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '操作已确认，正在生成中...',
          action_result: { type: 'generate_setup', status: 'generating' },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('设定生成中...')
    expect(wrapper.text()).not.toContain('生成设定生成中')
  })
})
