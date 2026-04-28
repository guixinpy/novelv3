// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ChatMessage from './ChatMessage.vue'

describe('ChatMessage', () => {
  it('renders chapter generation action results with a user-facing label', () => {
    const wrapper = mount(ChatMessage, {
      props: {
        msg: {
          role: 'system',
          message_type: 'plain',
          content: '第1章正文生成完成。',
          action_result: { type: 'generate_chapter', status: 'success' },
        },
        isLatest: false,
        loading: false,
      },
    })

    expect(wrapper.text()).toContain('生成正文执行成功')
    expect(wrapper.text()).not.toContain('generate_chapter')
  })
})
