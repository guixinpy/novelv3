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

  it('forwards openAgentRun from child messages', async () => {
    const wrapper = mount(ChatMessageList, {
      props: {
        messages: [
          {
            role: 'assistant',
            content: '恢复预览已生成。',
            action_result: {
              type: 'plan_recovery_tools',
              status: 'success',
              data: { agent_run_id: 'run-list-1' },
            },
            action_result_view: {
              type: 'plan_recovery_tools',
              status: 'success',
              label: '恢复预览已生成',
              variant: 'success',
            },
          },
        ],
        loading: false,
      },
    })

    await wrapper.get('[data-testid="open-agent-run"]').trigger('click')

    expect(wrapper.emitted('openAgentRun')).toEqual([['run-list-1']])
  })
})
