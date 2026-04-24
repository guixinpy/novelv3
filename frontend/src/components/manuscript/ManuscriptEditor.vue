<script setup lang="ts">
import { computed, ref } from 'vue'
import AnnotationBubble from './AnnotationBubble.vue'
import { getSelectionOffsetsWithin } from './selectionOffsets'
import { buildParagraphSegments, diffCorrection } from './revisionRender'
import type { LocalAnnotation, LocalCorrection } from '../../stores/manuscript'

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

const activeSelection = ref<{ paragraphIndex: number; startOffset: number; endOffset: number; selectedText: string } | null>(null)
const editableText = ref<Record<number, string>>({})
const annotationText = computed(() => activeSelection.value?.selectedText || '')

function paragraphAnnotations(index: number) {
  return props.annotations.filter((item) => item.paragraphIndex === index)
}

function paragraphSegments(index: number) {
  return buildParagraphSegments(props.paragraphs[index], paragraphAnnotations(index))
}

function paragraphCorrection(index: number) {
  return props.corrections.find((item) => item.paragraphIndex === index) || null
}

function paragraphCorrectionDiff(index: number) {
  const correction = paragraphCorrection(index)
  return correction ? diffCorrection(correction) : null
}

function onMouseup(paragraphIndex: number, event: MouseEvent) {
  const selection = window.getSelection()
  const offsets = getSelectionOffsetsWithin(event.currentTarget as HTMLElement, selection)
  if (!offsets) return
  activeSelection.value = { paragraphIndex, ...offsets }
}

function onInput(paragraphIndex: number, event: Event) {
  editableText.value[paragraphIndex] = (event.target as HTMLElement).innerText
}

function onBlur(paragraphIndex: number, event: FocusEvent) {
  const originalText = props.paragraphs[paragraphIndex]
  const target = event.currentTarget as HTMLElement
  const correctedText = editableText.value[paragraphIndex] || target.innerText || target.textContent || ''
  if (!correctedText || correctedText === originalText) return
  emit('addCorrection', { paragraphIndex, originalText, correctedText })
}

function saveAnnotation(comment: string) {
  if (!activeSelection.value) return
  emit('addAnnotation', { ...activeSelection.value, comment })
  activeSelection.value = null
}
</script>

<template>
  <article class="manuscript-editor">
    <AnnotationBubble :open="activeSelection !== null" :selected-text="annotationText" @save="saveAnnotation" @cancel="activeSelection = null" />
    <header class="manuscript-editor__header">
      <h1 class="manuscript-editor__title">{{ title || '未命名章节' }}</h1>
      <p class="manuscript-editor__meta">选中文字添加批注，直接编辑段落生成修正。</p>
    </header>
    <div class="manuscript-editor__body">
      <section v-for="(_, index) in paragraphs" :key="index" class="manuscript-editor__paragraph-wrap" :data-paragraph-index="index">
        <p class="manuscript-editor__paragraph" contenteditable="true" spellcheck="false" @mouseup="onMouseup(index, $event)" @input="onInput(index, $event)" @blur="onBlur(index, $event)">
          <template v-if="!paragraphCorrection(index)">
            <template v-for="(segment, segmentIndex) in paragraphSegments(index)" :key="`${index}-${segmentIndex}`">
              <mark v-if="segment.type === 'annotation'" class="manuscript-editor__inline-annotation" :title="segment.annotation.comment">{{ segment.text }}</mark>
              <template v-else>{{ segment.text }}</template>
            </template>
          </template>
          <template v-else-if="paragraphCorrectionDiff(index)">
            {{ paragraphCorrectionDiff(index)?.prefix }}<s class="manuscript-editor__inline-original">{{ paragraphCorrectionDiff(index)?.originalMiddle }}</s><mark class="manuscript-editor__inline-correction">{{ paragraphCorrectionDiff(index)?.correctedMiddle }}</mark>{{ paragraphCorrectionDiff(index)?.suffix }}
          </template>
        </p>
        <div v-if="paragraphAnnotations(index).length" class="manuscript-editor__marks">
          <span v-for="item in paragraphAnnotations(index)" :key="item.id" class="manuscript-editor__mark manuscript-editor__mark--annotation">批注：{{ item.selectedText }} · {{ item.comment }}</span>
        </div>
      </section>
      <div v-if="paragraphs.length === 0" class="manuscript-editor__empty">请选择已有正文的章节</div>
    </div>
  </article>
</template>

<style scoped>
.manuscript-editor { width: min(720px, 100%); margin: 0 auto; padding: var(--space-6) 0 var(--space-10); }
.manuscript-editor__header { margin-bottom: var(--space-6); }
.manuscript-editor__title { color: var(--color-text-primary); font-size: var(--text-2xl); font-weight: var(--font-semibold); }
.manuscript-editor__meta { margin-top: var(--space-2); color: var(--color-text-tertiary); font-size: var(--text-sm); }
.manuscript-editor__paragraph-wrap { margin-bottom: var(--space-5); }
.manuscript-editor__paragraph { min-height: 1.8em; color: var(--color-text-primary); font-size: var(--text-base); line-height: 1.8; outline: none; }
.manuscript-editor__paragraph:focus { background: var(--color-bg-secondary); border-radius: var(--radius-md); }
.manuscript-editor__marks { display: flex; flex-direction: column; gap: var(--space-1); margin-top: var(--space-2); }
.manuscript-editor__mark { width: fit-content; padding: var(--space-1) var(--space-2); border-radius: var(--radius-md); font-size: var(--text-xs); }
.manuscript-editor__mark--annotation { background: rgba(254, 240, 138, 0.55); color: var(--color-text-primary); }
.manuscript-editor__mark--correction { background: rgba(187, 247, 208, 0.55); color: var(--color-text-primary); }
.manuscript-editor__inline-annotation { background: rgba(254, 240, 138, 0.75); color: inherit; }
.manuscript-editor__inline-original { color: var(--color-text-tertiary); text-decoration-color: var(--color-error); }
.manuscript-editor__inline-correction { background: rgba(187, 247, 208, 0.75); color: inherit; }
.manuscript-editor__empty { padding: var(--space-8); color: var(--color-text-tertiary); text-align: center; }
</style>
