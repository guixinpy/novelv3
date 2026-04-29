// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AthenaOverview from './AthenaOverview.vue'

describe('AthenaOverview', () => {
  it('renders dashboard metrics and next action', () => {
    const wrapper = mount(AthenaOverview, {
      props: {
        dashboard: {
          project_profile: {
            id: 'profile-1',
            project_id: 'project-1',
            genre_profile_id: 'genre-1',
            version: 3,
            contract_version: 'world.contract.v1',
            profile_payload: {},
            created_at: '2026-04-29T00:00:00Z',
          },
          metrics: {
            entity_count: 4,
            fact_count: 8,
            presence_count: 1,
            event_count: 2,
            pending_bundle_count: 1,
            pending_item_count: 3,
          },
          next_action: {
            action: 'review_proposals',
            label: '处理待审世界模型提案',
          },
        },
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('Profile v3')
    expect(wrapper.text()).toContain('实体')
    expect(wrapper.text()).toContain('4')
    expect(wrapper.text()).toContain('待审条目')
    expect(wrapper.text()).toContain('3')
    expect(wrapper.text()).toContain('处理待审世界模型提案')
  })

  it('emits the mapped next section when action is clicked', async () => {
    const wrapper = mount(AthenaOverview, {
      props: {
        dashboard: {
          project_profile: null,
          metrics: {
            entity_count: 0,
            fact_count: 0,
            presence_count: 0,
            event_count: 0,
            pending_bundle_count: 1,
            pending_item_count: 1,
          },
          next_action: {
            action: 'review_proposals',
            label: '处理待审世界模型提案',
          },
        },
        loading: false,
      },
    })

    await wrapper.get('[data-testid="athena-overview-next-action"]').trigger('click')

    expect(wrapper.emitted('navigate')).toEqual([['proposals']])
  })

  it('renders setup import preview counts before profile exists', () => {
    const wrapper = mount(AthenaOverview, {
      props: {
        dashboard: {
          project_profile: null,
          metrics: {
            entity_count: 0,
            fact_count: 0,
            presence_count: 0,
            event_count: 0,
            pending_bundle_count: 0,
            pending_item_count: 0,
          },
          next_action: {
            action: 'import_setup',
            label: '导入 Setup',
          },
        },
        setupPreview: {
          status: 'preview',
          project_profile_exists: false,
          profile_version: null,
          would_create: {
            profile: 1,
            characters: 2,
            locations: 2,
            factions: 2,
            artifacts: 1,
            rules: 1,
          },
          candidates: {
            characters: [],
            locations: [],
            factions: [],
            artifacts: [],
            rules: [],
          },
        },
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('导入预览')
    expect(wrapper.text()).toContain('角色 2')
    expect(wrapper.text()).toContain('地点 2')
    expect(wrapper.text()).toContain('规则 1')
  })
})
