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
    const secondCharacter = () => wrapper.get('[data-testid="setup-character-item-周岚"]')
    const detail = () => wrapper.get('[data-testid="setup-character-detail"]')

    await worldTab().trigger('click')
    await secondCharacter().trigger('click')
    expect(worldTab().attributes('aria-selected')).toBe('true')
    expect(detail().text()).toContain('周岚')

    await wrapper.setProps({
      setup: {
        ...setupFixture,
        id: 'setup-2',
        characters: [
          { name: '林雾', background: '雾港信使' },
          { name: '赵衡', background: '盐场护卫' },
        ],
      },
    })

    expect(charactersTab().attributes('aria-selected')).toBe('true')
    expect(charactersTab().attributes('tabindex')).toBe('0')
    expect(worldTab().attributes('aria-selected')).toBe('false')
    expect(charactersPanel().attributes('hidden')).toBeUndefined()
    expect(worldPanel().attributes('hidden')).toBe('')
    expect(wrapper.get('[data-testid="setup-character-item-林雾"]').attributes('aria-pressed')).toBe('true')
    expect(detail().text()).toContain('林雾')
    expect(detail().text()).toContain('雾港信使')
    expect(detail().text()).not.toContain('周岚')
  })

  it('默认详情区展示第一名角色', () => {
    const wrapper = mountSetupTab()

    const firstCharacter = wrapper.get('[data-testid="setup-character-item-沈砚"]')
    const detail = wrapper.get('[data-testid="setup-character-detail"]')

    expect(firstCharacter.attributes('aria-pressed')).toBe('true')
    expect(detail.text()).toContain('沈砚')
    expect(detail.text()).toContain('旧城档案馆的修复员')
    expect(detail.text()).toContain('28 岁')
    expect(detail.text()).toContain('男')
    expect(detail.text()).toContain('存活')
  })

  it('点击角色列表项后，详情区切换到目标角色', async () => {
    const wrapper = mountSetupTab()

    const firstCharacter = () => wrapper.get('[data-testid="setup-character-item-沈砚"]')
    const secondCharacter = () => wrapper.get('[data-testid="setup-character-item-周岚"]')
    const detail = () => wrapper.get('[data-testid="setup-character-detail"]')

    await secondCharacter().trigger('click')

    expect(secondCharacter().attributes('aria-pressed')).toBe('true')
    expect(firstCharacter().attributes('aria-pressed')).toBe('false')
    expect(detail().text()).toContain('周岚')
    expect(detail().text()).toContain('边境调查员')
    expect(detail().text()).not.toContain('沈砚')
  })

  it('空字段显示待补充', () => {
    const wrapper = mountSetupTab({
      ...setupFixture,
      id: 'setup-empty-fields',
      characters: [
        {
          name: '顾迟',
          background: '  ',
          personality: '',
          goals: null,
          age: null,
          gender: null,
          character_status: null,
        },
      ],
    })

    const detail = wrapper.get('[data-testid="setup-character-detail"]')
    const text = detail.text()

    expect(text).toContain('顾迟')
    expect(text).toContain('待补充')
  })

  it('切到世界观后展示 5 张中文字段卡，空字段显示待补充且不暴露 JSON key', async () => {
    const wrapper = mountSetupTab({
      ...setupFixture,
      id: 'setup-world-empty-fields',
      world_building: {
        background: '  ',
        geography: '群岛与雾海',
        society: '',
        rules: '记忆税制度',
        atmosphere: null,
      },
    })

    await wrapper.get('[data-testid="setup-section-tab-world"]').trigger('click')

    const panelText = wrapper.get('#setup-section-panel-world').text()
    const worldCards = wrapper.findAll('[data-testid="setup-world-card"]')
    const worldLabels = wrapper.findAll('[data-testid="setup-world-label"]').map((node) => node.text())
    const worldValues = wrapper.findAll('[data-testid="setup-world-value"]').map((node) => node.text())

    expect(worldCards).toHaveLength(5)
    expect(worldLabels).toEqual(['时代背景', '地理格局', '社会结构', '规则体系', '氛围基调'])
    expect(worldValues).toEqual(['待补充', '群岛与雾海', '待补充', '记忆税制度', '待补充'])
    expect(worldCards[1].get('[data-testid="setup-world-label"]').text()).toBe('地理格局')
    expect(worldCards[1].get('[data-testid="setup-world-value"]').text()).toBe('群岛与雾海')
    expect(panelText).not.toContain('background')
    expect(panelText).not.toContain('geography')
    expect(panelText).not.toContain('society')
    expect(panelText).not.toContain('rules')
    expect(panelText).not.toContain('atmosphere')
  })

  it('切到核心概念后展示 4 张中文字段卡，空字段显示待补充且不暴露 JSON key', async () => {
    const wrapper = mountSetupTab({
      ...setupFixture,
      id: 'setup-concept-empty-fields',
      core_concept: {
        theme: ' ',
        premise: '记忆能被征税和买卖',
        hook: '',
        unique_selling_point: null,
      },
    })

    await wrapper.get('[data-testid="setup-section-tab-concept"]').trigger('click')

    const panelText = wrapper.get('#setup-section-panel-concept').text()
    const conceptCards = wrapper.findAll('[data-testid="setup-concept-card"]')
    const conceptLabels = wrapper.findAll('[data-testid="setup-concept-label"]').map((node) => node.text())
    const conceptValues = wrapper.findAll('[data-testid="setup-concept-value"]').map((node) => node.text())

    expect(conceptCards).toHaveLength(4)
    expect(conceptLabels).toEqual(['主题', '前提设定', '核心钩子', '独特卖点'])
    expect(conceptValues).toEqual(['待补充', '记忆能被征税和买卖', '待补充', '待补充'])
    expect(conceptCards[1].get('[data-testid="setup-concept-label"]').text()).toBe('前提设定')
    expect(conceptCards[1].get('[data-testid="setup-concept-value"]').text()).toBe('记忆能被征税和买卖')
    expect(panelText).not.toContain('theme')
    expect(panelText).not.toContain('premise')
    expect(panelText).not.toContain('hook')
    expect(panelText).not.toContain('unique_selling_point')
  })

  it('character_status: alive 显示为存活', () => {
    const wrapper = mountSetupTab()

    const detail = wrapper.get('[data-testid="setup-character-detail"]')

    expect(detail.text()).toContain('存活')
  })

  it('characters 更新且当前选中角色不存在时，会回退到第一名角色', async () => {
    const wrapper = mountSetupTab()
    const secondCharacter = () => wrapper.get('[data-testid="setup-character-item-周岚"]')
    const detail = () => wrapper.get('[data-testid="setup-character-detail"]')

    await secondCharacter().trigger('click')
    expect(secondCharacter().attributes('aria-pressed')).toBe('true')
    expect(detail().text()).toContain('周岚')

    await wrapper.setProps({
      setup: {
        ...setupFixture,
        characters: [
          {
            name: '顾迟',
            background: '残塔守夜人',
            personality: '寡言',
            goals: '守住最后灯火',
          },
          {
            name: '苏遥',
            background: '流亡测绘师',
            personality: '敏锐',
            goals: '重绘航线',
          },
        ],
      },
    })

    expect(wrapper.get('[data-testid="setup-character-item-顾迟"]').attributes('aria-pressed')).toBe('true')
    expect(detail().text()).toContain('顾迟')
    expect(detail().text()).toContain('残塔守夜人')
    expect(detail().text()).not.toContain('周岚')
  })

  it('重名角色场景下可以稳定选中目标项，不会双高亮', async () => {
    const wrapper = mountSetupTab({
      ...setupFixture,
      id: 'setup-duplicate-names',
      characters: [
        {
          name: '沈砚',
          background: '旧城档案馆的修复员',
          personality: '克制',
          goals: '找回失落档案',
        },
        {
          name: '沈砚',
          background: '北境巡夜人',
          personality: '冷硬',
          goals: '追查边哨失踪案',
        },
      ],
    })

    const characterItems = () => wrapper.findAll('[data-testid^="setup-character-item-沈砚"]')
    const detail = () => wrapper.get('[data-testid="setup-character-detail"]')

    expect(characterItems()).toHaveLength(2)
    expect(characterItems()[0].attributes('aria-pressed')).toBe('true')
    expect(characterItems()[1].attributes('aria-pressed')).toBe('false')
    expect(detail().text()).toContain('旧城档案馆的修复员')

    await characterItems()[1].trigger('click')

    expect(characterItems()[0].attributes('aria-pressed')).toBe('false')
    expect(characterItems()[1].attributes('aria-pressed')).toBe('true')
    expect(detail().text()).toContain('北境巡夜人')
    expect(detail().text()).not.toContain('旧城档案馆的修复员')
  })
})
