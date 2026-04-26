<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import AnnotationBubble from './AnnotationBubble.vue'
import { getSelectionOffsetsWithin, textNodeOffsetEntries, textOffsetWithin } from './selectionOffsets'
import { buildCorrectionRenderSegments, buildParagraphSegments } from './revisionRender'
import { annotationSelectionPreview } from './annotationPreview'
import type { LocalAnnotation, LocalCorrection } from '../../stores/manuscript'
import type { CorrectionRenderSegment, ParagraphSegment } from './revisionRender'

interface AnnotationBubblePosition {
  top: number
  left: number
}

const props = defineProps<{
  title: string
  paragraphs: string[]
  annotations: LocalAnnotation[]
  corrections: LocalCorrection[]
}>()

const emit = defineEmits<{
  addAnnotation: [payload: { paragraphIndex: number; startOffset: number; endOffset: number; selectedText: string; comment: string }]
  addCorrection: [payload: { paragraphIndex: number; originalText: string; correctedText: string }]
}>()

const BUBBLE_WIDTH = 320
const BUBBLE_VERTICAL_OFFSET = 8
const BUBBLE_SCREEN_PADDING = 16
const ZERO_WIDTH_SPACE = '\u200B'
const HARD_PARAGRAPH_BREAK = '\n\n'

type DraftParagraphSegment = ParagraphSegment | { type: 'draft'; text: string }
type ManuscriptInlineSegment = DraftParagraphSegment | CorrectionRenderSegment

interface ParagraphRenderBlock {
  segments: ManuscriptInlineSegment[]
  startsWithStructuralBreak?: boolean
}

const editorRef = ref<HTMLElement | null>(null)
const activeSelection = ref<{ paragraphIndex: number; startOffset: number; endOffset: number; selectedText: string; caretOffset: number; bubblePosition: AnnotationBubblePosition } | null>(null)
const editableText = ref<Record<number, string>>({})
const annotationText = computed(() => activeSelection.value?.selectedText || '')
const annotationPosition = computed(() => activeSelection.value?.bubblePosition || null)
let isPointerSelecting = false
let preserveSelectionOnNextMouseup = false

function paragraphAnnotations(index: number) {
  return props.annotations.filter((item) => item.paragraphIndex === index)
}

function paragraphSegments(index: number) {
  return buildParagraphSegments(props.paragraphs[index], paragraphAnnotations(index))
}

function segmentWithText(segment: ParagraphSegment, text: string): ParagraphSegment {
  return segment.type === 'annotation'
    ? { type: 'annotation', text, annotation: segment.annotation }
    : { type: 'text', text }
}

function withDraftSelection(segments: ParagraphSegment[], startOffset: number, endOffset: number): DraftParagraphSegment[] {
  const renderedSegments: DraftParagraphSegment[] = []
  let cursor = 0

  for (const segment of segments) {
    const segmentStart = cursor
    const segmentEnd = cursor + segment.text.length
    const selectionStart = Math.max(startOffset, segmentStart)
    const selectionEnd = Math.min(endOffset, segmentEnd)

    if (selectionStart >= selectionEnd) {
      renderedSegments.push(segment)
    } else {
      if (selectionStart > segmentStart) {
        renderedSegments.push(segmentWithText(segment, segment.text.slice(0, selectionStart - segmentStart)))
      }
      renderedSegments.push({
        type: 'draft',
        text: segment.text.slice(selectionStart - segmentStart, selectionEnd - segmentStart),
      })
      if (selectionEnd < segmentEnd) {
        renderedSegments.push(segmentWithText(segment, segment.text.slice(selectionEnd - segmentStart)))
      }
    }

    cursor = segmentEnd
  }

  return renderedSegments
}

function paragraphRenderSegments(index: number): DraftParagraphSegment[] {
  const segments = paragraphSegments(index)
  const selection = activeSelection.value
  if (!selection || selection.paragraphIndex !== index) return segments
  return withDraftSelection(segments, selection.startOffset, selection.endOffset)
}

function paragraphCorrection(index: number) {
  return props.corrections.find((item) => item.paragraphIndex === index) || null
}

function paragraphVisualText(index: number) {
  return editableText.value[index] ?? paragraphCorrection(index)?.correctedText ?? props.paragraphs[index] ?? ''
}

function segmentWithRenderedText(segment: ManuscriptInlineSegment, text: string): ManuscriptInlineSegment {
  if (segment.type === 'annotation') return { type: 'annotation', text, annotation: segment.annotation }
  return { ...segment, text }
}

function pushTextIntoCurrentBlock(blocks: ParagraphRenderBlock[], segment: ManuscriptInlineSegment, text: string) {
  if (!text) return
  blocks[blocks.length - 1].segments.push(segmentWithRenderedText(segment, text))
}

function pushNewBlock(blocks: ParagraphRenderBlock[], startsWithStructuralBreak = false) {
  blocks.push({ segments: [], startsWithStructuralBreak })
}

function splitSegmentsIntoBlocks(segments: ManuscriptInlineSegment[]): ParagraphRenderBlock[] {
  const blocks: ParagraphRenderBlock[] = [{ segments: [] }]

  for (const segment of segments) {
    if (!segment.text) {
      if (segment.type === 'correction') blocks[blocks.length - 1].segments.push(segment)
      continue
    }

    let cursor = 0
    while (cursor < segment.text.length) {
      const breakStart = segment.text.indexOf('\n', cursor)
      if (breakStart < 0) {
        pushTextIntoCurrentBlock(blocks, segment, segment.text.slice(cursor))
        break
      }

      pushTextIntoCurrentBlock(blocks, segment, segment.text.slice(cursor, breakStart))

      let breakEnd = breakStart
      while (breakEnd < segment.text.length && segment.text[breakEnd] === '\n') {
        breakEnd += 1
      }

      const hardBreaks = Math.floor((breakEnd - breakStart) / 2)
      for (let index = 0; index < hardBreaks; index += 1) {
        pushNewBlock(blocks, segment.type === 'layout')
      }
      if ((breakEnd - breakStart) % 2 === 1) {
        pushTextIntoCurrentBlock(blocks, segment, '\n')
      }

      cursor = breakEnd
    }
  }

  return blocks
}

function paragraphHasBlockBreak(index: number) {
  return /\n{2,}/.test(paragraphVisualText(index))
}

function paragraphRenderKey(index: number) {
  const correction = paragraphCorrection(index)
  return correction
    ? `${index}:correction:${correction.id}:${correction.originalText}:${correction.correctedText}`
    : `${index}:plain:${props.paragraphs[index]}`
}

function paragraphInlineSegments(index: number): ManuscriptInlineSegment[] {
  const draftText = editableText.value[index]
  if (draftText !== undefined) return [{ type: 'text', text: draftText }]

  const correction = paragraphCorrection(index)
  if (correction) return buildCorrectionRenderSegments(correction)

  return paragraphRenderSegments(index)
}

function paragraphRenderBlocks(index: number) {
  return splitSegmentsIntoBlocks(paragraphInlineSegments(index))
}

function blockText(block: ParagraphRenderBlock) {
  return block.segments.map((segment) => segment.text).join('')
}

function blockEndsWithSoftBreak(block: ParagraphRenderBlock) {
  return blockText(block).endsWith('\n')
}

function blockIsEmpty(block: ParagraphRenderBlock) {
  return block.segments.length === 0
}

function clampBubbleLeft(left: number, viewportWidth: number) {
  const minLeft = Math.min(BUBBLE_WIDTH / 2 + BUBBLE_SCREEN_PADDING, viewportWidth / 2)
  const maxLeft = Math.max(minLeft, viewportWidth - minLeft)
  return Math.min(Math.max(left, minLeft), maxLeft)
}

function getBubblePosition(range: Range): AnnotationBubblePosition {
  const rangeRect = range.getBoundingClientRect()
  const rawLeft = rangeRect.left + rangeRect.width / 2
  return {
    top: Math.max(BUBBLE_SCREEN_PADDING, rangeRect.bottom + BUBBLE_VERTICAL_OFFSET),
    left: clampBubbleLeft(rawLeft, window.innerWidth),
  }
}

function getSelectionFocusOffsetWithin(container: HTMLElement, selection: Selection) {
  return textOffsetWithin(container, selection.focusNode, selection.focusOffset)
}

function editorParagraphs() {
  return Array.from(editorRef.value?.querySelectorAll<HTMLElement>('.manuscript-editor__paragraph') || [])
}

function paragraphElementAt(index: number) {
  return editorParagraphs().find((paragraph) => Number(paragraph.dataset.paragraphIndex) === index) || null
}

function setCaretAtTextOffset(container: HTMLElement, targetOffset: number) {
  const selection = window.getSelection()
  if (!selection) return

  const range = document.createRange()
  const entries = textNodeOffsetEntries(container)

  for (const entry of entries) {
    if (targetOffset <= entry.startOffset) {
      if (entry.node.nodeType === Node.TEXT_NODE) {
        range.setStart(entry.node, 0)
      } else {
        range.setStartBefore(entry.node)
      }
      range.collapse(true)
      selection.removeAllRanges()
      selection.addRange(range)
      return
    }

    if (targetOffset <= entry.endOffset) {
      if (entry.node.nodeType === Node.TEXT_NODE) {
        range.setStart(entry.node, Math.max(0, targetOffset - entry.startOffset))
      } else {
        range.setStartAfter(entry.node)
      }
      range.collapse(true)
      selection.removeAllRanges()
      selection.addRange(range)
      return
    }
  }

  const lastEntry = entries[entries.length - 1] || null
  if (lastEntry?.node.nodeType === Node.TEXT_NODE) {
    range.setStart(lastEntry.node, lastEntry.node.textContent?.length || 0)
  } else if (lastEntry) {
    range.setStartAfter(lastEntry.node)
  } else {
    range.selectNodeContents(container)
    range.collapse(false)
  }
  selection.removeAllRanges()
  selection.addRange(range)
}

function restoreEditableCaretAfterRender(paragraphIndex: number, caretOffset: number | null) {
  if (caretOffset === null) return

  nextTick(() => {
    const paragraph = paragraphElementAt(paragraphIndex)
    if (!paragraph) return
    paragraph.focus()
    setCaretAtTextOffset(paragraph, caretOffset)
  })
}

function restoreCaretAfterRender(paragraphIndex: number, caretOffset: number) {
  nextTick(() => {
    const selection = activeSelection.value
    if (!selection || selection.paragraphIndex !== paragraphIndex || selection.caretOffset !== caretOffset) return

    const paragraph = paragraphElementAt(paragraphIndex)
    if (!paragraph) return
    setCaretAtTextOffset(paragraph, caretOffset)
  })
}

function setActiveSelection(paragraphIndex: number, offsets: { startOffset: number; endOffset: number; selectedText: string }, range: Range, caretOffset = offsets.endOffset) {
  activeSelection.value = {
    paragraphIndex,
    ...offsets,
    caretOffset,
    bubblePosition: getBubblePosition(range),
  }
  restoreCaretAfterRender(paragraphIndex, caretOffset)
}

function captureSelectionFromDocument() {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed || !editorRef.value) return false

  const paragraphs = editorParagraphs()
  for (const paragraph of paragraphs) {
    const offsets = getSelectionOffsetsWithin(paragraph, selection)
    if (!offsets) continue

    const paragraphIndex = Number(paragraph.dataset.paragraphIndex)
    if (!Number.isInteger(paragraphIndex)) continue

    setActiveSelection(paragraphIndex, offsets, selection.getRangeAt(0), getSelectionFocusOffsetWithin(paragraph, selection) ?? offsets.endOffset)
    return true
  }

  return false
}

function onMouseup(paragraphIndex: number, event: MouseEvent) {
  const selection = window.getSelection()
  const paragraph = event.currentTarget as HTMLElement
  const offsets = getSelectionOffsetsWithin(paragraph, selection)
  if (!offsets || !selection || selection.rangeCount === 0) {
    if (preserveSelectionOnNextMouseup) {
      preserveSelectionOnNextMouseup = false
      return
    }
    activeSelection.value = null
    return
  }
  preserveSelectionOnNextMouseup = false
  setActiveSelection(paragraphIndex, offsets, selection.getRangeAt(0), getSelectionFocusOffsetWithin(paragraph, selection) ?? offsets.endOffset)
}

function onInput(paragraphIndex: number, event: Event) {
  const target = event.target as HTMLElement
  const selection = window.getSelection()
  const caretOffset = selection ? getSelectionFocusOffsetWithin(target, selection) : null
  const correctedText = editableParagraphText(target)
  if (editableText.value[paragraphIndex] !== undefined || /\n/.test(correctedText)) {
    editableText.value[paragraphIndex] = correctedText
  }
  if (/\n/.test(correctedText)) restoreEditableCaretAfterRender(paragraphIndex, caretOffset)
}

function replaceActiveSelectionText(paragraphIndex: number, target: HTMLElement, replacementText: string, caretOffset?: number) {
  const selection = activeSelection.value
  if (!selection || selection.paragraphIndex !== paragraphIndex) return false

  const currentText = editableParagraphText(target)
  const correctedText = `${currentText.slice(0, selection.startOffset)}${replacementText}${currentText.slice(selection.endOffset)}`
  activeSelection.value = null
  editableText.value[paragraphIndex] = correctedText
  restoreEditableCaretAfterRender(paragraphIndex, caretOffset ?? selection.startOffset + replacementText.length)
  return true
}

function inputEventReplacementText(event: InputEvent) {
  if (event.inputType === 'insertText' || event.inputType === 'insertCompositionText') return event.data ?? ''
  if (event.inputType === 'insertFromPaste') return event.dataTransfer?.getData('text/plain') ?? event.data ?? ''
  if (event.inputType === 'deleteContentBackward' || event.inputType === 'deleteContentForward' || event.inputType === 'deleteByCut') return ''
  return null
}

function onBeforeInput(paragraphIndex: number, event: InputEvent) {
  const replacementText = inputEventReplacementText(event)
  if (replacementText === null) return

  const target = event.currentTarget as HTMLElement
  if (!replaceActiveSelectionText(paragraphIndex, target, replacementText)) return
  event.preventDefault()
}

function textWithInsertionAtSelection(target: HTMLElement, text: string) {
  const currentText = editableParagraphText(target)
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) {
    return {
      text: `${currentText}${text}`,
      caretOffset: currentText.length + text.length,
      replaceStart: currentText.length,
    }
  }

  const range = selection.getRangeAt(0)
  if (!target.contains(range.commonAncestorContainer)) return null

  const startOffset = textOffsetWithin(target, range.startContainer, range.startOffset)
  const endOffset = textOffsetWithin(target, range.endContainer, range.endOffset)
  if (startOffset === null || endOffset === null) return null

  const replaceStart = Math.min(startOffset, endOffset)
  const replaceEnd = Math.max(startOffset, endOffset)
  return {
    text: `${currentText.slice(0, replaceStart)}${text}${currentText.slice(replaceEnd)}`,
    caretOffset: replaceStart + text.length,
    replaceStart,
  }
}

function textRangeWithinSelection(target: HTMLElement) {
  const selection = window.getSelection()
  if (!selection || selection.rangeCount === 0) return null

  const range = selection.getRangeAt(0)
  if (!target.contains(range.commonAncestorContainer)) return null

  const startOffset = textOffsetWithin(target, range.startContainer, range.startOffset)
  const endOffset = textOffsetWithin(target, range.endContainer, range.endOffset)
  if (startOffset === null || endOffset === null) return null

  return {
    startOffset: Math.min(startOffset, endOffset),
    endOffset: Math.max(startOffset, endOffset),
  }
}

function deletionRangeForKey(text: string, startOffset: number, endOffset: number, key: string) {
  if (startOffset !== endOffset) return { startOffset, endOffset }

  if (key === 'Backspace') {
    if (startOffset <= 0) {
      if (text.startsWith(HARD_PARAGRAPH_BREAK)) {
        return { startOffset: 0, endOffset: HARD_PARAGRAPH_BREAK.length }
      }
      return null
    }
    const hardBreakStart = startOffset - HARD_PARAGRAPH_BREAK.length
    if (hardBreakStart >= 0 && text.slice(hardBreakStart, startOffset) === HARD_PARAGRAPH_BREAK) {
      return { startOffset: hardBreakStart, endOffset: startOffset }
    }
    return { startOffset: startOffset - 1, endOffset: startOffset }
  }

  if (startOffset >= text.length) return null
  const hardBreakEnd = startOffset + HARD_PARAGRAPH_BREAK.length
  if (text.slice(startOffset, hardBreakEnd) === HARD_PARAGRAPH_BREAK) {
    return { startOffset, endOffset: hardBreakEnd }
  }
  return { startOffset, endOffset: startOffset + 1 }
}

function textWithDeletionAtSelection(target: HTMLElement, key: 'Backspace' | 'Delete') {
  const currentText = editableParagraphText(target)
  const selectionRange = textRangeWithinSelection(target)
  if (!selectionRange) return null

  const deletionRange = deletionRangeForKey(currentText, selectionRange.startOffset, selectionRange.endOffset, key)
  if (!deletionRange) return { text: currentText, caretOffset: selectionRange.startOffset }

  return {
    text: `${currentText.slice(0, deletionRange.startOffset)}${currentText.slice(deletionRange.endOffset)}`,
    caretOffset: deletionRange.startOffset,
  }
}

function paragraphBreakCaretOffset(replaceStart: number, defaultCaretOffset: number) {
  return replaceStart === 0 ? 0 : defaultCaretOffset
}

function onKeydown(paragraphIndex: number, event: KeyboardEvent) {
  if (event.key === 'Backspace' || event.key === 'Delete') {
    event.preventDefault()

    const target = event.currentTarget as HTMLElement
    if (replaceActiveSelectionText(paragraphIndex, target, '', activeSelection.value?.startOffset)) return

    const deletion = textWithDeletionAtSelection(target, event.key)
    if (!deletion) return
    editableText.value[paragraphIndex] = deletion.text
    restoreEditableCaretAfterRender(paragraphIndex, deletion.caretOffset)
    return
  }

  if (event.key !== 'Enter') return
  event.preventDefault()

  const target = event.currentTarget as HTMLElement
  const insertionText = event.shiftKey ? '\n' : HARD_PARAGRAPH_BREAK
  const activeSelectionCaretOffset = !event.shiftKey && activeSelection.value?.startOffset === 0 ? 0 : undefined
  if (replaceActiveSelectionText(paragraphIndex, target, insertionText, activeSelectionCaretOffset)) return

  const insertion = textWithInsertionAtSelection(target, insertionText)
  if (!insertion) return
  editableText.value[paragraphIndex] = insertion.text
  restoreEditableCaretAfterRender(
    paragraphIndex,
    event.shiftKey ? insertion.caretOffset : paragraphBreakCaretOffset(insertion.replaceStart, insertion.caretOffset),
  )
}

function textInsertedIntoOriginalMarker(element: Element) {
  const originalText = element.getAttribute('data-original-text') || ''
  const currentText = element.textContent || ''
  if (!currentText || currentText === originalText) return ''
  if (!originalText) return currentText
  if (currentText.startsWith(originalText)) return currentText.slice(originalText.length)
  if (currentText.endsWith(originalText)) return currentText.slice(0, currentText.length - originalText.length)

  const originalIndex = currentText.indexOf(originalText)
  if (originalIndex >= 0) {
    return `${currentText.slice(0, originalIndex)}${currentText.slice(originalIndex + originalText.length)}`
  }
  return currentText
}

function editableNodeText(node: Node): string {
  if (node instanceof Element && node.classList.contains('manuscript-editor__soft-break-placeholder')) return ''
  if (node instanceof Element && node.classList.contains('manuscript-editor__empty-block-placeholder')) {
    return (node.textContent || '').replace(new RegExp(ZERO_WIDTH_SPACE, 'g'), '')
  }
  if (node.nodeName === 'BR') return '\n'
  if (node.nodeType === Node.TEXT_NODE) return node.textContent || ''
  if (!(node instanceof Element)) return ''
  if (node.classList.contains('manuscript-editor__inline-original')) return textInsertedIntoOriginalMarker(node)

  let text = ''
  node.childNodes.forEach((child) => {
    text += editableNodeText(child)
  })
  return text
}

function editableParagraphText(target: HTMLElement) {
  const textBlocks = Array.from(target.children).filter((child) => child.classList.contains('manuscript-editor__text-block'))
  if (textBlocks.length) return textBlocks.map((child) => editableNodeText(child)).join('\n\n')

  let text = ''
  target.childNodes.forEach((child) => {
    text += editableNodeText(child)
  })
  return text || target.innerText || target.textContent || ''
}

function onBlur(paragraphIndex: number, event: FocusEvent) {
  const originalText = props.paragraphs[paragraphIndex]
  const target = event.currentTarget as HTMLElement
  const correctedText = editableParagraphText(target) || editableText.value[paragraphIndex] || ''
  const correction = paragraphCorrection(paragraphIndex)
  delete editableText.value[paragraphIndex]
  if (!correctedText) return
  if (!correction && correctedText === originalText) return
  if (correction?.correctedText === correctedText) return
  emit('addCorrection', { paragraphIndex, originalText, correctedText })
}

function saveAnnotation(comment: string) {
  if (!activeSelection.value) return
  const { paragraphIndex, startOffset, endOffset, selectedText } = activeSelection.value
  emit('addAnnotation', { paragraphIndex, startOffset, endOffset, selectedText, comment })
  activeSelection.value = null
}

function eventTargetElement(event: Event) {
  const target = event.target
  if (target instanceof Element) return target
  if (target instanceof Node && target.parentNode instanceof Element) return target.parentNode
  return null
}

function onDocumentPointerDown(event: PointerEvent) {
  const targetElement = eventTargetElement(event)
  if (targetElement?.closest('.annotation-bubble')) return

  const target = event.target
  if (target instanceof Node && editorRef.value?.contains(target)) {
    activeSelection.value = null
    isPointerSelecting = true
    preserveSelectionOnNextMouseup = false
    return
  }

  isPointerSelecting = false
  preserveSelectionOnNextMouseup = false
  activeSelection.value = null
}

function onDocumentPointerUp() {
  if (!isPointerSelecting) return
  isPointerSelecting = false
  preserveSelectionOnNextMouseup = captureSelectionFromDocument()
}

function onDocumentSelectionChange() {
  if (isPointerSelecting) return
  captureSelectionFromDocument()
}

function onDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') activeSelection.value = null
}

onMounted(() => {
  document.addEventListener('selectionchange', onDocumentSelectionChange)
  document.addEventListener('pointerdown', onDocumentPointerDown, true)
  document.addEventListener('pointerup', onDocumentPointerUp, true)
  document.addEventListener('keydown', onDocumentKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('selectionchange', onDocumentSelectionChange)
  document.removeEventListener('pointerdown', onDocumentPointerDown, true)
  document.removeEventListener('pointerup', onDocumentPointerUp, true)
  document.removeEventListener('keydown', onDocumentKeydown)
})
</script>

<template>
  <article ref="editorRef" class="manuscript-editor">
    <AnnotationBubble :open="activeSelection !== null" :selected-text="annotationText" :position="annotationPosition" @save="saveAnnotation" @cancel="activeSelection = null" />
    <header class="manuscript-editor__header">
      <h1 class="manuscript-editor__title">{{ title || '未命名章节' }}</h1>
      <p class="manuscript-editor__meta">选中文字添加批注，直接编辑段落生成修正。</p>
    </header>
    <div class="manuscript-editor__body">
      <section v-for="(_, index) in paragraphs" :key="index" class="manuscript-editor__paragraph-wrap" :data-paragraph-index="index">
        <p :key="paragraphRenderKey(index)" class="manuscript-editor__paragraph" :class="{ 'manuscript-editor__paragraph--block-break': paragraphHasBlockBreak(index) }" :data-paragraph-index="index" contenteditable="true" spellcheck="false" @mouseup="onMouseup(index, $event)" @beforeinput="onBeforeInput(index, $event)" @keydown="onKeydown(index, $event)" @input="onInput(index, $event)" @blur="onBlur(index, $event)">
          <span v-for="(block, blockIndex) in paragraphRenderBlocks(index)" :key="`${index}-block-${blockIndex}`" class="manuscript-editor__text-block">
            <span v-if="block.startsWithStructuralBreak" class="manuscript-editor__paragraph-break-marker" contenteditable="false" aria-hidden="true"></span>
            <template v-if="blockIsEmpty(block)">
              <span class="manuscript-editor__empty-block-placeholder" aria-hidden="true">{{ ZERO_WIDTH_SPACE }}</span>
            </template>
            <template v-else>
              <template v-for="(segment, segmentIndex) in block.segments" :key="`${index}-${blockIndex}-${segmentIndex}`">
                <mark v-if="segment.type === 'annotation'" class="manuscript-editor__inline-annotation" :data-annotation-id="segment.annotation.id" :title="segment.annotation.comment">{{ segment.text }}</mark>
                <mark v-else-if="segment.type === 'draft'" class="manuscript-editor__draft-selection">{{ segment.text }}</mark>
                <s v-else-if="segment.type === 'original' && segment.text" class="manuscript-editor__inline-original" contenteditable="false" :data-original-text="segment.text">{{ segment.text }}</s>
                <mark v-else-if="segment.type === 'correction'" class="manuscript-editor__inline-correction" :data-correction-id="paragraphCorrection(index)?.id">{{ segment.text }}</mark>
                <template v-else>{{ segment.text }}</template>
              </template>
            </template>
            <span v-if="blockEndsWithSoftBreak(block)" class="manuscript-editor__soft-break-placeholder" contenteditable="false" aria-hidden="true">&#8203;</span>
          </span>
        </p>
        <div v-if="paragraphAnnotations(index).length" class="manuscript-editor__marks">
          <span v-for="item in paragraphAnnotations(index)" :key="item.id" class="manuscript-editor__mark manuscript-editor__mark--annotation" :title="item.selectedText">批注：{{ annotationSelectionPreview(item.selectedText) }} · {{ item.comment }}</span>
        </div>
      </section>
      <div v-if="paragraphs.length === 0" class="manuscript-editor__empty">请选择已有正文的章节</div>
    </div>
  </article>
</template>

<style scoped>
.manuscript-editor { position: relative; width: min(720px, 100%); margin: 0 auto; padding: var(--space-6) 0 var(--space-10); }
.manuscript-editor__header { margin-bottom: var(--space-6); }
.manuscript-editor__title { color: var(--color-text-primary); font-size: var(--text-2xl); font-weight: var(--font-semibold); }
.manuscript-editor__meta { margin-top: var(--space-2); color: var(--color-text-tertiary); font-size: var(--text-sm); }
.manuscript-editor__paragraph-wrap { margin-bottom: var(--space-5); }
.manuscript-editor__paragraph { min-height: 1.8em; color: var(--color-text-primary); font-size: var(--text-base); line-height: 1.8; white-space: pre-wrap; outline: none; }
.manuscript-editor__paragraph:focus { background: transparent; }
.manuscript-editor__text-block { display: block; min-height: 1.8em; white-space: pre-wrap; }
.manuscript-editor__text-block + .manuscript-editor__text-block { margin-top: 1.8em; }
.manuscript-editor__paragraph:focus .manuscript-editor__text-block { background: var(--color-bg-secondary); border-radius: var(--radius-md); }
.manuscript-editor__empty-block-placeholder { display: inline-block; min-width: 1px; }
.manuscript-editor__soft-break-placeholder { display: inline-block; width: 0; overflow: hidden; }
.manuscript-editor__paragraph-break-marker { display: block; width: fit-content; margin-bottom: var(--space-1); padding: 0 var(--space-1); border-radius: var(--radius-sm); background: rgba(59, 130, 246, 0.08); color: var(--color-text-tertiary); font-size: var(--text-xs); line-height: 1.4; pointer-events: none; user-select: none; }
.manuscript-editor__paragraph-break-marker::before { content: '↵ 新段落'; }
.manuscript-editor__marks { display: flex; flex-direction: column; gap: var(--space-1); margin-top: var(--space-2); }
.manuscript-editor__mark { width: fit-content; padding: var(--space-1) var(--space-2); border-radius: var(--radius-md); font-size: var(--text-xs); }
.manuscript-editor__mark--annotation { background: rgba(254, 240, 138, 0.55); color: var(--color-text-primary); }
.manuscript-editor__mark--correction { background: rgba(187, 247, 208, 0.55); color: var(--color-text-primary); }
.manuscript-editor__inline-annotation { background: rgba(254, 240, 138, 0.75); color: inherit; }
.manuscript-editor__draft-selection { background: rgba(250, 204, 21, 0.35); color: inherit; }
.manuscript-editor__inline-original { color: var(--color-text-tertiary); text-decoration-color: var(--color-error); }
.manuscript-editor__inline-correction { background: rgba(187, 247, 208, 0.75); color: inherit; }
.manuscript-editor__flash-target { animation: manuscript-flash-target 1.15s ease-in-out 2; border-radius: var(--radius-sm); }
.manuscript-editor__empty { padding: var(--space-8); color: var(--color-text-tertiary); text-align: center; }

@keyframes manuscript-flash-target {
  0%, 100% { box-shadow: 0 0 0 0 rgba(251, 191, 36, 0); }
  35% { box-shadow: 0 0 0 4px rgba(251, 191, 36, 0.35); background-color: rgba(254, 240, 138, 0.95); }
  70% { box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.18); }
}
</style>
