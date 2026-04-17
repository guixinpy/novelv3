<template>
  <section class="chat-workspace">
    <header class="chat-workspace__header">
      <div class="space-y-3">
        <div class="flex flex-wrap items-center gap-3">
          <p class="chat-workspace__eyebrow">Project Workspace</p>
          <span class="chat-workspace__mode">{{ modeLabel }}</span>
        </div>
        <div class="space-y-2">
          <h1 class="chat-workspace__title">{{ project.name }}</h1>
          <p class="chat-workspace__meta">
            {{ project.genre || '未分类题材' }}
            <span class="chat-workspace__dot" />
            {{ project.current_word_count || 0 }} 字
            <span class="chat-workspace__dot" />
            {{ project.status || '进行中' }}
          </p>
        </div>
      </div>
      <div class="chat-workspace__context">
        <div class="chat-workspace__context-head">
          <span class="chat-workspace__context-label">当前 Inspector</span>
          <span class="chat-workspace__context-panel">{{ currentPanelLabel }}</span>
        </div>
        <p class="chat-workspace__context-copy">{{ contextCopy }}</p>
      </div>
    </header>

    <div ref="messageContainer" class="chat-workspace__messages">
      <ChatMessage
        v-for="(message, index) in messages"
        :key="`${index}-${message.role}`"
        :msg="message"
        :is-latest="index === messages.length - 1"
        :loading="loading"
        @decide="forwardDecision"
      />
      <div v-if="loading" class="flex justify-start">
        <div class="chat-workspace__loading">墨舟正在整理上下文...</div>
      </div>
    </div>

    <QuickActions
      :diagnosis="diagnosis"
      :disabled="loading || !!pendingAction"
      @action="emit('action', $event)"
    />

    <footer class="chat-workspace__composer">
      <div class="chat-workspace__composer-inner">
        <input
          v-model="input"
          :disabled="loading || !!pendingAction"
          class="chat-workspace__input"
          placeholder="继续描述你的设想，或直接让墨舟推进下一步..."
          @keyup.enter="submit"
        />
        <button
          :disabled="loading || !!pendingAction || !input.trim()"
          class="chat-workspace__send"
          @click="submit"
        >
          发送
        </button>
      </div>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { WorkspacePanel } from '../../api/types'
import type { Diagnosis, ChatMessage as ChatMessageItem, PendingAction } from '../../stores/chat'
import type { WorkspaceMode, WorkspaceSource } from '../../stores/workspace'
import ChatMessage from '../ChatMessage.vue'
import QuickActions from '../QuickActions.vue'
import type { WorkspaceTab } from './workspaceMeta'

const props = defineProps<{
  project: any
  tabs: WorkspaceTab[]
  panel: WorkspacePanel
  mode: WorkspaceMode
  source: WorkspaceSource
  reason: string
  messages: ChatMessageItem[]
  diagnosis: Diagnosis | null
  pendingAction: PendingAction | null
  loading: boolean
}>()

const emit = defineEmits<{
  send: [text: string]
  action: [type: string]
  decide: [decision: string, comment?: string]
}>()

const input = ref('')
const messageContainer = ref<HTMLElement | null>(null)

const currentPanelLabel = computed(() =>
  props.tabs.find((tab) => tab.id === props.panel)?.label ?? '概览',
)

const modeLabel = computed(() => (props.mode === 'locked' ? '锁定观察' : '自动联动'))

const sourceLabel = computed(() => {
  if (props.source === 'user') return '你'
  if (props.source === 'ai') return '墨舟'
  return '系统'
})

const contextCopy = computed(() => {
  if (props.reason) return `${sourceLabel.value}：${props.reason}`
  if (props.mode === 'locked') return 'Inspector 已锁定，关键动作仍会临时跳转。'
  return '聊天会驱动右侧 Inspector 自动联动。'
})

function scrollToBottom() {
  nextTick(() => {
    if (!messageContainer.value) return
    messageContainer.value.scrollTop = messageContainer.value.scrollHeight
  })
}

function submit() {
  const text = input.value.trim()
  if (!text || props.loading || props.pendingAction) return
  emit('send', text)
  input.value = ''
}

function forwardDecision(decision: string, comment?: string) {
  emit('decide', decision, comment)
}

watch(() => props.messages.length, scrollToBottom)
watch(() => props.loading, scrollToBottom)
</script>

<style scoped>
.chat-workspace {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--line-soft);
  background:
    linear-gradient(180deg, rgba(252, 248, 239, 0.98) 0%, rgba(245, 238, 222, 0.97) 100%);
  box-shadow:
    0 26px 46px rgba(72, 49, 24, 0.14),
    inset 0 1px 0 rgba(255, 250, 239, 0.82);
  border-radius: 2rem;
}

.chat-workspace__header {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1.25rem 1.25rem 1rem;
  border-bottom: 1px solid rgba(111, 69, 31, 0.16);
  background:
    linear-gradient(135deg, rgba(255, 249, 236, 0.94) 0%, rgba(240, 230, 209, 0.88) 100%);
}

.chat-workspace__eyebrow {
  color: var(--accent-strong);
  font-family: "Palatino Linotype", "Book Antiqua", serif;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.24em;
  text-transform: uppercase;
}

.chat-workspace__mode {
  border: 1px solid rgba(111, 69, 31, 0.18);
  background: rgba(255, 248, 233, 0.8);
  color: var(--ink-muted);
  border-radius: 999px;
  padding: 0.25rem 0.75rem;
  font-size: 0.72rem;
  font-weight: 600;
}

.chat-workspace__title {
  color: var(--ink-strong);
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  font-size: clamp(1.85rem, 3vw, 2.5rem);
  line-height: 1.05;
}

.chat-workspace__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
  color: var(--ink-muted);
  font-size: 0.92rem;
}

.chat-workspace__dot {
  width: 0.3rem;
  height: 0.3rem;
  border-radius: 999px;
  background: rgba(111, 69, 31, 0.26);
}

.chat-workspace__context {
  border: 1px solid rgba(111, 69, 31, 0.14);
  background: rgba(255, 249, 237, 0.74);
  border-radius: 1.25rem;
  padding: 0.9rem 1rem;
}

.chat-workspace__context-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.65rem;
}

.chat-workspace__context-label {
  color: var(--ink-muted);
  font-size: 0.76rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.chat-workspace__context-panel {
  color: var(--accent-strong);
  font-family: "Palatino Linotype", "Book Antiqua", serif;
  font-size: 1rem;
  font-weight: 700;
}

.chat-workspace__context-copy {
  margin-top: 0.35rem;
  color: var(--ink-muted);
  font-size: 0.94rem;
  line-height: 1.5;
}

.chat-workspace__messages {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
}

.chat-workspace__loading {
  border: 1px solid rgba(111, 69, 31, 0.14);
  background: rgba(255, 249, 237, 0.84);
  color: var(--ink-muted);
  border-radius: 1rem;
  padding: 0.75rem 0.95rem;
  font-size: 0.85rem;
  animation: workspace-pulse 1.4s ease-in-out infinite;
}

.chat-workspace__composer {
  border-top: 1px solid rgba(111, 69, 31, 0.16);
  padding: 1rem 1.25rem 1.25rem;
  background: linear-gradient(180deg, rgba(247, 240, 228, 0.86) 0%, rgba(242, 233, 218, 0.94) 100%);
}

.chat-workspace__composer-inner {
  display: flex;
  gap: 0.75rem;
}

.chat-workspace__input {
  flex: 1;
  min-width: 0;
  border: 1px solid rgba(111, 69, 31, 0.16);
  background: rgba(255, 251, 242, 0.98);
  color: var(--ink-strong);
  border-radius: 1rem;
  padding: 0.9rem 1rem;
  font-size: 0.94rem;
  outline: none;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.chat-workspace__input:focus {
  border-color: rgba(111, 69, 31, 0.38);
  box-shadow: 0 0 0 3px rgba(141, 93, 49, 0.12);
}

.chat-workspace__input:disabled {
  background: rgba(241, 233, 220, 0.92);
  cursor: not-allowed;
}

.chat-workspace__send {
  border: 1px solid rgba(111, 69, 31, 0.18);
  background: linear-gradient(180deg, #8d5d31 0%, #6f451f 100%);
  color: #fffaf0;
  border-radius: 1rem;
  padding: 0 1.1rem;
  font-size: 0.9rem;
  font-weight: 700;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.chat-workspace__send:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(83, 49, 21, 0.18);
}

.chat-workspace__send:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@keyframes workspace-pulse {
  0%,
  100% {
    opacity: 0.72;
  }

  50% {
    opacity: 1;
  }
}

@media (min-width: 768px) {
  .chat-workspace__header {
    padding: 1.5rem 1.5rem 1.15rem;
  }

  .chat-workspace__messages {
    padding: 1.5rem;
  }

  .chat-workspace__composer {
    padding: 1rem 1.5rem 1.5rem;
  }
}
</style>
