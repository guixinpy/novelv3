// @vitest-environment jsdom
import { afterEach, describe, expect, it } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent, nextTick } from 'vue'
import type { SetupData } from '../../api/types'
import SetupTab from './SetupTab.vue'

const mountedWrappers: VueWrapper[] = []

const SetupDetailModalStub = defineComponent({
  name: 'SetupDetailModal',
  props: {
    show: {
      type: Boolean,
      required: true,
    },
    setup: {
      type: Object as () => SetupData,
      required: true,
    },
    initialSection: {
      type: String as () => 'characters' | 'world' | 'concept',
      required: true,
    },
  },
  template: `
    <div
      data-testid="setup-detail-modal-stub"
      :data-show="String(show)"
      :data-initial-section="initialSection"
      :data-setup-id="setup.id"
    />
  `,
})

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
    global: {
      stubs: {
        SetupDetailModal: SetupDetailModalStub,
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

describe('SetupTab structured sections', () => {
  it('默认展示三张设定概览卡，且不再直接渲染完整阅读区', () => {
    const wrapper = mountSetupTab()

    expect(wrapper.get('[data-testid="setup-summary-card-characters"]').text()).toContain('角色')
    expect(wrapper.get('[data-testid="setup-summary-card-world"]').text()).toContain('世界观')
    expect(wrapper.get('[data-testid="setup-summary-card-concept"]').text()).toContain('核心概念')

    expect(wrapper.find('[data-testid="setup-section-tabs"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="setup-character-detail"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="setup-world-card"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="setup-concept-card"]').exists()).toBe(false)
  })

  it('点击角色卡的查看完整后会打开 modal，并把角色 section 作为入口传给它', async () => {
    const wrapper = mountSetupTab()

    await wrapper
      .get('[data-testid="setup-summary-card-characters"] [data-testid="setup-summary-open"]')
      .trigger('click')

    const modalStub = wrapper.get('[data-testid="setup-detail-modal-stub"]')
    expect(modalStub.attributes('data-show')).toBe('true')
    expect(modalStub.attributes('data-initial-section')).toBe('characters')
    expect(modalStub.attributes('data-setup-id')).toBe('setup-1')
  })

  it('点击世界观卡的查看完整后会打开 modal，并把世界观 section 作为入口传给它', async () => {
    const wrapper = mountSetupTab()

    await wrapper
      .get('[data-testid="setup-summary-card-world"] [data-testid="setup-summary-open"]')
      .trigger('click')

    const modalStub = wrapper.get('[data-testid="setup-detail-modal-stub"]')
    expect(modalStub.attributes('data-show')).toBe('true')
    expect(modalStub.attributes('data-initial-section')).toBe('world')
  })

  it('点击核心概念卡的查看完整后会打开 modal，并把核心概念 section 作为入口传给它', async () => {
    const wrapper = mountSetupTab()

    await wrapper
      .get('[data-testid="setup-summary-card-concept"] [data-testid="setup-summary-open"]')
      .trigger('click')

    const modalStub = wrapper.get('[data-testid="setup-detail-modal-stub"]')
    expect(modalStub.attributes('data-show')).toBe('true')
    expect(modalStub.attributes('data-initial-section')).toBe('concept')
  })

  it('setup.id 变化时会关闭已打开的详情弹窗', async () => {
    const wrapper = mountSetupTab()

    await wrapper
      .get('[data-testid="setup-summary-card-world"] [data-testid="setup-summary-open"]')
      .trigger('click')

    expect(wrapper.get('[data-testid="setup-detail-modal-stub"]').attributes('data-show')).toBe('true')

    await wrapper.setProps({
      setup: {
        ...setupFixture,
        id: 'setup-2',
      },
    })
    await nextTick()

    const modalStub = wrapper.get('[data-testid="setup-detail-modal-stub"]')
    expect(modalStub.attributes('data-show')).toBe('false')
    expect(modalStub.attributes('data-initial-section')).toBe('characters')
    expect(modalStub.attributes('data-setup-id')).toBe('setup-2')
  })

  it('角色为空时渲染稳定空态节点', () => {
    const wrapper = mountSetupTab({
      ...setupFixture,
      id: 'setup-empty-characters',
      characters: [],
    })

    expect(wrapper.get('[data-testid="setup-summary-card-characters-body"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="setup-summary-card-characters-empty"]').text()).toContain('暂无角色概览')
  })

  it('世界观和核心概念在兜底摘要下仍有稳定正文节点', () => {
    const wrapper = mountSetupTab({
      ...setupFixture,
      id: 'setup-empty-summary',
      world_building: {
        background: '  ',
        geography: ' ',
        society: '',
        rules: '',
        atmosphere: null,
      },
      core_concept: {
        theme: ' ',
        premise: '',
        hook: ' ',
        unique_selling_point: null,
      },
    })

    expect(wrapper.get('[data-testid="setup-summary-card-world-body"]').text()).toContain('世界观待补充')
    expect(wrapper.get('[data-testid="setup-summary-card-concept-body"]').text()).toContain('核心概念待补充')
  })
})
