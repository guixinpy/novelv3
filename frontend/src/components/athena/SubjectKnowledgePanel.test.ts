// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SubjectKnowledgePanel from './SubjectKnowledgePanel.vue'

describe('SubjectKnowledgePanel', () => {
  it('shows readable subject names with refs in the selector', () => {
    const wrapper = mount(SubjectKnowledgePanel, {
      props: {
        projection: {
          view_type: 'current_truth',
          entities: {
            'char.lin': {
              entity_type: 'character',
              attributes: { name: '林舟' },
            },
          },
          relations: {},
          presence: {},
          occurred_events: {},
          event_links: {},
          facts: {},
        },
        subjectKnowledge: null,
        selectedSubjectRef: null,
      },
    })

    expect(wrapper.find('option[value="char.lin"]').text()).toBe('林舟（char.lin）')
  })

  it('offers subjects from fact groups when projection entity catalog is incomplete', () => {
    const wrapper = mount(SubjectKnowledgePanel, {
      props: {
        projection: {
          view_type: 'current_truth',
          entities: {},
          relations: {},
          presence: {},
          occurred_events: {},
          event_links: {},
          facts: {
            'char.lin': {
              rank: '守夜人',
            },
          },
        },
        subjectKnowledge: null,
        selectedSubjectRef: null,
      },
    })

    expect(wrapper.find('option[value="char.lin"]').exists()).toBe(true)
  })

  it('does not offer non-character entities as knowledge subjects', () => {
    const wrapper = mount(SubjectKnowledgePanel, {
      props: {
        projection: {
          view_type: 'current_truth',
          entities: {
            'char.lin': {
              entity_type: 'character',
              attributes: { name: '林舟' },
            },
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
            'char.lin': { rank: '守夜人' },
            'loc.tower': { status: '点亮' },
          },
        },
        subjectKnowledge: null,
        selectedSubjectRef: null,
      },
    })

    expect(wrapper.find('option[value="char.lin"]').exists()).toBe(true)
    expect(wrapper.find('option[value="loc.tower"]').exists()).toBe(false)
  })
})
