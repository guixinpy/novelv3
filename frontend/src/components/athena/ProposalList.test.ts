// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ProposalList from './ProposalList.vue'

describe('ProposalList', () => {
  it('renders bundle_status from proposal list endpoint', () => {
    const wrapper = mount(ProposalList, {
      props: {
        proposals: {
          items: [
            {
              id: 'bundle-1',
              title: 'Athena 对话待审世界更新',
              bundle_status: 'pending',
            },
          ],
        },
      },
    })

    expect(wrapper.text()).toContain('Athena 对话待审世界更新')
    expect(wrapper.text()).toContain('pending')
    expect(wrapper.text()).not.toContain('0 项')
  })
})
