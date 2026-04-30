// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import AthenaSubnav from './AthenaSubnav.vue'
import { athenaPrimaryNav } from '../../views/athenaNavigation'

describe('AthenaSubnav', () => {
  it('renders the five primary Athena sections', () => {
    const wrapper = mount(AthenaSubnav, {
      props: {
        items: athenaPrimaryNav,
        activeSection: 'overview',
        canImportSetup: false,
        hasLatestChapter: false,
      },
    })

    expect(wrapper.findAll('button.athena-subnav__item').map((button) => button.text())).toEqual([
      '总览',
      '设定库',
      '叙事脉络',
      '真相认知',
      '待审变更',
    ])
  })

  it('emits the primary section when a nav item is clicked', async () => {
    const wrapper = mount(AthenaSubnav, {
      props: {
        items: athenaPrimaryNav,
        activeSection: 'catalog',
        canImportSetup: false,
        hasLatestChapter: false,
      },
    })

    await wrapper.findAll('button.athena-subnav__item')[2].trigger('click')

    expect(wrapper.emitted('navigate')).toEqual([['narrative']])
  })

  it('emits action events', async () => {
    const wrapper = mount(AthenaSubnav, {
      props: {
        items: athenaPrimaryNav,
        activeSection: 'overview',
        canImportSetup: true,
        hasLatestChapter: true,
      },
    })

    await wrapper.findAllComponents({ name: 'BaseButton' })[0].trigger('click')
    await wrapper.findAllComponents({ name: 'BaseButton' })[1].trigger('click')
    await wrapper.findAllComponents({ name: 'BaseButton' })[2].trigger('click')

    expect(wrapper.emitted('importSetup')).toHaveLength(1)
    expect(wrapper.emitted('analyzeLatestChapter')).toHaveLength(1)
    expect(wrapper.emitted('openChat')).toHaveLength(1)
  })
})
