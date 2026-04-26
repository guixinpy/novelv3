// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ActivityBar from './ActivityBar.vue'

describe('ActivityBar', () => {
  it('labels the manuscript workspace as Calliope for users', () => {
    const wrapper = mount(ActivityBar, {
      props: {
        activeWorkspace: 'manuscript',
        projectId: 'project-1',
      },
    })

    const calliopeButton = wrapper.get('button[aria-label="Calliope"]')

    expect(calliopeButton.attributes('title')).toBe('Calliope')
    expect(wrapper.text()).not.toContain('Manuscript')
  })
})
