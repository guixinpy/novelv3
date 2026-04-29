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
})
