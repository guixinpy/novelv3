// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import BaseBadge from '../base/BaseBadge.vue'
import ConsistencyList from './ConsistencyList.vue'

describe('ConsistencyList', () => {
  it('emits a latest-chapter consistency check from the empty state', async () => {
    const wrapper = mount(ConsistencyList, {
      props: {
        issues: [],
        latestChapterIndex: 3,
        loading: false,
      },
    })

    await wrapper.get('[data-testid="athena-consistency-run-latest"]').trigger('click')

    expect(wrapper.emitted('runCheck')).toEqual([[3]])
  })

  it('renders checker severity aliases with the expected visual variant', () => {
    const wrapper = mount(ConsistencyList, {
      props: {
        issues: [
          {
            severity: 'fatal',
            checker_name: 'schema_gate',
            description: '缺少事件字段',
          },
          {
            severity: 'warn',
            checker_name: 'timeline_consistency',
            description: '时间线需要复核',
          },
        ],
      },
    })

    const badges = wrapper.findAllComponents(BaseBadge)

    expect(badges[0].props('variant')).toBe('error')
    expect(badges[1].props('variant')).toBe('warning')
    expect(wrapper.text()).toContain('schema_gate')
    expect(wrapper.text()).toContain('timeline_consistency')
  })
})
