// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import ManuscriptEditor from './ManuscriptEditor.vue'


function rect(left: number, top: number, width: number, height: number): DOMRect {
  return {
    x: left,
    y: top,
    left,
    top,
    width,
    height,
    right: left + width,
    bottom: top + height,
    toJSON: () => ({}),
  } as DOMRect
}

function findTextNode(root: Node, text: string): Text {
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let current = walker.nextNode()
  while (current) {
    if (current.textContent?.includes(text)) return current as Text
    current = walker.nextNode()
  }
  throw new Error(`Text node not found: ${text}`)
}

function selectionFocusOffsetWithin(root: Node): number | null {
  const selection = window.getSelection()
  if (!selection?.focusNode) return null

  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  let offset = 0
  let current = walker.nextNode()
  while (current) {
    if (current === selection.focusNode) return offset + selection.focusOffset
    offset += current.textContent?.length || 0
    current = walker.nextNode()
  }
  return null
}

describe('ManuscriptEditor', () => {
  afterEach(() => {
    window.getSelection()?.removeAllRanges()
    document.body.innerHTML = ''
  })

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

  it('positions annotation bubble near selected text without taking layout space', async () => {
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: ['风吹过树林，风吹过河面。'],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraph = wrapper.find('.manuscript-editor__paragraph').element as HTMLElement

    const selectedText = '风吹过树林'
    const textNode = findTextNode(paragraph, selectedText)
    const range = document.createRange()
    range.setStart(textNode, textNode.textContent!.indexOf(selectedText))
    range.setEnd(textNode, textNode.textContent!.indexOf(selectedText) + selectedText.length)
    range.getBoundingClientRect = () => rect(220, 320, 80, 20)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await wrapper.find('.manuscript-editor__paragraph').trigger('mouseup')

    const bubble = wrapper.find('.annotation-bubble')
    expect(bubble.exists()).toBe(true)
    expect(bubble.attributes('style') || '').toContain('position: fixed')
    expect(bubble.attributes('style') || '').toContain('top: 348px')
    expect(bubble.attributes('style') || '').toContain('left: 260px')
    expect(getComputedStyle(bubble.element).position).toBe('fixed')

    selection.removeAllRanges()
    wrapper.unmount()
  })

  it('keeps a draft highlight after native selection is cleared by clicking the bubble', async () => {
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: ['风吹过树林，风吹过河面。'],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraph = wrapper.find('.manuscript-editor__paragraph').element as HTMLElement
    const selectedText = '风吹过树林'
    const textNode = findTextNode(paragraph, selectedText)
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.setEnd(textNode, selectedText.length)
    range.getBoundingClientRect = () => rect(220, 320, 80, 20)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await wrapper.find('.manuscript-editor__paragraph').trigger('mouseup')
    selection.removeAllRanges()
    document.dispatchEvent(new Event('selectionchange'))
    await wrapper.find('.annotation-bubble__input').trigger('pointerdown')

    expect(wrapper.find('.annotation-bubble').exists()).toBe(true)
    expect(wrapper.find('.manuscript-editor__draft-selection').text()).toBe(selectedText)
  })

  it('restores the caret to the drag end after rendering the draft highlight', async () => {
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: ['风吹过树林，风吹过河面。'],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const selectedText = '风吹过树林'
    const textNode = findTextNode(paragraph, selectedText)
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.setEnd(textNode, selectedText.length)
    range.getBoundingClientRect = () => rect(220, 320, 80, 20)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('mouseup')
    await wrapper.vm.$nextTick()

    expect(selection.isCollapsed).toBe(true)
    expect(selectionFocusOffsetWithin(paragraph)).toBe(selectedText.length)
  })

  it('closes the annotation bubble when clicking outside the editor and bubble', async () => {
    const outside = document.createElement('button')
    document.body.appendChild(outside)
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: ['风吹过树林，风吹过河面。'],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraph = wrapper.find('.manuscript-editor__paragraph').element as HTMLElement
    const selectedText = '风吹过树林'
    const textNode = findTextNode(paragraph, selectedText)
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.setEnd(textNode, selectedText.length)
    range.getBoundingClientRect = () => rect(220, 320, 80, 20)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)
    await wrapper.find('.manuscript-editor__paragraph').trigger('mouseup')

    outside.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.annotation-bubble').exists()).toBe(false)
    expect(wrapper.find('.manuscript-editor__draft-selection').exists()).toBe(false)
  })

  it('closes the annotation bubble with Escape', async () => {
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: ['风吹过树林，风吹过河面。'],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraph = wrapper.find('.manuscript-editor__paragraph').element as HTMLElement
    const selectedText = '风吹过树林'
    const textNode = findTextNode(paragraph, selectedText)
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.setEnd(textNode, selectedText.length)
    range.getBoundingClientRect = () => rect(220, 320, 80, 20)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)
    await wrapper.find('.manuscript-editor__paragraph').trigger('mouseup')

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.annotation-bubble').exists()).toBe(false)
    expect(wrapper.find('.manuscript-editor__draft-selection').exists()).toBe(false)
  })

  it('captures selection from document selectionchange for drag releases outside the paragraph', async () => {
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: ['风吹过树林，风吹过河面。'],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraph = wrapper.find('.manuscript-editor__paragraph').element as HTMLElement
    const selectedText = '风吹过树林'
    const textNode = findTextNode(paragraph, selectedText)
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.setEnd(textNode, selectedText.length)
    range.getBoundingClientRect = () => rect(220, 320, 80, 20)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    document.dispatchEvent(new Event('selectionchange'))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.annotation-bubble').exists()).toBe(true)
    expect(wrapper.find('.manuscript-editor__draft-selection').text()).toBe(selectedText)
  })

  it('keeps selection when drag ends inside the same paragraph before mouseup bubbles', async () => {
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: ['风吹过树林，风吹过河面。'],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const selectedText = '风吹过树林'
    const textNode = findTextNode(paragraph, selectedText)
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.setEnd(textNode, selectedText.length)
    range.getBoundingClientRect = () => rect(220, 320, 80, 20)
    const selection = window.getSelection()!

    paragraph.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))
    selection.removeAllRanges()
    selection.addRange(range)
    paragraph.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }))
    selection.removeAllRanges()
    await paragraphWrapper.trigger('mouseup')

    expect(wrapper.find('.annotation-bubble').exists()).toBe(true)
    expect(wrapper.find('.manuscript-editor__draft-selection').text()).toBe(selectedText)
  })

  it('truncates long selected text in annotation summary marks', () => {
    const longSelectedText = '新希望城的穹顶在火星的晨光中泛着金属的冷光，像一颗被强行嵌入红色大地的银钉'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [longSelectedText],
        annotations: [
          {
            id: 'annotation-1',
            paragraphIndex: 0,
            startOffset: 0,
            endOffset: longSelectedText.length,
            selectedText: longSelectedText,
            comment: '不错',
          },
        ],
        corrections: [],
      },
    })

    const markText = wrapper.find('.manuscript-editor__mark--annotation').text()

    expect(markText).toBe('批注：新希望城的穹顶在火星的晨光中泛着金属的冷光… · 不错')
    expect(markText).not.toContain('像一颗被强行嵌入红色大地的银钉')
  })

  it('renders target ids for summary panel flash navigation', () => {
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: ['风吹过树林。', '寒风凛冽。'],
        annotations: [
          {
            id: 'annotation-1',
            paragraphIndex: 0,
            startOffset: 0,
            endOffset: 2,
            selectedText: '风吹',
            comment: '节奏太慢',
          },
        ],
        corrections: [
          {
            id: 'correction-1',
            paragraphIndex: 1,
            originalText: '寒风凛冽。',
            correctedText: '夜风微凉。',
          },
        ],
      },
    })

    expect(wrapper.find('[data-annotation-id="annotation-1"]').exists()).toBe(true)
    expect(wrapper.find('[data-correction-id="correction-1"]').exists()).toBe(true)
  })

  it('emits the real corrected text when editing an existing diff', async () => {
    const originalText = '沃克！三号气闸的传感器又失灵了，午饭前修好它！'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [
          {
            id: 'correction-1',
            paragraphIndex: 0,
            originalText,
            correctedText: '沃克！三号气闸的传感又失灵了，午饭前修好它！',
          },
        ],
      },
    })

    const correctionMark = wrapper.find('.manuscript-editor__inline-correction')
    correctionMark.element.textContent = '器'
    await wrapper.find('.manuscript-editor__paragraph').trigger('input')
    await wrapper.find('.manuscript-editor__paragraph').trigger('blur')

    expect(wrapper.emitted('addCorrection')?.[0]).toEqual([
      {
        paragraphIndex: 0,
        originalText,
        correctedText: originalText,
      },
    ])
  })

  it('replaces selected text with typed text instead of keeping the annotation draft selection', async () => {
    const originalText = '“林舟，货到了！”'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, '货')
    const range = document.createRange()
    range.setStart(textNode, originalText.indexOf('货'))
    range.setEnd(textNode, originalText.indexOf('货') + 1)
    range.getBoundingClientRect = () => rect(220, 320, 20, 20)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    document.dispatchEvent(new Event('selectionchange'))
    await wrapper.vm.$nextTick()
    paragraph.dispatchEvent(new InputEvent('beforeinput', {
      bubbles: true,
      cancelable: true,
      inputType: 'insertText',
      data: '人来了',
    }))
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('blur')

    expect(wrapper.find('.annotation-bubble').exists()).toBe(false)
    expect(wrapper.find('.manuscript-editor__draft-selection').exists()).toBe(false)
    expect(wrapper.emitted('addCorrection')?.[0]).toEqual([
      {
        paragraphIndex: 0,
        originalText,
        correctedText: '“林舟，人来了到了！”',
      },
    ])
  })

  it('deletes selected text with Backspace instead of emitting a duplicated correction', async () => {
    const originalText = '“林舟，货到了！”'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, '货')
    const range = document.createRange()
    range.setStart(textNode, originalText.indexOf('货'))
    range.setEnd(textNode, originalText.indexOf('货') + 1)
    range.getBoundingClientRect = () => rect(220, 320, 20, 20)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    document.dispatchEvent(new Event('selectionchange'))
    await wrapper.vm.$nextTick()
    paragraph.dispatchEvent(new InputEvent('beforeinput', {
      bubbles: true,
      cancelable: true,
      inputType: 'deleteContentBackward',
      data: null,
    }))
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('blur')

    expect(wrapper.emitted('addCorrection')?.[0]).toEqual([
      {
        paragraphIndex: 0,
        originalText,
        correctedText: '“林舟，到了！”',
      },
    ])
  })

  it('uses Enter to insert a paragraph break into the corrected text', async () => {
    const originalText = '沃克！三号气闸的传感器又失灵了，午饭前修好它！'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, '传感器')
    const range = document.createRange()
    range.setStart(textNode, originalText.indexOf('又失灵'))
    range.collapse(true)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('keydown', { key: 'Enter' })
    const updatedParagraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    expect(updatedParagraphWrapper.classes()).toContain('manuscript-editor__paragraph--block-break')
    const textBlocks = wrapper.findAll('.manuscript-editor__text-block')
    expect(textBlocks).toHaveLength(2)
    expect(textBlocks[0].text()).toBe('沃克！三号气闸的传感器')
    expect(textBlocks[1].text()).toBe('又失灵了，午饭前修好它！')
    await updatedParagraphWrapper.trigger('blur')

    expect(wrapper.emitted('addCorrection')?.[0]).toEqual([
      {
        paragraphIndex: 0,
        originalText,
        correctedText: '沃克！三号气闸的传感器\n\n又失灵了，午饭前修好它！',
      },
    ])
  })

  it('keeps the caret in the leading empty paragraph when Enter is pressed at paragraph start', async () => {
    const originalText = '新希望城的穹顶在火星的晨光中泛着金属的冷光'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, '新希望城')
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.collapse(true)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()

    const textBlocks = wrapper.findAll('.manuscript-editor__text-block')
    expect(textBlocks).toHaveLength(2)
    expect(textBlocks[0].find('.manuscript-editor__empty-block-placeholder').exists()).toBe(true)
    const focusElement = selection.focusNode instanceof Element
      ? selection.focusNode
      : selection.focusNode?.parentNode instanceof Element
        ? selection.focusNode.parentNode
        : null
    expect(focusElement?.closest('.manuscript-editor__text-block')).toBe(textBlocks[0].element)
    expect(selectionFocusOffsetWithin(wrapper.find('.manuscript-editor__paragraph').element)).toBe(0)
    await wrapper.find('.manuscript-editor__paragraph').trigger('blur')
    expect(wrapper.emitted('addCorrection')?.[0]).toEqual([
      {
        paragraphIndex: 0,
        originalText,
        correctedText: `\n\n${originalText}`,
      },
    ])
  })

  it('keeps consecutive Enter presses at paragraph start as separate empty paragraphs', async () => {
    const originalText = '新希望城的穹顶在火星的晨光中泛着金属的冷光'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, '新希望城')
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.collapse(true)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()

    const textBlocks = wrapper.findAll('.manuscript-editor__text-block')
    expect(textBlocks).toHaveLength(3)
    expect(textBlocks[0].find('.manuscript-editor__empty-block-placeholder').exists()).toBe(true)
    expect(textBlocks[1].find('.manuscript-editor__empty-block-placeholder').exists()).toBe(true)
    expect(textBlocks[2].text()).toBe(originalText)
    expect(selectionFocusOffsetWithin(wrapper.find('.manuscript-editor__paragraph').element)).toBe(0)
    await wrapper.find('.manuscript-editor__paragraph').trigger('blur')
    expect(wrapper.emitted('addCorrection')?.[0]).toEqual([
      {
        paragraphIndex: 0,
        originalText,
        correctedText: `\n\n\n\n${originalText}`,
      },
    ])
  })

  it('removes consecutive paragraph breaks with Backspace without duplicating following text', async () => {
    const originalText = '雾港城的夜晚总是来得格外早。下午四点刚过，雾气就从河面上升起。'
    const prefix = '雾港城的'
    const suffix = originalText.slice(prefix.length)
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, prefix)
    const range = document.createRange()
    range.setStart(textNode, prefix.length)
    range.collapse(true)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Backspace' })
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Backspace' })
    await wrapper.vm.$nextTick()

    const textBlocks = wrapper.findAll('.manuscript-editor__text-block')
    expect(textBlocks).toHaveLength(2)
    expect(textBlocks[0].text()).toBe(prefix)
    expect(textBlocks[1].text()).toBe(suffix)
    expect(textBlocks[1].text().indexOf(suffix)).toBe(textBlocks[1].text().lastIndexOf(suffix))
    await wrapper.find('.manuscript-editor__paragraph').trigger('blur')
    expect(wrapper.emitted('addCorrection')?.[0]).toEqual([
      {
        paragraphIndex: 0,
        originalText,
        correctedText: `${prefix}\n\n${suffix}`,
      },
    ])
  })

  it('merges consecutive paragraph breaks back to original text with Backspace', async () => {
    const originalText = '雾港城的夜晚总是来得格外早。下午四点刚过，雾气就从河面上升起。'
    const prefix = '雾港城的'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, prefix)
    const range = document.createRange()
    range.setStart(textNode, prefix.length)
    range.collapse(true)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Backspace' })
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Backspace' })
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Backspace' })
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.manuscript-editor__text-block')).toHaveLength(1)
    expect(wrapper.find('.manuscript-editor__text-block').text()).toBe(originalText)
    await wrapper.find('.manuscript-editor__paragraph').trigger('blur')
    expect(wrapper.emitted('addCorrection')).toBeUndefined()
  })

  it('removes leading empty paragraphs with Backspace when the caret is inside the empty block', async () => {
    const originalText = '新希望城的穹顶在火星的晨光中泛着金属的冷光'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, '新希望城')
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.collapse(true)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()
    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Backspace' })
    await wrapper.vm.$nextTick()

    let textBlocks = wrapper.findAll('.manuscript-editor__text-block')
    expect(textBlocks).toHaveLength(2)
    expect(textBlocks[0].find('.manuscript-editor__empty-block-placeholder').exists()).toBe(true)
    expect(textBlocks[1].text()).toBe(originalText)
    expect(selectionFocusOffsetWithin(wrapper.find('.manuscript-editor__paragraph').element)).toBe(0)

    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Backspace' })
    await wrapper.vm.$nextTick()

    textBlocks = wrapper.findAll('.manuscript-editor__text-block')
    expect(textBlocks).toHaveLength(1)
    expect(textBlocks[0].text()).toBe(originalText)
    expect(selectionFocusOffsetWithin(wrapper.find('.manuscript-editor__paragraph').element)).toBe(0)
  })

  it('removes a following paragraph break with Delete without duplicating following text', async () => {
    const originalText = '雾港城的夜晚总是来得格外早。'
    const prefix = '雾港城的'
    const suffix = originalText.slice(prefix.length)
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, prefix)
    const range = document.createRange()
    range.setStart(textNode, prefix.length)
    range.collapse(true)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('keydown', { key: 'Enter' })
    await wrapper.vm.$nextTick()
    const prefixNode = findTextNode(wrapper.find('.manuscript-editor__paragraph').element, prefix)
    const deleteRange = document.createRange()
    deleteRange.setStart(prefixNode, prefix.length)
    deleteRange.collapse(true)
    selection.removeAllRanges()
    selection.addRange(deleteRange)

    await wrapper.find('.manuscript-editor__paragraph').trigger('keydown', { key: 'Delete' })
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.manuscript-editor__text-block')).toHaveLength(1)
    expect(wrapper.find('.manuscript-editor__text-block').text()).toBe(`${prefix}${suffix}`)
  })

  it('renders unchanged paragraph-split text as plain layout instead of inserted text', () => {
    const originalText = '地平线外，未改造的荒野'
    const correctedText = '地平线外，\n\n未改\n\n造的荒野'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [
          {
            id: 'correction-1',
            paragraphIndex: 0,
            originalText,
            correctedText,
          },
        ],
      },
    })

    expect(wrapper.find('.manuscript-editor__inline-original').exists()).toBe(false)
    expect(wrapper.find('.manuscript-editor__inline-correction').exists()).toBe(false)
    expect(wrapper.findAll('.manuscript-editor__paragraph-break-marker')).toHaveLength(2)
    const textBlocks = wrapper.findAll('.manuscript-editor__text-block')
    expect(textBlocks).toHaveLength(3)
    expect(textBlocks[0].text()).toBe('地平线外，')
    expect(textBlocks[1].text()).toContain('未改')
    expect(textBlocks[2].text()).toBe('造的荒野')
  })

  it('renders repeated paragraph breaks as separate structural blocks without marking unchanged text inserted', () => {
    const originalText = '地平线外，未改造的荒野'
    const correctedText = '地平线外，\n\n\n\n未改\n\n\n\n造的荒野'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [
          {
            id: 'correction-1',
            paragraphIndex: 0,
            originalText,
            correctedText,
          },
        ],
      },
    })

    expect(wrapper.find('.manuscript-editor__inline-original').exists()).toBe(false)
    expect(wrapper.find('.manuscript-editor__inline-correction').exists()).toBe(false)
    expect(wrapper.findAll('.manuscript-editor__paragraph-break-marker')).toHaveLength(4)
    const textBlocks = wrapper.findAll('.manuscript-editor__text-block')
    expect(textBlocks).toHaveLength(5)
    expect(textBlocks[0].text()).toBe('地平线外，')
    expect(textBlocks[1].find('.manuscript-editor__empty-block-placeholder').exists()).toBe(true)
    expect(textBlocks[2].text()).toBe('未改')
    expect(textBlocks[3].find('.manuscript-editor__empty-block-placeholder').exists()).toBe(true)
    expect(textBlocks[4].text()).toBe('造的荒野')
  })

  it('only highlights newly inserted text when paragraph breaks wrap unchanged text', () => {
    const originalText = '稀薄的大气中蒸腾着红色的热浪'
    const correctedText = '稀薄的\n\n大气中蒸腾\n\n着着\n\n红色的热浪'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [
          {
            id: 'correction-1',
            paragraphIndex: 0,
            originalText,
            correctedText,
          },
        ],
      },
    })

    expect(wrapper.find('.manuscript-editor__inline-original').exists()).toBe(false)
    expect(wrapper.find('.manuscript-editor__inline-correction').text()).toBe('着')
    expect(wrapper.findAll('.manuscript-editor__paragraph-break-marker')).toHaveLength(3)
    const textBlocks = wrapper.findAll('.manuscript-editor__text-block')
    expect(textBlocks).toHaveLength(4)
    expect(textBlocks[0].text()).toBe('稀薄的')
    expect(textBlocks[1].text()).toContain('大气中蒸腾')
    expect(textBlocks[2].text()).toContain('着着')
    expect(textBlocks[3].text()).toBe('红色的热浪')
  })

  it('uses Shift+Enter to insert a soft line break into the corrected text', async () => {
    const originalText = '沃克！三号气闸的传感器又失灵了，午饭前修好它！'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, '传感器')
    const range = document.createRange()
    range.setStart(textNode, originalText.indexOf('又失灵'))
    range.collapse(true)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('keydown', { key: 'Enter', shiftKey: true })
    expect(paragraphWrapper.classes()).not.toContain('manuscript-editor__paragraph--block-break')
    expect(wrapper.find('.manuscript-editor__text-block').element.textContent).toBe('沃克！三号气闸的传感器\n又失灵了，午饭前修好它！')
    await paragraphWrapper.trigger('blur')

    expect(wrapper.emitted('addCorrection')?.[0]).toEqual([
      {
        paragraphIndex: 0,
        originalText,
        correctedText: '沃克！三号气闸的传感器\n又失灵了，午饭前修好它！',
      },
    ])
  })

  it('keeps a Shift+Enter soft line break after a component rerender', async () => {
    const originalText = '沃克！三号气闸的传感器又失灵了，午饭前修好它！'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, '传感器')
    const range = document.createRange()
    range.setStart(textNode, originalText.indexOf('又失灵'))
    range.collapse(true)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('keydown', { key: 'Enter', shiftKey: true })
    await wrapper.setProps({ title: '第一章-刷新' })

    const textBlock = wrapper.find('.manuscript-editor__text-block').element as HTMLElement
    expect(textBlock.textContent).toBe('沃克！三号气闸的传感器\n又失灵了，午饭前修好它！')
    expect(wrapper.findAll('.manuscript-editor__text-block')).toHaveLength(1)
    expect(wrapper.find('.manuscript-editor__paragraph').classes()).not.toContain('manuscript-editor__paragraph--block-break')
  })

  it('renders Shift+Enter at the paragraph end as a visible soft break', async () => {
    const originalText = '沃克！三号气闸的传感器又失灵了'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, '传感器')
    const range = document.createRange()
    range.setStart(textNode, originalText.length)
    range.collapse(true)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('keydown', { key: 'Enter', shiftKey: true })

    expect(wrapper.find('.manuscript-editor__soft-break-placeholder').exists()).toBe(true)
    await wrapper.find('.manuscript-editor__paragraph').trigger('blur')
    expect(wrapper.emitted('addCorrection')?.[0]).toEqual([
      {
        paragraphIndex: 0,
        originalText,
        correctedText: `${originalText}\n`,
      },
    ])
  })

  it('keeps focus after Shift+Enter creates a soft line break', async () => {
    const originalText = '沃克！三号气闸的传感器又失灵了'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    paragraph.focus()
    const textNode = findTextNode(paragraph, '传感器')
    const range = document.createRange()
    range.setStart(textNode, originalText.length)
    range.collapse(true)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('keydown', { key: 'Enter', shiftKey: true })
    await wrapper.vm.$nextTick()

    expect(document.activeElement).toBe(wrapper.find('.manuscript-editor__paragraph').element)
  })

  it('does not render a trailing soft-break placeholder when text follows the break', async () => {
    const originalText = '沃克！三号气闸的传感器又失灵了'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [],
      },
      attachTo: document.body,
    })
    const paragraphWrapper = wrapper.find('.manuscript-editor__paragraph')
    const paragraph = paragraphWrapper.element as HTMLElement
    const textNode = findTextNode(paragraph, '传感器')
    const range = document.createRange()
    range.setStart(textNode, originalText.indexOf('又失灵'))
    range.collapse(true)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    await paragraphWrapper.trigger('keydown', { key: 'Enter', shiftKey: true })

    expect(wrapper.find('.manuscript-editor__text-block').element.textContent).toBe('沃克！三号气闸的传感器\n又失灵了')
    expect(wrapper.find('.manuscript-editor__soft-break-placeholder').exists()).toBe(false)
  })

  it('renders persisted middle soft line break without dropping following text', () => {
    const originalText = '沃克！三号气闸的传感器又失灵了，午饭前修好它！'
    const correctedText = '沃克！三号气闸的传感器\n又失灵了，午饭前修好它！'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [
          {
            id: 'correction-1',
            paragraphIndex: 0,
            originalText,
            correctedText,
          },
        ],
      },
    })

    const textBlock = wrapper.find('.manuscript-editor__text-block').element

    expect(textBlock.textContent).toBe(correctedText)
    expect(wrapper.find('.manuscript-editor__soft-break-placeholder').exists()).toBe(false)
    expect(wrapper.find('.manuscript-editor__paragraph').text()).toContain('又失灵了，午饭前修好它！')
  })

  it('marks persisted paragraph-break corrections for separated focus styling', () => {
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: ['沃克！三号气闸的传感器又失灵了，午饭前修好它！'],
        annotations: [],
        corrections: [
          {
            id: 'correction-1',
            paragraphIndex: 0,
            originalText: '沃克！三号气闸的传感器又失灵了，午饭前修好它！',
            correctedText: '沃克！三号气闸的传感器\n\n又失灵了，午饭前修好它！',
          },
        ],
      },
    })

    expect(wrapper.find('.manuscript-editor__paragraph').classes()).toContain('manuscript-editor__paragraph--block-break')
    const textBlocks = wrapper.findAll('.manuscript-editor__text-block')
    expect(textBlocks).toHaveLength(2)
    expect(textBlocks[0].text()).toBe('沃克！三号气闸的传感器')
    expect(textBlocks[1].text()).toBe('又失灵了，午饭前修好它！')
  })

  it('keeps accidental text inserted inside a deleted marker as inserted text', async () => {
    const originalText = '沃克！三号气闸的传感器又失灵了，午饭前修好它！'
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: [originalText],
        annotations: [],
        corrections: [
          {
            id: 'correction-1',
            paragraphIndex: 0,
            originalText,
            correctedText: '沃克！三号气闸的传感又失灵了，午饭前修好它！',
          },
        ],
      },
    })

    const originalMarker = wrapper.find('.manuscript-editor__inline-original')
    originalMarker.element.textContent = '器又哈哈哈'
    await wrapper.find('.manuscript-editor__paragraph').trigger('input')
    await wrapper.find('.manuscript-editor__paragraph').trigger('blur')

    expect(wrapper.emitted('addCorrection')?.[0]).toEqual([
      {
        paragraphIndex: 0,
        originalText,
        correctedText: '沃克！三号气闸的传感又哈哈哈又失灵了，午饭前修好它！',
      },
    ])
  })

  it('renders deleted correction text as non-editable', () => {
    const wrapper = mount(ManuscriptEditor, {
      props: {
        title: '第一章',
        paragraphs: ['沃克！三号气闸的传感器又失灵了，午饭前修好它！'],
        annotations: [],
        corrections: [
          {
            id: 'correction-1',
            paragraphIndex: 0,
            originalText: '沃克！三号气闸的传感器又失灵了，午饭前修好它！',
            correctedText: '沃克！三号气闸的传感又失灵了，午饭前修好它！',
          },
        ],
      },
    })

    const originalMarker = wrapper.find('.manuscript-editor__inline-original')

    expect(originalMarker.attributes('contenteditable')).toBe('false')
    expect(originalMarker.attributes('data-original-text')).toBe('器')
  })
})
