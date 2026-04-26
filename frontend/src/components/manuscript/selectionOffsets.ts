export interface SelectionOffsets {
  startOffset: number
  endOffset: number
  selectedText: string
}

export interface TextNodeOffsetEntry {
  node: Text | HTMLBRElement
  startOffset: number
  endOffset: number
}

const HARD_BLOCK_BREAK_LENGTH = 2
const TEXT_BLOCK_CLASS = 'manuscript-editor__text-block'
const EMPTY_BLOCK_PLACEHOLDER_CLASS = 'manuscript-editor__empty-block-placeholder'
const ZERO_WIDTH_SPACE = '\u200B'

function isTextBlockElement(node: Node): node is Element {
  return node instanceof Element && node.classList.contains(TEXT_BLOCK_CLASS)
}

function isSoftBreakElement(node: Node): node is HTMLBRElement {
  return node.nodeName === 'BR' && !(node instanceof Element && node.classList.contains('manuscript-editor__soft-break-placeholder'))
}

function isSoftBreakPlaceholderElement(node: Node): node is Element {
  return node instanceof Element && node.classList.contains('manuscript-editor__soft-break-placeholder')
}

function isEmptyBlockPlaceholderText(node: Node) {
  return node.nodeType === Node.TEXT_NODE
    && node.parentElement?.classList.contains(EMPTY_BLOCK_PLACEHOLDER_CLASS)
}

function logicalTextLength(text: string) {
  return text.replace(new RegExp(ZERO_WIDTH_SPACE, 'g'), '').length
}

function nodeContainsTextEntry(node: Node, entry: TextNodeOffsetEntry) {
  return node === entry.node || node.contains(entry.node)
}

export function textNodeOffsetEntries(container: HTMLElement): TextNodeOffsetEntry[] {
  const entries: TextNodeOffsetEntry[] = []
  let offset = 0
  let textBlockCount = 0

  function walk(node: Node) {
    if (isSoftBreakPlaceholderElement(node)) return

    if (isTextBlockElement(node)) {
      if (textBlockCount > 0) offset += HARD_BLOCK_BREAK_LENGTH
      textBlockCount += 1
    }

    if (node.nodeType === Node.TEXT_NODE) {
      const textNode = node as Text
      const rawText = textNode.textContent || ''
      const isEmptyPlaceholder = isEmptyBlockPlaceholderText(textNode)
      if (!isEmptyPlaceholder && rawText.length === 0) return
      const textLength = isEmptyPlaceholder
        ? logicalTextLength(rawText)
        : rawText.length
      entries.push({ node: textNode, startOffset: offset, endOffset: offset + textLength })
      offset += textLength
      return
    }

    if (isSoftBreakElement(node)) {
      entries.push({ node, startOffset: offset, endOffset: offset + 1 })
      offset += 1
      return
    }

    node.childNodes.forEach(walk)
  }

  container.childNodes.forEach(walk)
  return entries
}

export function textOffsetWithin(container: HTMLElement, node: Node | null, nodeOffset: number): number | null {
  if (!node) return null

  const entries = textNodeOffsetEntries(container)
  const textEntry = entries.find((entry) => entry.node === node)
  if (textEntry) {
    const entryLength = textEntry.endOffset - textEntry.startOffset
    return textEntry.startOffset + Math.min(nodeOffset, entryLength)
  }

  if (!(node instanceof Element) || !container.contains(node)) {
    if (node === container) return Math.min(nodeOffset, entries[entries.length - 1]?.endOffset || 0)
    return null
  }

  const childNodes = Array.from(node.childNodes)
  const nextChild = childNodes[nodeOffset]
  if (nextChild) {
    const nextEntry = entries.find((entry) => nodeContainsTextEntry(nextChild, entry))
    if (nextEntry) return nextEntry.startOffset
  }

  const previousChild = childNodes[nodeOffset - 1]
  if (previousChild) {
    const previousEntries = entries.filter((entry) => nodeContainsTextEntry(previousChild, entry))
    if (previousEntries.length) return previousEntries[previousEntries.length - 1].endOffset
  }

  const nestedEntries = entries.filter((entry) => nodeContainsTextEntry(node, entry))
  if (!nestedEntries.length) return null
  return nodeOffset <= 0 ? nestedEntries[0].startOffset : nestedEntries[nestedEntries.length - 1].endOffset
}

export function getSelectionOffsetsWithin(container: HTMLElement, selection: Selection | null): SelectionOffsets | null {
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return null

  const range = selection.getRangeAt(0)
  if (!container.contains(range.startContainer) || !container.contains(range.endContainer)) return null

  const startOffset = textOffsetWithin(container, range.startContainer, range.startOffset)
  const endOffset = textOffsetWithin(container, range.endContainer, range.endOffset)
  const selectedText = selection.toString().trim()
  if (startOffset === null || endOffset === null || !selectedText) return null

  return {
    startOffset: Math.min(startOffset, endOffset),
    endOffset: Math.max(startOffset, endOffset),
    selectedText,
  }
}
