// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import type { SetupData } from '../../api/types'
import SetupTab from './SetupTab.vue'

const mountedWrappers: VueWrapper[] = []

const setupFixture: SetupData = {
  id: 'setup-1',
  project_id: 'project-1',
  status: 'ready',
  created_at: '2026-04-18T00:00:00Z',
  updated_at: '2026-04-18T00:00:00Z',
  characters: [
    {
      name: '沈砚',
      background: '旧城档案馆的修复员',
      personality: '克制',
      goals: '找回失落档案',
      age: 28,
      gender: 'male',
      character_status: 'alive',
    },
    {
      name: '周岚',
      background: '边境调查员',
      personality: '直接',
      goals: '封锁裂隙',
      age: 26,
      gender: 'female',
      character_status: 'alive',
    },
  ],
  world_building: {
    background: '灾后第三纪元',
    geography: '群岛与雾海',
    society: '城邦联盟',
    rules: '记忆税制度',
    atmosphere: '冷峻压抑',
  },
  core_concept: {
    theme: '记忆与身份',
    premise: '记忆能被征税和买卖',
    hook: '主角记忆在被人篡改',
    unique_selling_point: '档案修复决定现实',
  },
}

function mountSetupTab(setup: SetupData | null = setupFixture) {
  const wrapper = mount(SetupTab, {
    attachTo: document.body,
    props: { setup },
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

describe('SetupTab structured sections', () => {
  it('渲染二级 tabs，并默认激活 characters', () => {
    const wrapper = mountSetupTab()

    const tablist = wrapper.get('[data-testid="setup-section-tabs"]')
    const charactersTab = wrapper.get('[data-testid="setup-section-tab-characters"]')
    const worldTab = wrapper.get('[data-testid="setup-section-tab-world"]')
    const conceptTab = wrapper.get('[data-testid="setup-section-tab-concept"]')
    const charactersPanel = wrapper.get('#setup-section-panel-characters')
    const worldPanel = wrapper.get('#setup-section-panel-world')
    const conceptPanel = wrapper.get('#setup-section-panel-concept')

    expect(tablist.attributes('role')).toBe('tablist')
    expect(charactersTab.attributes('role')).toBe('tab')
    expect(worldTab.attributes('role')).toBe('tab')
    expect(conceptTab.attributes('role')).toBe('tab')
    expect(charactersTab.attributes('aria-selected')).toBe('true')
    expect(charactersTab.attributes('tabindex')).toBe('0')
    expect(worldTab.attributes('aria-selected')).toBe('false')
    expect(worldTab.attributes('tabindex')).toBe('-1')
    expect(conceptTab.attributes('aria-selected')).toBe('false')
    expect(charactersPanel.attributes('role')).toBe('tabpanel')
    expect(worldPanel.attributes('role')).toBe('tabpanel')
    expect(conceptPanel.attributes('role')).toBe('tabpanel')
    expect(charactersTab.attributes('aria-controls')).toBe('setup-section-panel-characters')
    expect(worldTab.attributes('aria-controls')).toBe('setup-section-panel-world')
    expect(conceptTab.attributes('aria-controls')).toBe('setup-section-panel-concept')
    expect(charactersPanel.attributes('aria-labelledby')).toBe(charactersTab.attributes('id'))
    expect(worldPanel.attributes('aria-labelledby')).toBe(worldTab.attributes('id'))
    expect(conceptPanel.attributes('aria-labelledby')).toBe(conceptTab.attributes('id'))
    expect(charactersPanel.attributes('hidden')).toBeUndefined()
    expect(worldPanel.attributes('hidden')).toBe('')
    expect(conceptPanel.attributes('hidden')).toBe('')
  })

  it('点击和键盘操作可切换 active section', async () => {
    const wrapper = mountSetupTab()
    const charactersTab = wrapper.get('[data-testid="setup-section-tab-characters"]')
    const worldTab = wrapper.get('[data-testid="setup-section-tab-world"]')
    const conceptTab = wrapper.get('[data-testid="setup-section-tab-concept"]')
    const charactersPanel = () => wrapper.get('#setup-section-panel-characters')
    const worldPanel = () => wrapper.get('#setup-section-panel-world')
    const conceptPanel = () => wrapper.get('#setup-section-panel-concept')

    await worldTab.trigger('click')
    expect(worldTab.attributes('aria-selected')).toBe('true')
    expect(worldTab.attributes('tabindex')).toBe('0')
    expect(charactersTab.attributes('aria-selected')).toBe('false')
    expect(worldPanel().attributes('hidden')).toBeUndefined()
    expect(charactersPanel().attributes('hidden')).toBe('')

    await worldTab.trigger('keydown', { key: 'ArrowRight' })
    await nextTick()
    expect(conceptTab.attributes('aria-selected')).toBe('true')
    expect(conceptTab.attributes('tabindex')).toBe('0')
    expect(worldTab.attributes('tabindex')).toBe('-1')
    expect(document.activeElement).toBe(conceptTab.element)
    expect(conceptPanel().attributes('hidden')).toBeUndefined()

    await conceptTab.trigger('keydown', { key: 'ArrowLeft' })
    await nextTick()
    expect(worldTab.attributes('aria-selected')).toBe('true')
    expect(document.activeElement).toBe(worldTab.element)

    await worldTab.trigger('keydown', { key: 'Home' })
    await nextTick()
    expect(charactersTab.attributes('aria-selected')).toBe('true')
    expect(document.activeElement).toBe(charactersTab.element)

    await charactersTab.trigger('keydown', { key: 'End' })
    await nextTick()
    expect(conceptTab.attributes('aria-selected')).toBe('true')
    expect(document.activeElement).toBe(conceptTab.element)
  })

  it('切换 setup.id 时会重置回角色子视图', async () => {
    const wrapper = mountSetupTab()
    const charactersTab = () => wrapper.get('[data-testid="setup-section-tab-characters"]')
    const worldTab = () => wrapper.get('[data-testid="setup-section-tab-world"]')
    const charactersPanel = () => wrapper.get('#setup-section-panel-characters')
    const worldPanel = () => wrapper.get('#setup-section-panel-world')

    await worldTab().trigger('click')
    expect(worldTab().attributes('aria-selected')).toBe('true')

    await wrapper.setProps({
      setup: {
        ...setupFixture,
        id: 'setup-2',
        characters: [{ name: '林雾' }],
      },
    })

    expect(charactersTab().attributes('aria-selected')).toBe('true')
    expect(charactersTab().attributes('tabindex')).toBe('0')
    expect(worldTab().attributes('aria-selected')).toBe('false')
    expect(charactersPanel().attributes('hidden')).toBeUndefined()
    expect(worldPanel().attributes('hidden')).toBe('')
  })
})
