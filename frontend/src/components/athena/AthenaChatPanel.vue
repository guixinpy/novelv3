<script setup lang="ts">
import { computed } from 'vue'
import ChatMessageList from '../chat/ChatMessageList.vue'
import ChatInput from '../chat/ChatInput.vue'
import { useAthenaStore } from '../../stores/athena'

const props = defineProps<{
  open: boolean
  projectId: string
}>()

const emit = defineEmits<{
  close: []
}>()

const athena = useAthenaStore()

const messages = computed(() =>
  (athena.messages || []).map((m: any) => ({
    role: m.role,
    content: m.content,
    message_type: m.message_type || null,
    meta: m.meta || null,
    pending_action: null,
    action_result: null,
  })),
)

async function onSend(text: string) {
  await athena.sendChat(props.projectId, text)
}
</script>

<template>
  <Teleport to="body">
    <Transition name="slide">
      <div v-if="open" class="athena-chat-panel">
        <header class="athena-chat-panel__header">
          <h3 class="athena-chat-panel__title">Athena</h3>
          <button class="athena-chat-panel__close" @click="emit('close')">&times;</button>
        </header>
        <ChatMessageList
          :messages="messages"
          :loading="athena.chatLoading"
        />
        <ChatInput
          :loading="athena.chatLoading"
          :disabled="false"
          :has-pending-action="false"
          @send="onSend"
        />
      </div>
    </Transition>
    <Transition name="fade">
      <div v-if="open" class="athena-chat-panel__backdrop" @click="emit('close')" />
    </Transition>
  </Teleport>
</template>

<style scoped>
.athena-chat-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: var(--athena-chat-width, 400px);
  background: var(--color-bg-white);
  border-left: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
  z-index: var(--z-panel);
  display: flex;
  flex-direction: column;
}

.athena-chat-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
}

.athena-chat-panel__title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.athena-chat-panel__close {
  font-size: var(--text-xl);
  color: var(--color-text-tertiary);
  padding: var(--space-1);
  line-height: 1;
}

.athena-chat-panel__close:hover {
  color: var(--color-text-primary);
}

.athena-chat-panel__backdrop {
  position: fixed;
  inset: 0;
  z-index: calc(var(--z-panel) - 1);
}

/* Transitions */
.slide-enter-active,
.slide-leave-active {
  transition: transform var(--transition-normal);
}

.slide-enter-from,
.slide-leave-to {
  transform: translateX(100%);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-normal);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
