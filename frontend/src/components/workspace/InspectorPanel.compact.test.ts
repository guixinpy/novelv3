// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import type { WorkspacePanel } from '../../api/types'
import InspectorPanel from './InspectorPanel.vue'
import { getWorkspaceTabs } from './workspaceMeta'

const mountedWrappers: VueWrapper[] = []

function mountInspector(props: Partial<Record<string, unknown>> = {}) {
  const wrapper = mount(InspectorPanel, {
    attachTo: document.body,
    props: {
      project: {
        name: '植化尸潮',
        genre: '科幻/末世',
        current_word_count: 0,
        status: 'outline_generated',
      },
      projectId: 'project-1',
      tabs: getWorkspaceTabs(),
      panel: 'setup' as WorkspacePanel,
      mode: 'auto',
      lockedPanel: null,
      source: 'user',
      reason: '你切换到设定',
      diagnosis: null,
      setup: null,
      storyline: null,
      outline: null,
      chapters: [],
      selectedChapter: null,
      topology: null,
      versions: [],
      ...props,
    },
    global: {
      stubs: {
        OverviewTab: { template: '<div data-testid="overview-tab-stub" />' },
        SetupTab: { template: '<div data-testid="setup-tab-stub" />' },
        StorylineTab: { template: '<div data-testid="storyline-tab-stub" />' },
        OutlineTab: { template: '<div data-testid="outline-tab-stub" />' },
        ContentTab: { template: '<div data-testid="content-tab-stub" />' },
        TopologyTab: { template: '<div data-testid="topology-tab-stub" />' },
        VersionsTab: { template: '<div data-testid="versions-tab-stub" />' },
        PreferencesTab: { template: '<div data-testid="preferences-tab-stub" />' },
      },
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

describe('InspectorPanel compact header', () => {
  it('只展示主线 tab，低频项收纳进更多菜单', async () => {
    const wrapper = mountInspector()

    const primaryTabs = wrapper.get('[data-testid="inspector-primary-tabs"]')
    expect(primaryTabs.text()).toContain('概览')
    expect(primaryTabs.text()).toContain('设定')
    expect(primaryTabs.text()).toContain('故事线')
    expect(primaryTabs.text()).toContain('大纲')
    expect(primaryTabs.text()).toContain('正文')
    expect(primaryTabs.text()).not.toContain('拓扑图')
    expect(primaryTabs.text()).not.toContain('版本历史')
    expect(primaryTabs.text()).not.toContain('偏好设置')

    expect(wrapper.find('[data-testid="inspector-overflow-menu"]').exists()).toBe(false)

    await wrapper.get('[data-testid="inspector-more-toggle"]').trigger('click')

    const overflowMenu = wrapper.get('[data-testid="inspector-overflow-menu"]')
    expect(overflowMenu.text()).toContain('拓扑图')
    expect(overflowMenu.text()).toContain('版本历史')
    expect(overflowMenu.text()).toContain('偏好设置')
  })

  it('移除旧眉标和原因文案，只保留当前面板标题', () => {
    const wrapper = mountInspector({
      panel: 'setup' as WorkspacePanel,
      reason: '你切换到设定',
    })

    const toolbar = wrapper.get('[data-testid="inspector-toolbar"]')
    expect(toolbar.text()).toContain('设定')
    expect(toolbar.text()).not.toContain('Inspector')
    expect(toolbar.text()).not.toContain('你切换到设定')
  })

  it('更多按钮支持 ArrowDown/ArrowUp 打开菜单并聚焦首尾项', async () => {
    const wrapper = mountInspector()
    const toggle = wrapper.get('[data-testid="inspector-more-toggle"]')

    await toggle.trigger('keydown', { key: 'ArrowDown' })
    await wrapper.vm.$nextTick()

    const itemsAfterDown = wrapper.findAll('[role="menuitem"]')
    expect(document.activeElement).toBe(itemsAfterDown[0].element)
    expect(itemsAfterDown[0].text()).toBe('拓扑图')

    await itemsAfterDown[0].trigger('keydown', { key: 'Escape' })
    await wrapper.vm.$nextTick()

    await toggle.trigger('keydown', { key: 'ArrowUp' })
    await wrapper.vm.$nextTick()

    const itemsAfterUp = wrapper.findAll('[role="menuitem"]')
    expect(document.activeElement).toBe(itemsAfterUp[itemsAfterUp.length - 1].element)
    expect(itemsAfterUp[itemsAfterUp.length - 1].text()).toBe('偏好设置')
  })

  it('菜单项支持 ArrowUp/ArrowDown 循环和 Home/End 跳转', async () => {
    const wrapper = mountInspector()
    const toggle = wrapper.get('[data-testid="inspector-more-toggle"]')

    await toggle.trigger('keydown', { key: 'ArrowDown' })
    await wrapper.vm.$nextTick()

    const items = wrapper.findAll('[role="menuitem"]')

    await items[0].trigger('keydown', { key: 'ArrowDown' })
    await wrapper.vm.$nextTick()
    expect(document.activeElement).toBe(items[1].element)

    await items[1].trigger('keydown', { key: 'ArrowUp' })
    await wrapper.vm.$nextTick()
    expect(document.activeElement).toBe(items[0].element)

    await items[0].trigger('keydown', { key: 'ArrowUp' })
    await wrapper.vm.$nextTick()
    expect(document.activeElement).toBe(items[items.length - 1].element)

    await items[items.length - 1].trigger('keydown', { key: 'Home' })
    await wrapper.vm.$nextTick()
    expect(document.activeElement).toBe(items[0].element)

    await items[0].trigger('keydown', { key: 'End' })
    await wrapper.vm.$nextTick()
    expect(document.activeElement).toBe(items[items.length - 1].element)
  })

  it('Escape 会关闭菜单并回到更多按钮，Enter 会选中目标面板', async () => {
    const wrapper = mountInspector()
    const toggle = wrapper.get('[data-testid="inspector-more-toggle"]')

    await toggle.trigger('keydown', { key: 'ArrowDown' })
    await wrapper.vm.$nextTick()

    const items = wrapper.findAll('[role="menuitem"]')
    await items[0].trigger('keydown', { key: 'Escape' })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="inspector-overflow-menu"]').exists()).toBe(false)
    expect(document.activeElement).toBe(toggle.element)

    await toggle.trigger('keydown', { key: 'ArrowDown' })
    await wrapper.vm.$nextTick()

    const reopenedItems = wrapper.findAll('[role="menuitem"]')
    await reopenedItems[1].trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('select-panel')).toEqual([['versions']])
    expect(wrapper.find('[data-testid="inspector-overflow-menu"]').exists()).toBe(false)
  })

  it('Tab 离开菜单时会自动关闭，不形成焦点陷阱', async () => {
    const wrapper = mountInspector()
    const toggle = wrapper.get('[data-testid="inspector-more-toggle"]')

    await toggle.trigger('keydown', { key: 'ArrowDown' })
    await wrapper.vm.$nextTick()

    const items = wrapper.findAll('[role="menuitem"]')
    await items[0].trigger('keydown', { key: 'Tab' })
    await new Promise((resolve) => window.setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[data-testid="inspector-overflow-menu"]').exists()).toBe(false)
  })
})
