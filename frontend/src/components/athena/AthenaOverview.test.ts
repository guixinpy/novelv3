// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AthenaOverview from './AthenaOverview.vue'

describe('AthenaOverview', () => {
  it('shows loading state instead of empty world-model conclusions while dashboard is loading', () => {
    const wrapper = mount(AthenaOverview, {
      props: {
        dashboard: null,
        loading: true,
      },
    })

    expect(wrapper.text()).toContain('正在读取世界模型')
    expect(wrapper.text()).not.toContain('未导入 world-model')
    expect(wrapper.text()).not.toContain('等待世界模型初始化')
  })

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

    expect(wrapper.emitted('navigate')).toEqual([['review']])
  })

  it('maps projection inspection to the truth section', async () => {
    const wrapper = mount(AthenaOverview, {
      props: {
        dashboard: {
          project_profile: null,
          metrics: {
            entity_count: 1,
            fact_count: 2,
            presence_count: 0,
            event_count: 0,
            pending_bundle_count: 0,
            pending_item_count: 0,
          },
          next_action: {
            action: 'inspect_projection',
            label: '检查真相投影',
          },
        },
        loading: false,
      },
    })

    await wrapper.get('[data-testid="athena-overview-next-action"]').trigger('click')

    expect(wrapper.emitted('navigate')).toEqual([['truth']])
  })

  it('emits executable next actions instead of navigating to an unrelated section', async () => {
    const wrapper = mount(AthenaOverview, {
      props: {
        dashboard: {
          project_profile: {
            id: 'profile-1',
            project_id: 'project-1',
            genre_profile_id: 'genre-1',
            version: 1,
            contract_version: 'world.contract.v1',
            profile_payload: {},
            created_at: '2026-04-29T00:00:00Z',
          },
          metrics: {
            entity_count: 5,
            fact_count: 0,
            presence_count: 0,
            event_count: 0,
            pending_bundle_count: 0,
            pending_item_count: 0,
          },
          next_action: {
            action: 'analyze_chapter',
            label: '分析章节，生成候选事实',
          },
        },
        loading: false,
      },
    })

    await wrapper.get('[data-testid="athena-overview-next-action"]').trigger('click')

    expect(wrapper.emitted('runAction')).toEqual([['analyze_chapter']])
    expect(wrapper.emitted('navigate')).toBeUndefined()
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

  it('renders stale longform maintenance diagnostics with Chinese labels and chapter indexes', () => {
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
            action: 'inspect_projection',
            label: '检查真相投影',
          },
        },
        maintenanceDiagnostics: {
          project_id: 'project-1',
          status: 'stale',
          ready_for_writing: false,
          issue_count: 4,
          recommendations: [
            {
              kind: 'stale_memory',
              severity: 'warning',
              title: '刷新过期章节记忆',
              message: '1 章长篇记忆落后于正文，建议先执行维护修复再继续长篇写作。',
              chapter_indexes: [512],
            },
            {
              kind: 'missing_retrieval',
              severity: 'warning',
              title: '补齐检索索引',
              message: '1 章长篇记忆尚未进入检索索引，建议补齐后再进行跨章节检索。',
              chapter_indexes: [900],
            },
          ],
          chapter_count: 1000,
          stale_memory_count: 1,
          missing_memory_count: 0,
          stale_retrieval_count: 2,
          missing_retrieval_count: 1,
          stale_chapter_indexes: [512],
          missing_memory_chapter_indexes: [],
          stale_retrieval_chapter_indexes: [512, 780],
          missing_retrieval_chapter_indexes: [900],
          latest_chapter_updated_at: '2026-05-13T00:00:00Z',
          latest_memory_updated_at: '2026-05-13T00:00:01Z',
          latest_retrieval_updated_at: '2026-05-12T23:59:59Z',
          latest_synced_chapter_index: 1000,
        },
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('长篇维护')
    expect(wrapper.text()).toContain('需要维护')
    expect(wrapper.text()).toContain('写作准备 需修复')
    expect(wrapper.text()).toContain('问题 4')
    expect(wrapper.text()).toContain('章节 1000')
    expect(wrapper.text()).toContain('过期记忆 1')
    expect(wrapper.text()).toContain('过期检索 2')
    expect(wrapper.text()).toContain('缺失检索 1')
    expect(wrapper.text()).toContain('过期记忆章节：512')
    expect(wrapper.text()).toContain('过期检索章节：512、780')
    expect(wrapper.text()).toContain('缺失检索章节：900')
    expect(wrapper.text()).toContain('维护建议')
    expect(wrapper.text()).toContain('刷新过期章节记忆')
    expect(wrapper.text()).toContain('补齐检索索引')
  })

  it('renders longform word target drift summary', () => {
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
            action: 'inspect_projection',
            label: '检查真相投影',
          },
        },
        maintenanceDiagnostics: {
          project_id: 'project-1',
          status: 'current',
          chapter_count: 3,
          word_target: {
            status: 'drift',
            target_average_word_count: 100,
            target_min_word_count: 85,
            target_max_word_count: 115,
            under_target_count: 1,
            within_target_count: 1,
            over_target_count: 1,
            under_target_chapter_indexes: [1],
            over_target_chapter_indexes: [3],
          },
          stale_memory_count: 0,
          missing_memory_count: 0,
          stale_retrieval_count: 0,
          missing_retrieval_count: 0,
          stale_chapter_indexes: [],
          missing_memory_chapter_indexes: [],
          stale_retrieval_chapter_indexes: [],
          missing_retrieval_chapter_indexes: [],
          latest_chapter_updated_at: '2026-05-13T00:00:00Z',
          latest_memory_updated_at: '2026-05-13T00:00:01Z',
          latest_retrieval_updated_at: '2026-05-13T00:00:02Z',
          latest_synced_chapter_index: 3,
        },
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('字数节奏')
    expect(wrapper.text()).toContain('目标 100字')
    expect(wrapper.text()).toContain('范围 85-115字')
    expect(wrapper.text()).toContain('偏短 1')
    expect(wrapper.text()).toContain('达标 1')
    expect(wrapper.text()).toContain('偏长 1')
    expect(wrapper.text()).toContain('偏短章节：1')
    expect(wrapper.text()).toContain('偏长章节：3')
  })

  it('emits repair request from stale longform maintenance diagnostics', async () => {
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
            action: 'inspect_projection',
            label: '检查真相投影',
          },
        },
        maintenanceDiagnostics: {
          project_id: 'project-1',
          status: 'stale',
          chapter_count: 1000,
          stale_memory_count: 1,
          missing_memory_count: 0,
          stale_retrieval_count: 2,
          missing_retrieval_count: 0,
          stale_chapter_indexes: [512],
          missing_memory_chapter_indexes: [],
          stale_retrieval_chapter_indexes: [512, 780],
          missing_retrieval_chapter_indexes: [],
          latest_chapter_updated_at: '2026-05-13T00:00:00Z',
          latest_memory_updated_at: '2026-05-13T00:00:01Z',
          latest_retrieval_updated_at: '2026-05-12T23:59:59Z',
          latest_synced_chapter_index: 1000,
        },
        loading: false,
      },
    })

    await wrapper.get('[data-testid="athena-overview-repair-maintenance"]').trigger('click')

    expect(wrapper.emitted('repairMaintenance')).toEqual([[]])
  })
})
