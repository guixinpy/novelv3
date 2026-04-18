// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatWorkspace from './ChatWorkspace.vue'
import ChatMessage from '../ChatMessage.vue'

function mountWorkspace(inputMessages: any[] = []) {
  return mount(ChatWorkspace, {
    props: {
      project: {
        name: '测试项目',
        genre: '奇幻',
        current_word_count: 1024,
        status: 'draft',
      },
      tabs: [],
      panel: 'overview',
      mode: 'auto',
      source: 'system',
      reason: '',
      messages: inputMessages,
      diagnosis: {
        missing_items: ['setup', 'storyline', 'outline'],
        completed_items: [],
        suggested_next_step: null,
      },
      pendingAction: null,
      loading: false,
    },
  })
}

describe('ChatWorkspace slash commands UI', () => {
  it('输入 / 时展示命令菜单', async () => {
    const wrapper = mountWorkspace()
    const input = wrapper.get('input')
    await input.setValue('/')

    expect(wrapper.find('[data-testid="chat-command-menu"]').exists()).toBe(true)
  })

  it('ArrowDown + Enter 会补全为命令头（不自动填参数模板）', async () => {
    const wrapper = mountWorkspace()
    const input = wrapper.get('input')

    await input.setValue('/')
    await input.trigger('keydown', { key: 'ArrowDown' })
    await input.trigger('keydown', { key: 'Enter' })

    expect((input.element as HTMLInputElement).value).toBe('/compact ')
    expect(wrapper.emitted('send')).toBeUndefined()
  })

  it('不再渲染旧 QuickActions 按钮文本', () => {
    const wrapper = mountWorkspace()

    expect(wrapper.text()).not.toContain('生成设定')
    expect(wrapper.text()).not.toContain('生成故事线')
    expect(wrapper.text()).not.toContain('生成大纲')
  })
})

describe('ChatMessage summary card', () => {
  it('summary 默认折叠，点击后展开正文', async () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'summary',
          content: '第一段摘要\n第二段摘要',
          meta: { command: 'compact' },
        },
        isLatest: true,
        loading: false,
      },
    })

    expect(wrapper.find('[data-testid="chat-summary-body"]').exists()).toBe(false)

    await wrapper.get('[data-testid="chat-summary-toggle"]').trigger('click')

    expect(wrapper.get('[data-testid="chat-summary-body"]').text()).toContain('第一段摘要')
  })
})
