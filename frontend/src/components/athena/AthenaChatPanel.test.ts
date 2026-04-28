// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { defineComponent } from 'vue'
import AthenaChatPanel from './AthenaChatPanel.vue'
import { useAthenaStore } from '../../stores/athena'

const ModelTraceDrawerStub = defineComponent({
  name: 'ModelTraceDrawer',
  props: {
    projectId: {
      type: String,
      required: true,
    },
    traceId: {
      type: String,
      default: null,
    },
    open: {
      type: Boolean,
      required: true,
    },
  },
  template: '<div data-testid="trace-drawer" />',
})

function mountPanel(projectId = 'project-1') {
  return mount(AthenaChatPanel, {
    props: {
      open: true,
      projectId,
    },
    global: {
      stubs: {
        Teleport: true,
        Transition: false,
        ModelTraceDrawer: ModelTraceDrawerStub,
      },
    },
  })
}

function setAssistantTraceMessage(traceId: string) {
  const athena = useAthenaStore()
  athena.messages = [
    {
      id: 'athena-message-1',
      role: 'assistant',
      content: 'Athena 回复',
      trace_id: traceId,
    },
  ]
}

describe('AthenaChatPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('opens trace drawer with clicked Athena message trace id', async () => {
    setAssistantTraceMessage('trace-athena-1')
    const wrapper = mountPanel('project-1')

    await wrapper.get('[data-testid="open-trace"]').trigger('click')

    const drawer = wrapper.getComponent({ name: 'ModelTraceDrawer' })
    expect(drawer.props()).toMatchObject({
      projectId: 'project-1',
      traceId: 'trace-athena-1',
      open: true,
    })
  })

  it('clears active trace drawer when project changes', async () => {
    setAssistantTraceMessage('trace-athena-1')
    const wrapper = mountPanel('project-1')

    await wrapper.get('[data-testid="open-trace"]').trigger('click')
    await wrapper.setProps({ projectId: 'project-2' })

    const drawer = wrapper.getComponent({ name: 'ModelTraceDrawer' })
    expect(drawer.props()).toMatchObject({
      projectId: 'project-2',
      traceId: null,
      open: false,
    })
  })
})
