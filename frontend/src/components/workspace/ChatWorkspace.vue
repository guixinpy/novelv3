<template>
  <section class="chat-workspace">
    <header class="chat-workspace__header">
      <div class="chat-workspace__headline">
        <h1 class="chat-workspace__title">{{ project.name }}</h1>
        <p class="chat-workspace__meta">
          <span>{{ project.genre || '未分类题材' }}</span>
          <span class="chat-workspace__dot" />
          <span>{{ project.current_word_count || 0 }} 字</span>
          <span class="chat-workspace__dot" />
          <span>{{ projectStatusLabel }}</span>
        </p>
      </div>
      <span class="chat-workspace__mode">{{ modeLabel }}</span>
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

    <footer class="chat-workspace__composer">
      <ChatCommandMenu
        v-if="showCommandMenu"
        :commands="commandCandidates"
        :active-index="activeCommandIndex"
        class="chat-workspace__command-menu"
        @pick="pickCommand"
      />
      <div class="chat-workspace__composer-inner">
        <input
          v-model="input"
          :disabled="loading || !!pendingAction"
          class="chat-workspace__input"
          placeholder="输入消息，或键入 / 查看命令"
          @keydown="onInputKeydown"
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
import ChatCommandMenu from './ChatCommandMenu.vue'
import { filterChatCommands, type ChatCommandDefinition } from './chatCommands'
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
const activeCommandIndex = ref(0)
const commandMenuDismissed = ref(false)

const modeLabel = computed(() => (props.mode === 'locked' ? '锁定观察' : '自动联动'))
const commandCandidates = computed(() => filterChatCommands(input.value))
const showCommandMenu = computed(() => {
  if (commandMenuDismissed.value) return false
  if (!input.value.startsWith('/')) return false
  return commandCandidates.value.length > 0
})

const projectStatusLabel = computed(() => {
  const status = String(props.project?.status || '').trim()
  const phase = String(props.project?.current_phase || '').trim()

  if (status === 'writing') return '正文写作中'
  if (status === 'outline_generated') return '大纲已生成'
  if (status === 'storyline_generated') return '故事线已生成'
  if (status === 'draft') return '待补全'

  if (phase === 'outline') return '大纲阶段'
  if (phase === 'storyline') return '故事线阶段'
  if (phase === 'setup') return '设定阶段'

  return '进行中'
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
  activeCommandIndex.value = 0
  commandMenuDismissed.value = false
}

function pickCommand(command: ChatCommandDefinition) {
  input.value = `/${command.name} `
  activeCommandIndex.value = 0
  commandMenuDismissed.value = true
}

function onInputKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && showCommandMenu.value) {
    commandMenuDismissed.value = true
    return
  }

  if (!showCommandMenu.value) {
    if (event.key === 'Enter') {
      event.preventDefault()
      submit()
    }
    return
  }

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    activeCommandIndex.value = (activeCommandIndex.value + 1) % commandCandidates.value.length
    return
  }

  if (event.key === 'ArrowUp') {
    event.preventDefault()
    const total = commandCandidates.value.length
    activeCommandIndex.value = (activeCommandIndex.value - 1 + total) % total
    return
  }

  if (event.key === 'Enter') {
    event.preventDefault()
    const command = commandCandidates.value[activeCommandIndex.value]
    if (command) {
      pickCommand(command)
    }
  }
}

function forwardDecision(decision: string, comment?: string) {
  emit('decide', decision, comment)
}

watch(() => props.messages.length, scrollToBottom)
watch(() => props.loading, scrollToBottom)
watch(input, () => {
  commandMenuDismissed.value = false
})
watch(commandCandidates, (nextCommands) => {
  if (!nextCommands.length) {
    activeCommandIndex.value = 0
    return
  }
  if (activeCommandIndex.value >= nextCommands.length) {
    activeCommandIndex.value = 0
  }
})
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
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.82rem 1.25rem 0.82rem;
  border-bottom: 1px solid rgba(111, 69, 31, 0.16);
  background:
    linear-gradient(135deg, rgba(255, 249, 236, 0.94) 0%, rgba(240, 230, 209, 0.88) 100%);
}

.chat-workspace__headline {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem 0.85rem;
}

.chat-workspace__mode {
  border: 1px solid rgba(111, 69, 31, 0.18);
  background: rgba(255, 248, 233, 0.8);
  color: var(--ink-muted);
  border-radius: 999px;
  padding: 0.28rem 0.72rem;
  font-size: 0.7rem;
  font-weight: 600;
  white-space: nowrap;
}

.chat-workspace__title {
  color: var(--ink-strong);
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  font-size: clamp(1.22rem, 1.9vw, 1.62rem);
  line-height: 1;
  white-space: nowrap;
}

.chat-workspace__meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem;
  color: var(--ink-muted);
  font-size: 0.82rem;
  line-height: 1.45;
  min-width: 0;
}

.chat-workspace__dot {
  width: 0.24rem;
  height: 0.24rem;
  border-radius: 999px;
  background: rgba(111, 69, 31, 0.26);
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

.chat-workspace__command-menu {
  margin-bottom: 0.65rem;
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
    padding: 0.9rem 1.5rem 0.88rem;
  }

  .chat-workspace__messages {
    padding: 1.5rem;
  }

  .chat-workspace__composer {
    padding: 1rem 1.5rem 1.5rem;
  }
}

@media (max-width: 767px) {
  .chat-workspace__header {
    align-items: flex-start;
  }

  .chat-workspace__mode {
    align-self: flex-start;
  }

  .chat-workspace__title {
    white-space: normal;
  }
}
</style>
