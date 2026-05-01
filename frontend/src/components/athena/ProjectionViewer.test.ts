// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ProjectionViewer from './ProjectionViewer.vue'

describe('ProjectionViewer', () => {
  it('renders WorldProjection facts stored as subject maps', () => {
    const wrapper = mount(ProjectionViewer, {
      props: {
        projection: {
          view_type: 'current_truth',
          entities: {
            'char.lin': {
              entity_type: 'character',
              attributes: { name: '林舟', status: 'alive' },
            },
            'loc.tower': {
              entity_type: 'location',
              attributes: { name: '旧灯塔' },
            },
          },
          relations: {},
          presence: {
            'char.lin': { location_ref: 'loc.tower', presence_status: 'active' },
          },
          occurred_events: {},
          event_links: {},
          facts: {
            'char.lin': {
              rank: '守夜人',
              secret: '知道旧灯塔真相',
            },
          },
        },
      },
    })

    expect(wrapper.text()).toContain('char.lin')
    expect(wrapper.text()).toContain('人物')
    expect(wrapper.text()).toContain('地点')
    expect(wrapper.text()).toContain('rank')
    expect(wrapper.text()).toContain('守夜人')
    expect(wrapper.text()).toContain('loc.tower')
  })

  it('merges facts into matching entity rows without duplicating the subject header', () => {
    const wrapper = mount(ProjectionViewer, {
      props: {
        projection: {
          view_type: 'current_truth',
          entities: {
            'loc.tower': {
              entity_type: 'location',
              attributes: { name: '旧灯塔' },
            },
          },
          relations: {},
          presence: {},
          occurred_events: {},
          event_links: {},
          facts: {
            'loc.tower': {
              mentioned_in_chapter: 1,
            },
          },
        },
      },
    })

    const subjectHeaders = wrapper
      .findAll('.projection-viewer__entity')
      .filter((node) => node.text() === 'loc.tower')

    expect(subjectHeaders).toHaveLength(1)
    expect(wrapper.text()).toContain('mentioned_in_chapter')
  })

  it('counts fact subjects even when facts are merged into entity rows', () => {
    const wrapper = mount(ProjectionViewer, {
      props: {
        projection: {
          view_type: 'current_truth',
          entities: {
            'char.lu': {
              entity_type: 'character',
              attributes: { name: '陆辞' },
            },
          },
          relations: {},
          presence: {},
          occurred_events: {},
          event_links: {},
          facts: {
            'char.lu': {
              presence_count: { count: 51, chapter_index: 1 },
            },
          },
        },
      },
    })

    const metricTexts = wrapper.findAll('.projection-viewer__metric').map((metric) => metric.text())

    expect(metricTexts).toContain('事实主体1')
  })

  it('renders occurred event details for ledger review', () => {
    const wrapper = mount(ProjectionViewer, {
      props: {
        projection: {
          view_type: 'current_truth',
          entities: {},
          relations: {},
          presence: {},
          occurred_events: {
            'event.chapter.1.summary': {
              title: '第一章',
              summary: '旧灯塔重新点亮',
              chapter_index: 1,
            },
          },
          event_links: {},
          facts: {},
        },
      },
    })

    expect(wrapper.text()).toContain('事件记录')
    expect(wrapper.text()).toContain('event.chapter.1.summary')
    expect(wrapper.text()).toContain('旧灯塔重新点亮')
  })

  it('formats structured presence_count facts for creator review', () => {
    const wrapper = mount(ProjectionViewer, {
      props: {
        projection: {
          view_type: 'current_truth',
          entities: {
            'char.lu': {
              entity_type: 'character',
              attributes: { name: '陆辞' },
            },
          },
          relations: {},
          presence: {},
          occurred_events: {},
          event_links: {},
          facts: {
            'char.lu': {
              presence_count: {
                count: 51,
                chapter_index: 1,
                source: 'l1_rule',
                matched_names: ['陆辞'],
              },
            },
          },
        },
      },
    })

    expect(wrapper.text()).toContain('第1章出现 51 次')
    expect(wrapper.text()).not.toContain('"matched_names"')
  })
})
