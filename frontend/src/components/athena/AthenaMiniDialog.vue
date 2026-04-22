<template>
  <aside class="athena-dialog">
    <header class="athena-dialog__header">
      <span class="athena-dialog__title">⏣ Athena 对话</span>
      <span class="athena-dialog__hint">世界构建专用</span>
    </header>
    <div ref="scrollArea" class="athena-dialog__messages">
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="athena-dialog__bubble"
        :class="msg.role === 'user' ? 'is-user' : 'is-assistant'"
      >
        {{ msg.content }}
      </div>
      <div v-if="loading" class="athena-dialog__bubble is-assistant">思考中...</div>
    </div>
    <form class="athena-dialog__input" @submit.prevent="onSend">
      <input
        v-model="text"
        placeholder="讨论世界设定..."
        :disabled="loading"
      >
      <button type="submit" :disabled="!text.trim() || loading">发送</button>
    </form>
  </aside>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import type { ChatHistoryMessage } from '../../api/types'

const props = defineProps<{
  messages: ChatHistoryMessage[]
  loading: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
}>()

const text = ref('')
const scrollArea = ref<HTMLElement | null>(null)

watch(() => props.messages.length, async () => {
  await nextTick()
  if (scrollArea.value) {
    scrollArea.value.scrollTop = scrollArea.value.scrollHeight
  }
})

function onSend() {
  const t = text.value.trim()
  if (!t) return
  emit('send', t)
  text.value = ''
}
</script>

<style scoped>
.athena-dialog {
  display: flex;
  flex-direction: column;
  border-left: 1px solid rgba(111, 69, 31, 0.1);
  height: 100%;
}
.athena-dialog__header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 0.85rem;
  border-bottom: 1px solid rgba(111, 69, 31, 0.1);
}
.athena-dialog__title {
  color: var(--accent-strong);
  font-size: 0.8rem;
  font-weight: 700;
}
.athena-dialog__hint {
  margin-left: auto;
  color: var(--ink-muted);
  font-size: 0.68rem;
}
.athena-dialog__messages {
  flex: 1;
  overflow-y: auto;
  padding: 0.65rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.athena-dialog__bubble {
  max-width: 90%;
  border-radius: 0.7rem;
  padding: 0.5rem 0.65rem;
  font-size: 0.76rem;
  line-height: 1.5;
  word-break: break-word;
}
.athena-dialog__bubble.is-user {
  align-self: flex-end;
  background: rgba(111, 69, 31, 0.06);
  color: var(--ink-strong);
}
.athena-dialog__bubble.is-assistant {
  align-self: flex-start;
  background: rgba(99, 102, 241, 0.08);
  color: var(--ink-strong);
}
.athena-dialog__input {
  display: flex;
  gap: 0.4rem;
  padding: 0.55rem 0.65rem;
  border-top: 1px solid rgba(111, 69, 31, 0.1);
}
.athena-dialog__input input {
  flex: 1;
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 0.6rem;
  padding: 0.4rem 0.6rem;
  background: rgba(255, 252, 246, 0.92);
  color: var(--ink-strong);
  font-size: 0.76rem;
}
.athena-dialog__input button {
  border: none;
  border-radius: 0.6rem;
  padding: 0.4rem 0.75rem;
  background: var(--accent-strong);
  color: #fff;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
}
.athena-dialog__input button:disabled { opacity: 0.5; }
</style>
