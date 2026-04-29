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

  it('exposes stable workspace navigation selectors', () => {
    const wrapper = mount(ActivityBar, {
      props: {
        activeWorkspace: 'hermes',
        projectId: 'project-1',
      },
    })

    expect(wrapper.get('[data-testid="workspace-nav-hermes"]').attributes('aria-label')).toBe('Hermes')
    expect(wrapper.get('[data-testid="workspace-nav-athena"]').attributes('aria-label')).toBe('Athena')
    expect(wrapper.get('[data-testid="workspace-nav-manuscript"]').attributes('aria-label')).toBe('Calliope')
  })
})
