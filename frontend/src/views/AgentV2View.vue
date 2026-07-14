<script setup lang="ts">
// Agent v2 对话视图：直接与 /api/v2 Agent 会话对话。
import { computed, nextTick, ref } from 'vue'
import { useRoute } from 'vue-router'

import {
  approveTool,
  createAgentSession,
  rejectTool,
  streamAgentMessage,
  type AgentStreamEvent,
} from '../api/agentV2'

interface ChatItem {
  kind: 'user' | 'assistant' | 'tool' | 'approval'
  text: string
  toolName?: string
  isError?: boolean
  approvalId?: string
}

const route = useRoute()
const projectId = computed(() => String(route.params.id ?? ''))

const sessionId = ref<string | null>(null)
const items = ref<ChatItem[]>([])
const input = ref('')
const busy = ref(false)
const error = ref('')
const lastStop = ref('')
const listEl = ref<HTMLElement | null>(null)

async function scrollToBottom() {
  await nextTick()
  listEl.value?.scrollTo({ top: listEl.value.scrollHeight })
}

async function onApprove(item: ChatItem) {
  if (!sessionId.value || !item.approvalId) return
  await approveTool(sessionId.value)
  item.text = '✅ 已批准'
}

async function onReject(item: ChatItem) {
  if (!sessionId.value || !item.approvalId) return
  await rejectTool(sessionId.value)
  item.text = '❌ 已拒绝'
}

function onEvent(event: AgentStreamEvent) {
  if (event.event === 'assistant_delta') {
    const last = items.value[items.value.length - 1]
    if (last && last.kind === 'assistant') last.text += event.data.text
    else items.value.push({ kind: 'assistant', text: event.data.text })
  } else if (event.event === 'tool_call_started') {
    items.value.push({ kind: 'tool', toolName: event.data.name, text: '执行中…' })
  } else if (event.event === 'tool_call_finished') {
    const item = [...items.value].reverse().find((i) => i.kind === 'tool' && i.toolName === event.data.name)
    if (item) {
      item.text = event.data.result_text.slice(0, 400)
      item.isError = event.data.is_error
    }
  } else if (event.event === 'approval_pending') {
    items.value.push({
      kind: 'approval',
      approvalId: event.data.approval_id,
      toolName: event.data.tool_name,
      text: `等待审批：${event.data.tool_name}(${JSON.stringify(event.data.arguments)})`,
    })
  } else if (event.event === 'turn_ended') {
    lastStop.value = `${event.data.stop_reason} · ${event.data.iterations} 轮 · ${
      event.data.usage.prompt_tokens + event.data.usage.completion_tokens
    } tokens`
  }
  void scrollToBottom()
}

async function send() {
  const content = input.value.trim()
  if (!content || busy.value) return
  busy.value = true
  error.value = ''
  input.value = ''
  items.value.push({ kind: 'user', text: content })
  try {
    if (!sessionId.value) {
      sessionId.value = (await createAgentSession(projectId.value)).session_id
    }
    await streamAgentMessage(sessionId.value, content, onEvent)
  } catch (e) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="agent-chat" data-testid="agent-v2-view">
    <div class="agent-chat__header">
      <span class="agent-chat__title">Agent 对话 · 项目 {{ projectId }}</span>
      <span v-if="sessionId" class="agent-chat__session">会话 {{ sessionId.slice(0, 8) }}</span>
      <span v-if="lastStop" class="agent-chat__stats">{{ lastStop }}</span>
    </div>

    <div ref="listEl" class="agent-chat__messages">
      <div v-for="(item, idx) in items" :key="idx">
        <div v-if="item.kind === 'user'" class="agent-chat__bubble agent-chat__bubble--user">
          {{ item.text }}
        </div>
        <div v-else-if="item.kind === 'assistant'" class="agent-chat__bubble agent-chat__bubble--assistant">
          {{ item.text }}
        </div>
        <div
          v-else-if="item.kind === 'approval'"
          class="agent-chat__approval"
        >
          <div class="agent-chat__approval-title">🔐 审批请求</div>
          <div class="agent-chat__approval-body">{{ item.text }}</div>
          <div class="agent-chat__approval-actions">
            <button
              class="agent-chat__btn agent-chat__btn--approve"
              :disabled="item.text.startsWith('✅') || item.text.startsWith('❌')"
              @click="onApprove(item)"
            >
              批准
            </button>
            <button
              class="agent-chat__btn agent-chat__btn--reject"
              :disabled="item.text.startsWith('✅') || item.text.startsWith('❌')"
              @click="onReject(item)"
            >
              拒绝
            </button>
          </div>
        </div>
        <div
          v-else
          class="agent-chat__tool"
          :class="{ 'agent-chat__tool--error': item.isError }"
        >
          🔧 {{ item.toolName }} → {{ item.text }}
        </div>
      </div>
    </div>

    <div v-if="error" class="agent-chat__error">
      {{ error }}
    </div>

    <form class="agent-chat__input-row" @submit.prevent="send">
      <input
        v-model="input"
        :disabled="busy"
        class="agent-chat__input"
        placeholder="对 Agent 说点什么…"
        data-testid="agent-v2-input"
      />
      <button
        type="submit"
        :disabled="busy || !input.trim()"
        class="agent-chat__send-btn"
      >
        发送
      </button>
    </form>
  </div>
</template>

<style scoped>
.agent-chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: var(--space-3);
  padding: var(--space-4);
}

.agent-chat__header {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.agent-chat__title {
  font-weight: var(--font-medium);
}

.agent-chat__session,
.agent-chat__stats {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.agent-chat__messages {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}

.agent-chat__bubble {
  max-width: 80%;
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
}

.agent-chat__bubble--user {
  margin-left: auto;
  background: var(--color-brand-light);
  color: var(--color-text-primary);
}

.agent-chat__bubble--assistant {
  white-space: pre-wrap;
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
}

.agent-chat__approval {
  max-width: 80%;
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-md);
  padding: var(--space-3);
  background: var(--color-warning-light);
  width: fit-content;
}

.agent-chat__approval-title {
  font-weight: var(--font-semibold);
  color: var(--color-warning-dark);
  margin-bottom: var(--space-1);
}

.agent-chat__approval-body {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
}

.agent-chat__approval-actions {
  display: flex;
  gap: var(--space-2);
}

.agent-chat__btn {
  border: none;
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-xs);
  color: var(--color-text-inverse);
  cursor: pointer;
}

.agent-chat__btn:disabled {
  opacity: 0.5;
}

.agent-chat__btn--approve {
  background: var(--color-success);
}

.agent-chat__btn--reject {
  background: var(--color-error);
}

.agent-chat__tool {
  max-width: 80%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-3);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  width: fit-content;
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
}

.agent-chat__tool--error {
  border-color: var(--color-error);
  background: var(--color-error-light);
}

.agent-chat__error {
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  background: var(--color-error-light);
  color: var(--color-error);
  font-size: var(--text-sm);
}

.agent-chat__input-row {
  display: flex;
  gap: var(--space-2);
}

.agent-chat__input {
  flex: 1;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  outline: none;
  background: var(--color-bg-white);
  color: var(--color-text-primary);
}

.agent-chat__input:focus {
  border-color: var(--color-brand);
}

.agent-chat__input:disabled {
  background: var(--color-bg-secondary);
  opacity: 0.7;
}

.agent-chat__send-btn {
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-brand);
  color: var(--color-text-inverse);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.agent-chat__send-btn:hover:not(:disabled) {
  background: var(--color-brand-hover);
}

.agent-chat__send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
