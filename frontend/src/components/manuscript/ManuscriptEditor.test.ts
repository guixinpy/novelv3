// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ManuscriptEditor from './ManuscriptEditor.vue'

describe('ManuscriptEditor', () => {
  it('emits correction on blur even when input event was missed', async () => {
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: ['风吹过树林，风吹过河面。'],
        annotations: [],
        corrections: [],
      },
    })
    const paragraph = wrapper.find('.manuscript-editor__paragraph')
    paragraph.element.textContent = '风吹过树林，水纹贴着河面散开。'

    await paragraph.trigger('blur')

    expect(wrapper.emitted('addCorrection')?.[0]).toEqual([
      {
        paragraphIndex: 0,
        originalText: '风吹过树林，风吹过河面。',
        correctedText: '风吹过树林，水纹贴着河面散开。',
      },
    ])
  })
})
