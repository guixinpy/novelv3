// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import AthenaChatPanel from './AthenaChatPanel.vue'
import { useAthenaStore } from '../../stores/athena'

describe('AthenaChatPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('maps Athena message trace_id into chat messages', () => {
    const athena = useAthenaStore()
    athena.messages = [
      {
        id: 'athena-message-1',
        role: 'assistant',
        content: 'Athena 回复',
        trace_id: 'trace-athena-1',
      },
    ]

    const wrapper = mount(AthenaChatPanel, {
      props: {
        open: true,
        projectId: 'project-1',
      },
      global: {
        stubs: {
          Teleport: true,
          Transition: false,
        },
      },
    })

    const button = wrapper.get('[data-testid="open-trace"]')
    expect(button.text()).toBe('上下文')
  })
})
