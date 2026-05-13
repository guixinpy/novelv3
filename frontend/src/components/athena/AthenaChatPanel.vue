<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import ChatMessageList from '../chat/ChatMessageList.vue'
import ChatInput from '../chat/ChatInput.vue'
import ModelTraceDrawer from '../modelTrace/ModelTraceDrawer.vue'
import { useAthenaStore } from '../../stores/athena'
import { useProjectStore } from '../../stores/project'
import type { ChatHistoryMessage } from '../../api/types'

const props = defineProps<{
  open: boolean
  projectId: string
}>()

const emit = defineEmits<{
  close: []
}>()

const athena = useAthenaStore()
const project = useProjectStore()
const activeTraceId = ref<string | null>(null)

const messages = computed(() =>
  (athena.messages || []).map((m: ChatHistoryMessage) => ({
    id: m.id,
    role: m.role,
    content: m.content,
    message_type: m.message_type || null,
    meta: m.meta || null,
    pending_action: null,
    action_result: null,
    trace_id: m.trace_id || null,
    created_at: m.created_at || null,
  })),
)

const contextSnapshot = computed(() => {
  const chapterCount = Array.isArray(project.chapters) ? project.chapters.length : 0
  const wordCount = Number(project.currentProject?.current_word_count || 0)
  const profileVersion = athena.ontology?.profile_version
  const indexedDocuments = athena.retrievalDiagnostics?.total_documents

  return {
    chapterCount,
    wordCount,
    profileLabel: profileVersion ? `Profile v${profileVersion}` : 'Profile 未建立',
    indexLabel: indexedDocuments === undefined || indexedDocuments === null
      ? '未读取'
      : String(Number(indexedDocuments)),
  }
})

watch(() => props.open, (open) => {
  if (!open) closeTrace()
})

watch(() => props.projectId, () => {
  closeTrace()
})

async function onSend(text: string) {
  await athena.sendChat(props.projectId, text)
}

function openTrace(traceId: string) {
  if (!traceId) return
  activeTraceId.value = traceId
}

function closeTrace() {
  activeTraceId.value = null
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
        <section class="athena-chat-panel__context" aria-label="Athena 当前上下文">
          <div class="athena-chat-panel__context-head">当前上下文</div>
          <div class="athena-chat-panel__context-metrics">
            <span>章节 {{ contextSnapshot.chapterCount }}</span>
            <span>字数 {{ contextSnapshot.wordCount }}</span>
            <span>{{ contextSnapshot.profileLabel }}</span>
            <span>索引文档 {{ contextSnapshot.indexLabel }}</span>
          </div>
          <p class="athena-chat-panel__context-note">
            历史回答基于当时上下文；项目状态变化后，请重新提问或清空上下文。
          </p>
        </section>
        <ChatMessageList
          :messages="messages"
          :loading="athena.chatLoading"
          @open-trace="openTrace"
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
    <ModelTraceDrawer
      :project-id="projectId"
      :trace-id="activeTraceId"
      :open="open && !!activeTraceId"
      @close="closeTrace"
    />
  </Teleport>
</template>

<style scoped>
.athena-chat-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(var(--athena-chat-width, 400px), 100vw);
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

.athena-chat-panel__context {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-bg-secondary);
}

.athena-chat-panel__context-head {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
}

.athena-chat-panel__context-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.athena-chat-panel__context-note {
  margin: 0;
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
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
