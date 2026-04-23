<template>
  <article class="summary-card">
    <button
      type="button"
      class="summary-card__toggle"
      data-testid="chat-summary-toggle"
      @click="expanded = !expanded"
    >
      <span class="summary-card__headline">
        <span class="summary-card__title">{{ title }}</span>
        <span
          v-if="compactedCount > 0"
          class="summary-card__meta"
        >已压缩 {{ compactedCount }} 条消息</span>
      </span>
      <span class="summary-card__arrow">{{ expanded ? '收起' : '展开' }}</span>
    </button>
    <div
      v-if="expanded"
      class="summary-card__body"
      data-testid="chat-summary-body"
    >
      {{ content }}
    </div>
  </article>
</template>

<script setup lang="ts">
import { ref } from 'vue'

withDefaults(defineProps<{
  content: string
  title?: string
  compactedCount?: number
}>(), {
  title: '会话摘要',
  compactedCount: 0,
})

const expanded = ref(false)
</script>

<style scoped>
.summary-card {
  width: min(88%, 42rem);
  border: 1px solid rgba(111, 69, 31, 0.18);
  border-radius: 1rem;
  background: linear-gradient(180deg, rgba(244, 234, 212, 0.94) 0%, rgba(235, 222, 195, 0.95) 100%);
  box-shadow: 0 12px 22px rgba(80, 55, 26, 0.1);
  overflow: hidden;
}

.summary-card__toggle {
  width: 100%;
  border: 0;
  background: transparent;
  color: var(--ink-strong);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.8rem;
  padding: 0.7rem 0.85rem;
  font-size: 0.84rem;
  font-weight: 700;
}

.summary-card__headline {
  display: grid;
  gap: 0.15rem;
  text-align: left;
}

.summary-card__title {
  font-size: 0.84rem;
}

.summary-card__meta {
  font-size: 0.74rem;
  color: var(--ink-muted);
  font-weight: 600;
}

.summary-card__arrow {
  color: var(--ink-muted);
  font-size: 0.76rem;
}

.summary-card__body {
  border-top: 1px solid rgba(111, 69, 31, 0.16);
  padding: 0.78rem 0.88rem 0.88rem;
  white-space: pre-wrap;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--ink-strong);
}
</style>
