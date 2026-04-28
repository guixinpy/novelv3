// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ChatMessageList from './ChatMessageList.vue'

describe('ChatMessageList', () => {
  it('forwards openTrace from child messages', async () => {
    const wrapper = mount(ChatMessageList, {
      props: {
        messages: [
          {
            role: 'assistant',
            content: '带 trace 的回复',
            trace_id: 'trace-list-1',
          },
        ],
        loading: false,
      },
    })

    await wrapper.get('[data-testid="open-trace"]').trigger('click')

    expect(wrapper.emitted('openTrace')).toEqual([['trace-list-1']])
  })
})
