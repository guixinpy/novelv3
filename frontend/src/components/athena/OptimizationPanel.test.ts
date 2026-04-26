// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import OptimizationPanel from './OptimizationPanel.vue'

describe('OptimizationPanel', () => {
  it('uses Calliope as the manuscript revision module name', () => {
    const wrapper = mount(OptimizationPanel, {
      props: {
        optimization: null,
      },
    })

    expect(wrapper.text()).toContain('提交 Calliope 修订')
    expect(wrapper.text()).not.toContain('Manuscript')
  })
})
