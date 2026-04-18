<template>
  <article class="summary-card">
    <button
      type="button"
      class="summary-card__toggle"
      data-testid="chat-summary-toggle"
      @click="expanded = !expanded"
    >
      <span>会话摘要</span>
      <span class="summary-card__arrow">{{ expanded ? '收起' : '展开' }}</span>
    </button>
    <div v-if="expanded" class="summary-card__body" data-testid="chat-summary-body">
      {{ content }}
    </div>
  </article>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{ content: string }>()

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
  align-items: center;
  padding: 0.7rem 0.85rem;
  font-size: 0.84rem;
  font-weight: 700;
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
