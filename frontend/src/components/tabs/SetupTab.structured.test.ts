// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import { defineComponent, nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import type { SetupData } from '../../api/types'
import SetupTab from './SetupTab.vue'
import { useWorldModelStore } from '../../stores/worldModel'

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

function mountSetupTab(setup: SetupData | null = setupFixture, projectId?: string) {
  const wrapper = mount(SetupTab, {
    attachTo: document.body,
    props: { setup, projectId },
    global: {
      stubs: {
        SetupDetailModal: SetupDetailModalStub,
      },
    },
  })
  mountedWrappers.push(wrapper)
  return wrapper
}

function seedWorldModelForProposalItems(itemOverrides: Array<Record<string, unknown>> = []) {
  const worldModel = useWorldModelStore()
  worldModel.projectProfile = {
    id: 'profile-1',
    project_id: 'project-1',
    genre_profile_id: 'genre-1',
    version: 2,
    contract_version: 'world.contract.v1',
    profile_payload: { genre: 'sci-fi' },
    created_at: '2026-04-20T00:00:00Z',
  }
  worldModel.projection = {
    view_type: 'current_truth',
    entities: {
      'char.hero': {
        entity_type: 'character',
        attributes: {
          status: 'alive',
          title: '修复员',
        },
      },
    },
    relations: {},
    presence: {},
    occurred_events: {},
    event_links: {},
    facts: {
      'char.hero': {
        rank: 'captain',
      },
    },
  }
  worldModel.proposalBundles = [
    {
      id: 'bundle-1',
      project_id: 'project-1',
      project_profile_version_id: 'profile-1',
      profile_version: 2,
      parent_bundle_id: null,
      bundle_status: 'pending',
      title: '候选事实',
      summary: '',
      created_by: 'writer.alpha',
      created_at: '2026-04-20T00:00:00Z',
      updated_at: '2026-04-20T00:00:00Z',
    },
  ]
  worldModel.selectedBundleId = 'bundle-1'
  worldModel.selectedBundleDetail = {
    bundle: worldModel.proposalBundles[0],
    items: itemOverrides.map((item, index) => ({
      id: `item-${index + 1}`,
      bundle_id: 'bundle-1',
      parent_item_id: null,
      item_status: 'approved',
      claim_id: `claim.hero.rank.${index + 1}`,
      subject_ref: 'char.hero',
      predicate: 'rank',
      object_ref_or_value: index === 0 ? 'captain' : 'lieutenant',
      claim_layer: 'truth',
      evidence_refs: [],
      authority_type: 'authoritative_structured',
      confidence: 0.9,
      contract_version: 'world.contract.v1',
      approved_claim_id: `claim.hero.rank.${index + 1}`,
      created_by: 'writer.alpha',
      created_at: '2026-04-20T00:00:00Z',
      ...item,
    })),
    reviews: itemOverrides.map((_, index) => ({
      id: `review-${index + 1}`,
      bundle_id: 'bundle-1',
      proposal_item_id: `item-${index + 1}`,
      review_action: 'approve',
      reviewer_ref: 'editor.alpha',
      reason: '通过',
      evidence_refs: ['chapter.01'],
      edited_fields: {},
      created_truth_claim_id: `claim.hero.rank.${index + 1}`,
      rollback_to_review_id: null,
      created_at: `2026-04-20T00:00:0${index + 1}Z`,
    })),
    impact_snapshots: [],
    conflicts: [],
  }
  return worldModel
}

afterEach(() => {
  while (mountedWrappers.length) {
    mountedWrappers.pop()?.unmount()
  }
  document.body.innerHTML = ''
})

describe('SetupTab structured sections', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

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

    expect(wrapper.find('[data-testid="setup-summary-card-characters-body"]').exists()).toBe(true)
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

  it('有世界模型投影时优先显示新视图，并隐藏旧 setup 摘要卡', () => {
    const worldModel = useWorldModelStore()
    worldModel.projectProfile = {
      id: 'profile-1',
      project_id: 'project-1',
      genre_profile_id: 'genre-1',
      version: 2,
      contract_version: 'world.contract.v1',
      profile_payload: { genre: 'sci-fi' },
      created_at: '2026-04-20T00:00:00Z',
    }
    worldModel.projection = {
      view_type: 'current_truth',
      entities: {
        'char.hero': {
          entity_type: 'character',
          attributes: {
            status: 'alive',
            title: '修复员',
          },
        },
      },
      relations: {},
      presence: {
        'char.hero': {
          location_ref: 'loc.dock-7',
          presence_status: 'active',
        },
      },
      occurred_events: {},
      event_links: {},
      facts: {
        'char.hero': {
          rank: 'captain',
        },
      },
    }
    worldModel.proposalBundles = [
      {
        id: 'bundle-1',
        project_id: 'project-1',
        project_profile_version_id: 'profile-1',
        profile_version: 2,
        parent_bundle_id: null,
        bundle_status: 'pending',
        title: '候选事实',
        summary: '',
        created_by: 'writer.alpha',
        created_at: '2026-04-20T00:00:00Z',
        updated_at: '2026-04-20T00:00:00Z',
      },
    ]

    const wrapper = mountSetupTab()

    expect(wrapper.find('[data-testid="world-model-view"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('当前真相')
    expect(wrapper.text()).toContain('候选事实')
    expect(wrapper.find('[data-testid="setup-summary-card-characters"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="setup-summary-card-world"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="setup-summary-card-concept"]').exists()).toBe(false)
  })

  it('同项目 setup 刷新后会同步重载 world model', async () => {
    const worldModel = useWorldModelStore()
    const loadSpy = vi.spyOn(worldModel, 'loadSetupPanelData').mockResolvedValue()
    const wrapper = mountSetupTab(setupFixture, 'project-1')

    await nextTick()
    expect(loadSpy).toHaveBeenCalledTimes(1)
    expect(loadSpy).toHaveBeenNthCalledWith(1, 'project-1')

    await wrapper.setProps({
      setup: {
        ...setupFixture,
        updated_at: '2026-04-18T00:01:00Z',
      },
    })
    await nextTick()

    expect(loadSpy).toHaveBeenCalledTimes(2)
    expect(loadSpy).toHaveBeenNthCalledWith(2, 'project-1')
  })

  it('世界模型加载失败时会显式显示错误，而不是静默回退到旧 setup 摘要', async () => {
    const worldModel = useWorldModelStore()
    vi.spyOn(worldModel, 'loadSetupPanelData').mockResolvedValue()

    const wrapper = mountSetupTab(setupFixture, 'project-1')
    worldModel.error = 'world projection anchor.typo 缺失'
    worldModel.loaded = true
    worldModel.loading = false
    await nextTick()

    expect(wrapper.get('[data-testid="world-model-error"]').text()).toContain(
      'world projection anchor.typo 缺失',
    )
  })

  it('审批后 overview refresh 失败时，即使还有旧 world data 也必须优先显示错误', async () => {
    const worldModel = useWorldModelStore()
    vi.spyOn(worldModel, 'loadSetupPanelData').mockResolvedValue()

    const wrapper = mountSetupTab(setupFixture, 'project-1')
    seedWorldModelForProposalItems([
      { item_status: 'approved' },
    ])
    worldModel.error = 'overview refresh failed'
    worldModel.proposalBundles = [
      {
        ...worldModel.proposalBundles[0],
        bundle_status: 'approved',
      },
    ]
    worldModel.selectedBundleDetail = {
      ...worldModel.selectedBundleDetail!,
      bundle: {
        ...worldModel.selectedBundleDetail!.bundle,
        bundle_status: 'approved',
      },
      items: worldModel.selectedBundleDetail!.items.map((item) => ({
        ...item,
        item_status: 'approved',
      })),
    }
    await nextTick()

    expect(wrapper.get('[data-testid="world-model-error"]').text()).toContain('overview refresh failed')
    expect(wrapper.find('[data-testid="world-model-view"]').exists()).toBe(false)
    expect(worldModel.proposalBundles[0].bundle_status).toBe('approved')
    expect(worldModel.selectedBundleDetail?.items[0].item_status).toBe('approved')
  })

  it('已 rolled_back 的 item 不再显示 rollback 入口', () => {
    seedWorldModelForProposalItems([
      { item_status: 'approved' },
      { item_status: 'rolled_back' },
    ])

    const wrapper = mountSetupTab(setupFixture)
    const rollbackButtons = wrapper.findAll('button').filter((button) => button.text() === '回滚')

    expect(rollbackButtons).toHaveLength(1)
  })

  it('pending action 中只禁用当前 item 的回滚按钮', () => {
    const worldModel = seedWorldModelForProposalItems([
      { item_status: 'approved' },
      { item_status: 'approved' },
    ])
    worldModel.pendingActionCounts = {
      'item-1': 1,
    }

    const wrapper = mountSetupTab(setupFixture)
    const cards = wrapper.findAll('[data-testid="world-proposal-item-card"]')
    const firstRollback = cards[0].findAll('button').find((button) => button.text() === '回滚')
    const secondRollback = cards[1].findAll('button').find((button) => button.text() === '回滚')

    expect(firstRollback?.attributes('disabled')).toBeDefined()
    expect(secondRollback?.attributes('disabled')).toBeUndefined()
  })
})
