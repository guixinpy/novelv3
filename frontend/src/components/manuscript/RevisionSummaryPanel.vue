<script setup lang="ts">
import { annotationSelectionPreview } from './annotationPreview'
import { diffCorrection } from './revisionRender'
import type { LocalAnnotation, LocalCorrection } from '../../stores/manuscript'
import type { CorrectionDiff } from './revisionRender'

const FLASH_CLASS = 'manuscript-editor__flash-target'
const FLASH_DURATION_MS = 2400
const CORRECTION_CONTEXT_CHARS = 14
const SPLIT_PREVIEW_CHARS = 22

function compactCorrectionDiff(item: LocalCorrection): CorrectionDiff {
  const diff = diffCorrection(item)
  return {
    ...diff,
    prefix: diff.prefix.length > CORRECTION_CONTEXT_CHARS
      ? `…${diff.prefix.slice(-CORRECTION_CONTEXT_CHARS)}`
      : diff.prefix,
    suffix: diff.suffix.length > CORRECTION_CONTEXT_CHARS
      ? `${diff.suffix.slice(0, CORRECTION_CONTEXT_CHARS)}…`
      : diff.suffix,
  }
}

function correctionHasParagraphSplit(item: LocalCorrection) {
  return /\n{2,}/.test(item.correctedText)
}

function correctionSplitBlocks(item: LocalCorrection) {
  return item.correctedText
    .split(/\n{2,}/)
    .map((block) => block.replace(/\s+/g, ' ').trim())
    .filter(Boolean)
}

function correctionSplitBlockPreview(block: string) {
  return block.length > SPLIT_PREVIEW_CHARS
    ? `${block.slice(0, SPLIT_PREVIEW_CHARS)}…`
    : block
}

function escapeAttributeValue(value: string) {
  return value.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
}

function flashTarget(target: Element) {
  target.classList.remove(FLASH_CLASS)
  void (target as HTMLElement).offsetWidth
  target.classList.add(FLASH_CLASS)
  window.setTimeout(() => target.classList.remove(FLASH_CLASS), FLASH_DURATION_MS)
}

function scrollToRevisionTarget(type: 'annotation' | 'correction', id: string, paragraphIndex: number) {
  const target = document.querySelector(`[data-${type}-id="${escapeAttributeValue(id)}"]`)
    || document.querySelector(`[data-paragraph-index="${paragraphIndex}"]`)
  target?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  if (target) flashTarget(target)
}

defineProps<{
  annotations: LocalAnnotation[]
  corrections: LocalCorrection[]
}>()

const emit = defineEmits<{
  removeAnnotation: [id: string]
  removeCorrection: [id: string]
}>()
</script>

<template>
  <aside class="revision-summary">
    <header class="revision-summary__header">
      <h3 class="revision-summary__title">修订摘要</h3>
      <span class="revision-summary__count">{{ annotations.length + corrections.length }}</span>
    </header>
    <p class="revision-summary__hint">Enter 新段落 · Shift+Enter 换行</p>

    <section class="revision-summary__section">
      <h4 class="revision-summary__label">批注</h4>
      <button v-for="item in annotations" :key="item.id" class="revision-summary__item" :title="item.selectedText" @click="scrollToRevisionTarget('annotation', item.id, item.paragraphIndex)">
        <span class="revision-summary__item-title">第{{ item.paragraphIndex + 1 }}段 · {{ annotationSelectionPreview(item.selectedText) }}</span>
        <span class="revision-summary__item-body">{{ item.comment }}</span>
        <span class="revision-summary__remove" @click.stop="emit('removeAnnotation', item.id)">删除</span>
      </button>
      <div v-if="annotations.length === 0" class="revision-summary__empty">暂无批注</div>
    </section>

    <section class="revision-summary__section">
      <h4 class="revision-summary__label">修正</h4>
      <button v-for="item in corrections" :key="item.id" class="revision-summary__item revision-summary__item--correction" @click="scrollToRevisionTarget('correction', item.id, item.paragraphIndex)">
        <span class="revision-summary__item-title">
          第{{ item.paragraphIndex + 1 }}段<template v-if="correctionHasParagraphSplit(item)"> · 段落拆分为{{ correctionSplitBlocks(item).length }}段</template>
        </span>
        <span v-if="correctionHasParagraphSplit(item)" class="revision-summary__item-body revision-summary__split-summary" :title="item.correctedText">
          <span v-for="(block, blockIndex) in correctionSplitBlocks(item)" :key="`${item.id}-split-${blockIndex}`" class="revision-summary__split-block">
            <span class="revision-summary__split-index">{{ blockIndex + 1 }}</span>{{ correctionSplitBlockPreview(block) }}
          </span>
        </span>
        <span v-else class="revision-summary__item-body revision-summary__correction-diff" :title="`${item.originalText} → ${item.correctedText}`">
          {{ compactCorrectionDiff(item).prefix }}<s v-if="compactCorrectionDiff(item).originalMiddle" class="revision-summary__correction-original">{{ compactCorrectionDiff(item).originalMiddle }}</s><mark v-if="compactCorrectionDiff(item).correctedMiddle" class="revision-summary__correction-updated">{{ compactCorrectionDiff(item).correctedMiddle }}</mark>{{ compactCorrectionDiff(item).suffix }}
        </span>
        <span class="revision-summary__remove" @click.stop="emit('removeCorrection', item.id)">撤销</span>
      </button>
      <div v-if="corrections.length === 0" class="revision-summary__empty">暂无修正</div>
    </section>
  </aside>
</template>

<style scoped>
.revision-summary { width: 240px; flex-shrink: 0; border-left: 1px solid var(--color-border); background: var(--color-bg-primary); overflow-y: auto; }
.revision-summary__header { display: flex; align-items: center; justify-content: space-between; padding: var(--space-4); border-bottom: 1px solid var(--color-border); }
.revision-summary__title { color: var(--color-text-primary); font-size: var(--text-base); font-weight: var(--font-semibold); }
.revision-summary__count { color: var(--color-brand); font-size: var(--text-sm); }
.revision-summary__hint { padding: var(--space-3) var(--space-4) 0; color: var(--color-text-tertiary); font-size: var(--text-xs); }
.revision-summary__section { padding: var(--space-3); }
.revision-summary__label { margin-bottom: var(--space-2); color: var(--color-text-tertiary); font-size: var(--text-xs); font-weight: var(--font-semibold); }
.revision-summary__item { display: block; width: 100%; margin-bottom: var(--space-2); padding: var(--space-3); border: 1px solid rgba(250, 204, 21, 0.35); border-radius: var(--radius-md); background: rgba(254, 240, 138, 0.2); text-align: left; }
.revision-summary__item--correction { border-color: rgba(34, 197, 94, 0.35); background: rgba(187, 247, 208, 0.2); }
.revision-summary__item-title, .revision-summary__item-body, .revision-summary__remove { display: block; }
.revision-summary__item-title { color: var(--color-text-primary); font-size: var(--text-sm); font-weight: var(--font-medium); }
.revision-summary__item-body { margin-top: var(--space-1); color: var(--color-text-secondary); font-size: var(--text-sm); }
.revision-summary__correction-diff { line-height: 1.6; }
.revision-summary__correction-original { color: var(--color-text-tertiary); text-decoration-color: var(--color-error); }
.revision-summary__correction-updated { border-radius: var(--radius-sm); background: rgba(187, 247, 208, 0.85); color: inherit; }
.revision-summary__split-summary { display: flex; flex-direction: column; gap: var(--space-1); }
.revision-summary__split-block { display: block; overflow: hidden; color: var(--color-text-secondary); text-overflow: ellipsis; white-space: nowrap; }
.revision-summary__split-index { display: inline-flex; align-items: center; justify-content: center; width: 1.25em; height: 1.25em; margin-right: var(--space-1); border-radius: 999px; background: rgba(34, 197, 94, 0.16); color: var(--color-text-tertiary); font-size: var(--text-xs); }
.revision-summary__remove { margin-top: var(--space-2); color: var(--color-error); font-size: var(--text-xs); }
.revision-summary__empty { color: var(--color-text-tertiary); font-size: var(--text-sm); }
</style>
