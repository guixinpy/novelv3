// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { mount, type VueWrapper, type DOMWrapper } from '@vue/test-utils'
import ChatWorkspace from './ChatWorkspace.vue'
import ChatMessage from '../ChatMessage.vue'

const mountedWrappers: VueWrapper[] = []

function mountWorkspace(inputMessages: any[] = []): VueWrapper {
  const wrapper = mount(ChatWorkspace, {
    attachTo: document.body,
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
  mountedWrappers.push(wrapper)
  return wrapper
}

afterEach(() => {
  while (mountedWrappers.length) {
    mountedWrappers.pop()?.unmount()
  }
  document.body.innerHTML = ''
})

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

  it('鼠标点选命令后输入框保持焦点并可继续输入参数', async () => {
    const wrapper = mountWorkspace()
    const input = wrapper.get('input')
    await input.setValue('/s')

    const setupItem = wrapper
      .findAll('[data-testid="chat-command-menu"] button')
      .find((item: DOMWrapper<Element>) => item.text().includes('/setup'))
    expect(setupItem).toBeDefined()

    ;(input.element as HTMLInputElement).blur()
    expect(document.activeElement).not.toBe(input.element)

    await setupItem!.trigger('click')

    expect((input.element as HTMLInputElement).value).toBe('/setup ')
    expect(document.activeElement).toBe(input.element)
  })

  it('IME 组合输入阶段按 Enter 不触发命令补全或发送', async () => {
    const wrapper = mountWorkspace()
    const input = wrapper.get('input')

    await input.setValue('/')
    await input.trigger('keydown', { key: 'Enter', keyCode: 229, isComposing: true })
    expect((input.element as HTMLInputElement).value).toBe('/')
    expect(wrapper.emitted('send')).toBeUndefined()

    await input.setValue('中文输入中')
    await input.trigger('keydown', { key: 'Enter', keyCode: 229, isComposing: true })
    expect(wrapper.emitted('send')).toBeUndefined()
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
