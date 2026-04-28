<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  messages: Array<Record<string, unknown>>
}>()

const safeMessages = computed(() => Array.isArray(props.messages) ? props.messages : [])

function roleOf(message: Record<string, unknown>) {
  const role = message && typeof message.role === 'string' ? message.role : 'unknown'
  return role || 'unknown'
}

function roleLabel(role: string) {
  if (role === 'system') return '系统'
  if (role === 'user') return '用户'
  if (role === 'assistant') return '助手'
  return role
}

function roleClass(role: string) {
  if (role === 'system') return 'raw-messages__role--system'
  if (role === 'user') return 'raw-messages__role--user'
  if (role === 'assistant') return 'raw-messages__role--assistant'
  return 'raw-messages__role--unknown'
}

function formatMessage(message: unknown) {
  try {
    return JSON.stringify(message, null, 2)
  } catch {
    return String(message || '')
  }
}
</script>

<template>
  <div class="raw-messages">
    <p v-if="!safeMessages.length" class="raw-messages__empty">无 messages</p>
    <ol v-else class="raw-messages__list">
      <li v-for="(message, index) in safeMessages" :key="index" class="raw-messages__item">
        <div class="raw-messages__header">
          <span class="raw-messages__role" :class="roleClass(roleOf(message))">{{ roleLabel(roleOf(message)) }}</span>
          <span class="raw-messages__index">#{{ index + 1 }}</span>
        </div>
        <pre class="raw-messages__json">{{ formatMessage(message) }}</pre>
      </li>
    </ol>
  </div>
</template>

<style scoped>
.raw-messages {
  min-width: 0;
}

.raw-messages__empty {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  margin: 0;
}

.raw-messages__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  list-style: none;
  margin: 0;
  padding: 0;
}

.raw-messages__item {
  border-top: 1px solid var(--color-border);
  min-width: 0;
  padding-top: var(--space-3);
}

.raw-messages__item:first-child {
  border-top: 0;
  padding-top: 0;
}

.raw-messages__header {
  align-items: center;
  display: flex;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.raw-messages__role {
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  line-height: var(--leading-tight);
  padding: var(--space-1) var(--space-2);
}

.raw-messages__role--system {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.raw-messages__role--user {
  background: var(--color-brand-light);
  color: var(--color-brand);
}

.raw-messages__role--assistant {
  background: var(--color-success-light);
  color: var(--color-success);
}

.raw-messages__role--unknown {
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
}

.raw-messages__index {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.raw-messages__json {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--leading-relaxed);
  margin: 0;
  max-height: 360px;
  overflow: auto;
  padding: var(--space-3);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
