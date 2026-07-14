<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AgentToolCard from '../components/agent/AgentToolCard.vue'

import {
  approveTool,
  createAgentSession,
  getAgentSession,
  rejectTool,
  streamAgentMessage,
  type AgentStreamEvent,
} from '../api/agentV2'
import { useProjectStore } from '../stores/project'

interface ChatItem {
  kind: 'user' | 'assistant' | 'tool' | 'approval'
  text: string
  toolName?: string
  isError?: boolean
  approvalId?: string
  toolIndex?: number
}

interface SessionItem {
  session_id: string
  project_id: string
}

const route = useRoute()
const projectStore = useProjectStore()
const pid = computed(() => String(route.params.id ?? ''))

const sessionId = ref<string | null>(null)
const sessions = ref<SessionItem[]>([])
const items = ref<ChatItem[]>([])
const input = ref('')
const busy = ref(false)
const error = ref('')
const lastStop = ref('')
const listEl = ref<HTMLElement | null>(null)

onMounted(async () => {
  await projectStore.loadProject(pid.value)
  await loadSessions()
})

async function loadSessions() {
  try {
    const resp = await fetch(`/api/v2/projects/${pid.value}/sessions`)
    const data = await resp.json()
    sessions.value = data.sessions || []
  } catch { /* ignore */ }
}

async function newSession() {
  sessionId.value = null
  items.value = []
  error.value = ''
  await loadSessions()
}

async function switchSession(sid: string) {
  sessionId.value = sid
  try {
    const s = await getAgentSession(sid)
    items.value = s.messages
      .filter((m: any) => m.role !== 'system')
      .map((m: any) => {
        if (m.role === 'user') return { kind: 'user', text: m.content || '' }
        if (m.role === 'tool') return { kind: 'tool', toolName: m.tool_call_id || 'tool', text: m.content || '' }
        return { kind: 'assistant', text: m.content || '' }
      }) as ChatItem[]
  } catch {
    error.value = '无法加载会话历史'
  }
}

async function scrollToBottom() {
  await nextTick()
  listEl.value?.scrollTo({ top: listEl.value.scrollHeight })
}

async function onApprove(item: ChatItem) {
  if (!sessionId.value || !item.approvalId) return
  try {
    await approveTool(sessionId.value)
    item.text = '✅ 已批准'
  } catch (e) {
    error.value = `批准失败: ${e instanceof Error ? e.message : e}`; } }

async function onReject(item: ChatItem) {
  if (!sessionId.value || !item.approvalId) return
  try {
    await rejectTool(sessionId.value)
    item.text = '❌ 已拒绝'
  } catch (e) {
    error.value = `拒绝失败: ${e instanceof Error ? e.message : e}`

function onEvent(event: AgentStreamEvent) {
  if (event.event === 'assistant_delta') {
    const last = items.value[items.value.length - 1]
    if (last && last.kind === 'assistant') last.text += event.data.text
    else items.value.push({ kind: 'assistant', text: event.data.text })
  } else if (event.event === 'tool_call_started') {
    items.value.push({ kind: 'tool', toolName: event.data.name, text: 'pending' })
  } else if (event.event === 'tool_call_finished') {
    const item = [...items.value].reverse().find(
      (i) => i.kind === 'tool' && i.toolName === event.data.name && i.text === 'pending'
    )
    if (item) {
      item.text = event.data.is_error ? 'error' : 'ok'
      item.isError = event.data.is_error
      item.toolIndex = Date.now()
    }
  } else if (event.event === 'approval_pending') {
    items.value.push({
      kind: 'approval',
      approvalId: event.data.approval_id,
      toolName: event.data.tool_name,
      text: `${event.data.tool_name}(${JSON.stringify(event.data.arguments, null, 1)})`,
    })
  } else if (event.event === 'turn_ended') {
    lastStop.value = `${event.data.stop_reason} · ${event.data.iterations} 轮`
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
      sessionId.value = (await createAgentSession(pid.value)).session_id
      await loadSessions()
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
    <!-- Session sidebar -->
    <aside class="agent-chat__sidebar">
      <button class="agent-chat__new-btn" @click="newSession">
        + 新会话
      </button>
      <div class="agent-chat__session-list">
        <div
          v-for="s in sessions"
          :key="s.session_id"
          class="agent-chat__session-item"
          :class="{ 'agent-chat__session-item--active': s.session_id === sessionId }"
          @click="switchSession(s.session_id)"
        >
          {{ s.session_id.slice(0, 8) }}
        </div>
        <div v-if="sessions.length === 0" class="agent-chat__session-empty">
          暂无会话
        </div>
      </div>
      <div v-if="lastStop" class="agent-chat__stop-info">{{ lastStop }}</div>
    </aside>

    <!-- Main chat area -->
    <main class="agent-chat__main">
      <div ref="listEl" class="agent-chat__messages">
        <!-- Empty state -->
        <div v-if="items.length === 0 && !busy" class="agent-chat__empty">
          <div class="agent-chat__empty-icon">🤖</div>
          <div class="agent-chat__empty-title">开始与 Agent 对话</div>
          <div class="agent-chat__empty-hint">
            试试：帮我看看项目进度、写一章新内容、帮我检查人物设定是否有矛盾
          </div>
        </div>

        <!-- Messages -->
        <div v-for="(item, idx) in items" :key="idx">
          <div v-if="item.kind === 'user'" class="agent-chat__bubble agent-chat__bubble--user">
            {{ item.text }}
          </div>
          <div v-else-if="item.kind === 'assistant'" class="agent-chat__bubble agent-chat__bubble--assistant">
            {{ item.text }}
          </div>
          <div v-else-if="item.kind === 'approval'" class="agent-chat__approval">
            <div class="agent-chat__approval-title">🔐 需要审批</div>
            <pre class="agent-chat__approval-body">{{ item.text }}</pre>
            <div class="agent-chat__approval-actions">
              <button
                class="agent-chat__btn agent-chat__btn--approve"
                :disabled="!item.text.includes('(')"
                @click="onApprove(item)"
              >批准</button>
              <button
                class="agent-chat__btn agent-chat__btn--reject"
                :disabled="!item.text.includes('(')"
                @click="onReject(item)"
              >拒绝</button>
            </div>
          </div>
          <AgentToolCard
            v-else-if="item.kind === 'tool'"
            :tool-name="item.toolName || '?'"
            :is-error="item.isError"
            :is-pending="item.text === 'pending'"
            :key="item.toolIndex || idx"
          />
        </div>

        <!-- Loading -->
        <div v-if="busy && items.length > 0" class="agent-chat__loading">
          <span class="agent-chat__loading-dot" />
          <span class="agent-chat__loading-dot" />
          <span class="agent-chat__loading-dot" />
        </div>
      </div>

      <div v-if="error" class="agent-chat__error">
        ⚠️ {{ error }}
        <button class="agent-chat__error-close" @click="error = ''">✕</button>
      </div>

      <form class="agent-chat__input-row" @submit.prevent="send">
        <textarea
          v-model="input"
          :disabled="busy"
          class="agent-chat__input"
          placeholder="对 Agent 说点什么…"
          rows="2"
          data-testid="agent-v2-input"
          @keydown.enter.exact.prevent="send"
        />
        <button
          type="submit"
          :disabled="busy || !input.trim()"
          class="agent-chat__send-btn"
        >
          {{ busy ? '…' : '发送' }}
        </button>
      </form>
    </main>
  </div>
</template>

<style scoped>
.agent-chat {
  display: grid;
  grid-template-columns: 180px 1fr;
  height: 100%;
  gap: 0;
}

/* --- Sidebar --- */
.agent-chat__sidebar {
  border-right: 1px solid var(--color-border);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  background: var(--color-bg-secondary);
  overflow-y: auto;
}

.agent-chat__new-btn {
  border: 1px solid var(--color-brand);
  background: var(--color-brand-light);
  color: var(--color-brand);
  border-radius: var(--radius-md);
  padding: var(--space-1) var(--space-3);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.agent-chat__new-btn:hover {
  background: var(--color-brand-subtle);
}

.agent-chat__session-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.agent-chat__session-item {
  font-size: var(--text-xs);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  cursor: pointer;
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.agent-chat__session-item:hover {
  background: var(--color-bg-tertiary);
}

.agent-chat__session-item--active {
  background: var(--color-brand-light);
  color: var(--color-brand);
  font-weight: var(--font-medium);
}

.agent-chat__session-empty {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.agent-chat__stop-info {
  font-size: 0.625rem;
  color: var(--color-text-tertiary);
}

/* --- Main --- */
.agent-chat__main {
  display: flex;
  flex-direction: column;
  padding: var(--space-4);
  gap: var(--space-3);
  min-width: 0;
}

.agent-chat__messages {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  overflow-y: auto;
}

/* --- Messages --- */
.agent-chat__bubble {
  max-width: 84%;
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  width: fit-content;
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

/* --- Empty --- */
.agent-chat__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: var(--space-3);
  color: var(--color-text-tertiary);
}

.agent-chat__empty-icon {
  font-size: 2.5rem;
}

.agent-chat__empty-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
}

.agent-chat__empty-hint {
  font-size: var(--text-sm);
  max-width: 320px;
  text-align: center;
  line-height: var(--leading-relaxed);
}

/* --- Approval --- */
.agent-chat__approval {
  max-width: 84%;
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
  font-size: var(--text-sm);
}

.agent-chat__approval-body {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
  white-space: pre-wrap;
  margin: 0;
}

.agent-chat__approval-actions {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-2);
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
  opacity: 0.3;
  cursor: not-allowed;
}

.agent-chat__btn--approve {
  background: var(--color-success);
}

.agent-chat__btn--reject {
  background: var(--color-error);
}

/* --- Error --- */
.agent-chat__error {
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  background: var(--color-error-light);
  color: var(--color-error);
  font-size: var(--text-sm);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.agent-chat__error-close {
  border: none;
  background: none;
  color: var(--color-error);
  cursor: pointer;
  font-size: var(--text-base);
}

/* --- Input --- */
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
  font-family: var(--font-family);
  resize: none;
}

.agent-chat__input:focus {
  border-color: var(--color-brand);
}

.agent-chat__input:disabled {
  background: var(--color-bg-secondary);
}

.agent-chat__send-btn {
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-brand);
  color: var(--color-text-inverse);
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--transition-fast);
}

.agent-chat__send-btn:hover:not(:disabled) {
  background: var(--color-brand-hover);
}

.agent-chat__send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* --- Loading dots --- */
.agent-chat__loading {
  display: flex;
  gap: var(--space-1);
  padding: var(--space-2);
}

.agent-chat__loading-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-text-tertiary);
  animation: agent-dot-pulse 1.2s infinite ease-in-out;
}

.agent-chat__loading-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.agent-chat__loading-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes agent-dot-pulse {
  0%, 80%, 100% { opacity: 0.3; }
  40% { opacity: 1; }
}
</style>
