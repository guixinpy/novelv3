<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import ChatMessage from './ChatMessage.vue'

const props = defineProps<{
  messages: any[]
  loading: boolean
}>()

const emit = defineEmits<{
  decide: [decision: string, comment?: string]
}>()

const container = ref<HTMLElement | null>(null)

function scrollToBottom() {
  nextTick(() => {
    if (!container.value) return
    container.value.scrollTop = container.value.scrollHeight
  })
}

watch(() => props.messages.length, scrollToBottom)
watch(() => props.loading, scrollToBottom)
</script>

<template>
  <div ref="container" class="chat-message-list">
    <ChatMessage
      v-for="(message, index) in messages"
      :key="`${index}-${message.role}`"
      :msg="message"
      :is-latest="index === messages.length - 1"
      :loading="loading"
      @decide="(d, c) => emit('decide', d, c)"
    />
    <div v-if="loading" class="chat-message-list__loading">
      <span class="chat-message-list__dots">
        <span /><span /><span />
      </span>
    </div>
  </div>
</template>

<style scoped>
.chat-message-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.chat-message-list__loading {
  display: flex;
  justify-content: flex-start;
}

.chat-message-list__dots {
  display: flex;
  gap: 4px;
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-white);
  border-left: 3px solid var(--color-brand);
  border-radius: var(--radius-md);
}

.chat-message-list__dots span {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: var(--color-text-tertiary);
  animation: dot-pulse 1.5s ease-in-out infinite;
}

.chat-message-list__dots span:nth-child(2) { animation-delay: 0.2s; }
.chat-message-list__dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes dot-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}
</style>
