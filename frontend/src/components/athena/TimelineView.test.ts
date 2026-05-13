// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TimelineView from './TimelineView.vue'

describe('TimelineView', () => {
  it('renders chapter plan events as a usable timeline fallback', () => {
    const wrapper = mount(TimelineView, {
      props: {
        events: [
          {
            id: 'plan-chapter-1',
            event_id: 'plan.chapter.1',
            chapter_index: 1,
            intra_chapter_seq: 0,
            event_type: 'chapter_plan',
            description: '雾锁灯塔：陆辞接到协会指派。',
          },
        ],
      },
    })

    expect(wrapper.text()).toContain('雾锁灯塔')
    expect(wrapper.text()).toContain('第1章')
    expect(wrapper.text()).toContain('章节规划')
    expect(wrapper.text()).not.toContain('暂无时间线数据')
  })

  it('collapses completed timeline nodes so the current node is visible first', async () => {
    const wrapper = mount(TimelineView, {
      props: {
        events: [
          {
            id: 'plan-chapter-1',
            event_id: 'plan.chapter.1',
            chapter_index: 1,
            intra_chapter_seq: 0,
            event_type: 'chapter_plan',
            description: '第1章：已经完成的调查。',
          },
          {
            id: 'plan-chapter-2',
            event_id: 'plan.chapter.2',
            chapter_index: 2,
            intra_chapter_seq: 0,
            event_type: 'chapter_plan',
            description: '第2章：已经完成的追踪。',
          },
          {
            id: 'plan-chapter-3',
            event_id: 'plan.chapter.3',
            chapter_index: 3,
            intra_chapter_seq: 0,
            event_type: 'chapter_plan',
            description: '第3章：当前推进的节点。',
          },
        ],
      },
    })

    expect(wrapper.text()).toContain('已收起前 2 个已完成节点')
    expect(wrapper.text()).toContain('当前推进的节点')
    expect(wrapper.text()).not.toContain('已经完成的调查')

    await wrapper.get('[data-testid="timeline-completed-toggle"]').trigger('click')

    expect(wrapper.text()).toContain('已经完成的调查')
  })

  it('shows loading before timeline data resolves', () => {
    const wrapper = mount(TimelineView, {
      props: {
        events: [],
        loading: true,
        fallbackSummary: {
          chapters: 20,
          plotlines: 4,
          foreshadowing: 10,
        },
      },
    })

    expect(wrapper.text()).toContain('正在读取叙事时间线')
    expect(wrapper.text()).not.toContain('暂无时间线数据')
  })

  it('explains when narrative plan data exists but no timeline facts exist yet', () => {
    const wrapper = mount(TimelineView, {
      props: {
        events: [],
        fallbackSummary: {
          chapters: 20,
          plotlines: 4,
          foreshadowing: 10,
        },
      },
    })

    expect(wrapper.text()).toContain('暂无时间线数据')
    expect(wrapper.text()).toContain('已生成 20 章规划')
    expect(wrapper.text()).toContain('4 条故事线')
    expect(wrapper.text()).toContain('10 条伏笔')
  })
})
