<script setup lang="ts">
export interface ChapterItem {
  index: number
  wordCount: number
}

defineProps<{
  chapters: ChapterItem[]
  activeIndex: number | null
}>()

const emit = defineEmits<{
  select: [index: number]
}>()
</script>

<template>
  <div class="chapter-list">
    <button
      v-for="ch in chapters"
      :key="ch.index"
      class="chapter-list__item"
      :class="{ 'chapter-list__item--active': activeIndex === ch.index }"
      @click="emit('select', ch.index)"
    >
      <span class="chapter-list__name">第{{ ch.index }}章</span>
      <span class="chapter-list__count">{{ ch.wordCount.toLocaleString() }}字</span>
    </button>
    <div v-if="chapters.length === 0" class="chapter-list__empty">
      暂无章节
    </div>
  </div>
</template>

<style scoped>
.chapter-list {
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.chapter-list__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  transition: background var(--transition-fast);
  border: none;
  background: transparent;
  text-align: left;
  width: 100%;
  cursor: pointer;
}

.chapter-list__item:hover {
  background: var(--color-bg-secondary);
}

.chapter-list__item--active {
  background: var(--color-brand-light);
  color: var(--color-brand);
  font-weight: var(--font-medium);
}

.chapter-list__item--active:hover {
  background: var(--color-brand-light);
}

.chapter-list__count {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.chapter-list__item--active .chapter-list__count {
  color: var(--color-brand);
  opacity: 0.7;
}

.chapter-list__empty {
  padding: var(--space-4) var(--space-3);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  text-align: center;
}
</style>
