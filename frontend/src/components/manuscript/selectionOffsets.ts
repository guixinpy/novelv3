export interface SelectionOffsets {
  startOffset: number
  endOffset: number
  selectedText: string
}

function textLengthBefore(container: HTMLElement, node: Node, nodeOffset: number): number | null {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT)
  let offset = 0
  let current = walker.nextNode()

  while (current) {
    if (current === node) {
      return offset + nodeOffset
    }
    offset += current.textContent?.length || 0
    current = walker.nextNode()
  }

  if (node === container) {
    return Math.min(nodeOffset, container.textContent?.length || 0)
  }

  return null
}

export function getSelectionOffsetsWithin(container: HTMLElement, selection: Selection | null): SelectionOffsets | null {
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return null

  const range = selection.getRangeAt(0)
  if (!container.contains(range.startContainer) || !container.contains(range.endContainer)) return null

  const startOffset = textLengthBefore(container, range.startContainer, range.startOffset)
  const endOffset = textLengthBefore(container, range.endContainer, range.endOffset)
  const selectedText = selection.toString().trim()
  if (startOffset === null || endOffset === null || !selectedText) return null

  return {
    startOffset: Math.min(startOffset, endOffset),
    endOffset: Math.max(startOffset, endOffset),
    selectedText,
  }
}
