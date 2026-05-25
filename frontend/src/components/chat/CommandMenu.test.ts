// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import CommandMenu from './CommandMenu.vue'
import type { ChatCommandDefinition } from '../../components/workspace/chatCommands'

describe('CommandMenu', () => {
  it('shows agent command contract labels without leaking raw projection ids', () => {
    const commands: ChatCommandDefinition[] = [
      {
        name: 'continue',
        label: '/continue',
        description: '继续推进',
        example: '/continue',
        supportsArgs: false,
        public: true,
        category: 'agent_control',
        capabilityId: 'agent.continue',
        controlProjectionType: 'continue_agent_control',
        requiredAgentTools: [
          'inspect_agent_health_projection',
          'plan_recovery_tools',
          'plan_recommended_followups',
          'prepare_generate_chapter_execution',
        ],
        available: true,
        unavailableReasons: [],
      },
    ]

    const wrapper = mount(CommandMenu, {
      props: {
        commands,
        activeIndex: 0,
      },
    })

    expect(wrapper.text()).toContain('Agent 控制')
    expect(wrapper.text()).toContain('继续控制')
    expect(wrapper.text()).toContain('4 项能力')
    expect(wrapper.text()).not.toContain('continue_agent_control')
  })
})
