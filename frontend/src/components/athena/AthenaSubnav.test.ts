// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AthenaSubnav from './AthenaSubnav.vue'

describe('AthenaSubnav', () => {
  it('emits navigation and action events', async () => {
    const wrapper = mount(AthenaSubnav, {
      props: {
        sections: [
          { label: '总览', items: [{ key: 'overview', label: '总览' }] },
          { label: '演化', items: [{ key: 'proposals', label: '提案' }] },
        ],
        activeSection: 'overview',
        canImportSetup: true,
        hasLatestChapter: true,
      },
    })

    await wrapper.findAll('button.athena-subnav__item')[0].trigger('click')
    await wrapper.findAllComponents({ name: 'BaseButton' })[0].trigger('click')
    await wrapper.findAllComponents({ name: 'BaseButton' })[1].trigger('click')
    await wrapper.findAllComponents({ name: 'BaseButton' })[2].trigger('click')

    expect(wrapper.emitted('navigate')).toEqual([['overview']])
    expect(wrapper.emitted('importSetup')).toHaveLength(1)
    expect(wrapper.emitted('analyzeLatestChapter')).toHaveLength(1)
    expect(wrapper.emitted('openChat')).toHaveLength(1)
  })
})
