// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import RevisionSummaryPanel from './RevisionSummaryPanel.vue'

describe('RevisionSummaryPanel', () => {
  afterEach(() => {
    document.body.innerHTML = ''
    vi.restoreAllMocks()
  })

  it('truncates long selected text in annotation summary title', () => {
    const longSelectedText = '新希望城的穹顶在火星的晨光中泛着金属的冷光，像一颗被强行嵌入红色大地的银钉'
    const wrapper = mount(RevisionSummaryPanel, {
      props: {
        annotations: [
          {
            id: 'annotation-1',
            paragraphIndex: 1,
            startOffset: 0,
            endOffset: longSelectedText.length,
            selectedText: longSelectedText,
            comment: '测试批注1',
          },
        ],
        corrections: [],
      },
    })

    const title = wrapper.find('.revision-summary__item-title')

    expect(title.text()).toBe('第2段 · 新希望城的穹顶在火星的晨光中泛着金属的冷光…')
    expect(title.text()).not.toContain('像一颗被强行嵌入红色大地的银钉')
    expect(wrapper.find('.revision-summary__item').attributes('title')).toBe(longSelectedText)
  })

  it('flashes the target annotation after clicking summary item', async () => {
    const target = document.createElement('mark')
    target.dataset.annotationId = 'annotation-1'
    target.scrollIntoView = vi.fn()
    document.body.appendChild(target)
    const wrapper = mount(RevisionSummaryPanel, {
      props: {
        annotations: [
          {
            id: 'annotation-1',
            paragraphIndex: 1,
            startOffset: 0,
            endOffset: 2,
            selectedText: '开头',
            comment: '测试批注1',
          },
        ],
        corrections: [],
      },
    })

    await wrapper.find('.revision-summary__item').trigger('click')

    expect(target.scrollIntoView).toHaveBeenCalledWith({ block: 'center', behavior: 'smooth' })
    expect(target.classList.contains('manuscript-editor__flash-target')).toBe(true)
  })

  it('renders correction summary as a compact inline diff', () => {
    const wrapper = mount(RevisionSummaryPanel, {
      props: {
        annotations: [],
        corrections: [
          {
            id: 'correction-1',
            paragraphIndex: 2,
            originalText: '这是很长的前置上下文，凯尔收回视线，手指无意识地摩挲旧伤。',
            correctedText: '这是很长的前置上下文，凯尔收回视线，手指无意识地握紧蓝色光晕。',
          },
        ],
      },
    })

    const correctionItem = wrapper.find('.revision-summary__item--correction')

    expect(correctionItem.find('.revision-summary__correction-original').text()).toBe('摩挲旧伤')
    expect(correctionItem.find('.revision-summary__correction-updated').text()).toBe('握紧蓝色光晕')
    expect(correctionItem.text()).toContain('…')
    expect(correctionItem.text()).not.toContain(' → ')
    expect(correctionItem.text()).not.toContain('这是很长的前置上下文，凯尔收回视线，手指无意识地摩挲旧伤。')
  })

  it('renders paragraph-split corrections as structural summaries', () => {
    const wrapper = mount(RevisionSummaryPanel, {
      props: {
        annotations: [],
        corrections: [
          {
            id: 'correction-1',
            paragraphIndex: 1,
            originalText: '稀薄的大气中蒸腾着红色的热浪',
            correctedText: '稀薄的\n\n大气中蒸腾\n\n着着\n\n红色的热浪',
          },
        ],
      },
    })

    const correctionItem = wrapper.find('.revision-summary__item--correction')

    expect(correctionItem.find('.revision-summary__item-title').text()).toBe('第2段 · 段落拆分为4段')
    expect(correctionItem.findAll('.revision-summary__split-block')).toHaveLength(4)
    expect(correctionItem.text()).toContain('稀薄的')
    expect(correctionItem.text()).toContain('大气中蒸腾')
    expect(correctionItem.find('.revision-summary__correction-updated').exists()).toBe(false)
  })

  it('shows editing shortcut hints for paragraph and line breaks', () => {
    const wrapper = mount(RevisionSummaryPanel, {
      props: {
        annotations: [],
        corrections: [],
      },
    })

    expect(wrapper.find('.revision-summary__hint').text()).toBe('Enter 新段落 · Shift+Enter 换行')
  })

  it('emits removeAnnotation without triggering summary navigation', async () => {
    const target = document.createElement('mark')
    target.dataset.annotationId = 'annotation-1'
    target.scrollIntoView = vi.fn()
    document.body.appendChild(target)
    const wrapper = mount(RevisionSummaryPanel, {
      props: {
        annotations: [
          {
            id: 'annotation-1',
            paragraphIndex: 1,
            startOffset: 0,
            endOffset: 2,
            selectedText: '开头',
            comment: '测试批注1',
          },
        ],
        corrections: [],
      },
    })

    await wrapper.find('.revision-summary__remove').trigger('click')

    expect(wrapper.emitted('removeAnnotation')).toEqual([['annotation-1']])
    expect(target.scrollIntoView).not.toHaveBeenCalled()
  })

  it('emits removeCorrection without triggering summary navigation', async () => {
    const target = document.createElement('mark')
    target.dataset.correctionId = 'correction-1'
    target.scrollIntoView = vi.fn()
    document.body.appendChild(target)
    const wrapper = mount(RevisionSummaryPanel, {
      props: {
        annotations: [],
        corrections: [
          {
            id: 'correction-1',
            paragraphIndex: 2,
            originalText: '寒风凛冽',
            correctedText: '夜风微凉',
          },
        ],
      },
    })

    await wrapper.find('.revision-summary__remove').trigger('click')

    expect(wrapper.emitted('removeCorrection')).toEqual([['correction-1']])
    expect(target.scrollIntoView).not.toHaveBeenCalled()
  })
})
