// @vitest-environment jsdom
import { describe, expect, it } from 'vitest'
import { getSelectionOffsetsWithin } from './selectionOffsets'

describe('getSelectionOffsetsWithin', () => {
  it('returns offsets for the actual selected occurrence when text repeats', () => {
    const paragraph = document.createElement('p')
    paragraph.textContent = '风吹过树林，风吹过河面。'
    document.body.appendChild(paragraph)

    const textNode = paragraph.firstChild as Text
    const secondStart = paragraph.textContent!.lastIndexOf('风吹')
    const range = document.createRange()
    range.setStart(textNode, secondStart)
    range.setEnd(textNode, secondStart + 2)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    const offsets = getSelectionOffsetsWithin(paragraph, selection)

    expect(offsets).toEqual({ startOffset: secondStart, endOffset: secondStart + 2, selectedText: '风吹' })
    selection.removeAllRanges()
    paragraph.remove()
  })

  it('counts visual text block boundaries as hard paragraph breaks', () => {
    const paragraph = document.createElement('p')
    const firstBlock = document.createElement('span')
    firstBlock.className = 'manuscript-editor__text-block'
    firstBlock.textContent = '第一段'
    const secondBlock = document.createElement('span')
    secondBlock.className = 'manuscript-editor__text-block'
    secondBlock.textContent = '第二段'
    paragraph.append(firstBlock, secondBlock)
    document.body.appendChild(paragraph)

    const textNode = secondBlock.firstChild as Text
    const range = document.createRange()
    range.setStart(textNode, 0)
    range.setEnd(textNode, 2)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    const offsets = getSelectionOffsetsWithin(paragraph, selection)

    expect(offsets).toEqual({ startOffset: 5, endOffset: 7, selectedText: '第二' })
    selection.removeAllRanges()
    paragraph.remove()
  })

  it('returns null when selection is outside the paragraph', () => {
    const paragraph = document.createElement('p')
    paragraph.textContent = '正文'
    const outside = document.createElement('span')
    outside.textContent = '外部'
    document.body.append(paragraph, outside)

    const range = document.createRange()
    range.selectNodeContents(outside)
    const selection = window.getSelection()!
    selection.removeAllRanges()
    selection.addRange(range)

    expect(getSelectionOffsetsWithin(paragraph, selection)).toBeNull()
    selection.removeAllRanges()
    paragraph.remove()
    outside.remove()
  })
})
