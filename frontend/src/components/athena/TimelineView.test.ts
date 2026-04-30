// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import TimelineView from './TimelineView.vue'

describe('TimelineView', () => {
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
