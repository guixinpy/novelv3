<script setup lang="ts">
import { ref } from 'vue'

const { toolName, isError, resultText, isPending } = defineProps<{
  toolName: string
  isError?: boolean
  resultText?: string
  isPending?: boolean
}>()

const expanded = ref(false)

function toggle() {
  if (resultText) expanded.value = !expanded.value
}
</script>

<template>
  <div
    class="agent-tool-card"
    :class="{
      'agent-tool-card--error': isError,
      'agent-tool-card--pending': isPending,
    }"
    role="status"
    :aria-label="`工具 ${toolName}`"
  >
    <div class="agent-tool-card__header" @click="toggle">
      <span class="agent-tool-card__icon">{{ isPending ? '⏳' : isError ? '⚠️' : '✅' }}</span>
      <span class="agent-tool-card__name">{{ toolName }}</span>
      <span v-if="isPending" class="agent-tool-card__label">执行中…</span>
      <span v-else-if="resultText" class="agent-tool-card__toggle">{{ expanded ? '▲' : '▼' }}</span>
    </div>
    <div v-if="expanded && resultText" class="agent-tool-card__result">
      {{ resultText }}
    </div>
  </div>
</template>

<style scoped>
.agent-tool-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  background: var(--color-bg-secondary);
}

.agent-tool-card--error {
  border-color: var(--color-error);
  background: var(--color-error-light);
}

.agent-tool-card--pending {
  border-color: var(--color-brand);
  background: var(--color-brand-light);
}

.agent-tool-card__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  cursor: pointer;
}

.agent-tool-card__icon {
  font-size: var(--text-sm);
}

.agent-tool-card__name {
  color: var(--color-text-primary);
  font-weight: var(--font-medium);
}

.agent-tool-card__label {
  color: var(--color-text-tertiary);
}

.agent-tool-card__toggle {
  margin-left: auto;
  color: var(--color-text-tertiary);
  font-size: 0.625rem;
}

.agent-tool-card__result {
  border-top: 1px solid var(--color-border);
  padding: var(--space-2);
  color: var(--color-text-secondary);
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
  line-height: var(--leading-normal);
}
</style>
