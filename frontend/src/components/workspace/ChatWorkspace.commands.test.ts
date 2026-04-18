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

function mountWorkspaceWithProps(props: Record<string, unknown>): VueWrapper {
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
      messages: [],
      diagnosis: {
        missing_items: ['setup', 'storyline', 'outline'],
        completed_items: [],
        suggested_next_step: null,
      },
      pendingAction: null,
      loading: false,
      ...props,
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

  it('命令菜单展示命令名、说明和示例', async () => {
    const wrapper = mountWorkspace()
    const input = wrapper.get('input')
    await input.setValue('/s')

    const setupItem = wrapper
      .findAll('[data-testid="chat-command-menu"] button')
      .find((item: DOMWrapper<Element>) => item.text().includes('/setup'))

    expect(setupItem).toBeDefined()
    expect(setupItem!.text()).toContain('生成或更新世界设定')
    expect(setupItem!.text()).toContain('/setup 主角是植物学家')
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

  it('pendingAction 存在时仍允许输入并发送 /clear', async () => {
    const wrapper = mountWorkspaceWithProps({
      pendingAction: {
        id: 'pending-1',
        type: 'preview_setup',
        description: '生成设定',
        params: { project_id: 'project-1' },
        requires_confirmation: true,
      },
    })
    const input = wrapper.get('input')

    expect(input.attributes('disabled')).toBeUndefined()

    await input.setValue('/clear')
    await input.trigger('keydown', { key: 'Enter' })

    expect(wrapper.emitted('send')).toEqual([['/clear']])
  })

  it('pendingAction 存在时普通文本和其它命令继续受限', async () => {
    const wrapper = mountWorkspaceWithProps({
      pendingAction: {
        id: 'pending-1',
        type: 'preview_setup',
        description: '生成设定',
        params: { project_id: 'project-1' },
        requires_confirmation: true,
      },
    })
    const input = wrapper.get('input')

    await input.setValue('继续聊')
    await input.trigger('keydown', { key: 'Enter' })
    await input.setValue('/setup 主角是植物学家')
    await input.trigger('keydown', { key: 'Enter' })

    expect(wrapper.emitted('send')).toBeUndefined()
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
  it('summary 默认折叠，使用 meta 展示标题与压缩条数，点击后展开正文', async () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'assistant',
          message_type: 'summary',
          content: '第一段摘要\n第二段摘要',
          meta: { title: '会话摘要（4条）', compacted_count: 4 },
        },
        isLatest: true,
        loading: false,
      },
    })

    expect(wrapper.find('[data-testid="chat-summary-body"]').exists()).toBe(false)
    expect(wrapper.get('[data-testid="chat-summary-toggle"]').text()).toContain('会话摘要（4条）')
    expect(wrapper.get('[data-testid="chat-summary-toggle"]').text()).toContain('已压缩 4 条消息')

    await wrapper.get('[data-testid="chat-summary-toggle"]').trigger('click')

    expect(wrapper.get('[data-testid="chat-summary-body"]').text()).toContain('第一段摘要')
  })
})
