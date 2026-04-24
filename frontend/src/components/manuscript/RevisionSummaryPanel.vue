<script setup lang="ts">
import type { LocalAnnotation, LocalCorrection } from '../../stores/manuscript'

function correctionPreview(item: LocalCorrection) {
  return `${item.originalText} → ${item.correctedText}`
}

function scrollToParagraph(index: number) {
  document.querySelector(`[data-paragraph-index="${index}"]`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })
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

    <section class="revision-summary__section">
      <h4 class="revision-summary__label">批注</h4>
      <button v-for="item in annotations" :key="item.id" class="revision-summary__item" @click="scrollToParagraph(item.paragraphIndex)">
        <span class="revision-summary__item-title">第{{ item.paragraphIndex + 1 }}段 · {{ item.selectedText }}</span>
        <span class="revision-summary__item-body">{{ item.comment }}</span>
        <span class="revision-summary__remove" @click.stop="emit('removeAnnotation', item.id)">删除</span>
      </button>
      <div v-if="annotations.length === 0" class="revision-summary__empty">暂无批注</div>
    </section>

    <section class="revision-summary__section">
      <h4 class="revision-summary__label">修正</h4>
      <button v-for="item in corrections" :key="item.id" class="revision-summary__item revision-summary__item--correction" @click="scrollToParagraph(item.paragraphIndex)">
        <span class="revision-summary__item-title">第{{ item.paragraphIndex + 1 }}段</span>
        <span class="revision-summary__item-body">{{ correctionPreview(item) }}</span>
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
.revision-summary__section { padding: var(--space-3); }
.revision-summary__label { margin-bottom: var(--space-2); color: var(--color-text-tertiary); font-size: var(--text-xs); font-weight: var(--font-semibold); }
.revision-summary__item { display: block; width: 100%; margin-bottom: var(--space-2); padding: var(--space-3); border: 1px solid rgba(250, 204, 21, 0.35); border-radius: var(--radius-md); background: rgba(254, 240, 138, 0.2); text-align: left; }
.revision-summary__item--correction { border-color: rgba(34, 197, 94, 0.35); background: rgba(187, 247, 208, 0.2); }
.revision-summary__item-title, .revision-summary__item-body, .revision-summary__remove { display: block; }
.revision-summary__item-title { color: var(--color-text-primary); font-size: var(--text-sm); font-weight: var(--font-medium); }
.revision-summary__item-body { margin-top: var(--space-1); color: var(--color-text-secondary); font-size: var(--text-sm); }
.revision-summary__remove { margin-top: var(--space-2); color: var(--color-error); font-size: var(--text-xs); }
.revision-summary__empty { color: var(--color-text-tertiary); font-size: var(--text-sm); }
</style>
