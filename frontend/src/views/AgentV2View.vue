<script setup lang="ts">
// M1 开发者验证视图（未在导航中暴露）：直接与 /api/v2 Agent 会话对话。
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
  <div class="flex h-full flex-col gap-3 p-4" data-testid="agent-v2-view">
    <div class="text-sm text-gray-500">
      Agent v2 开发验证 · 项目 {{ projectId }}
      <span v-if="sessionId"> · 会话 {{ sessionId.slice(0, 8) }}</span>
      <span v-if="lastStop"> · {{ lastStop }}</span>
    </div>

    <div ref="listEl" class="flex-1 space-y-2 overflow-y-auto rounded border border-gray-200 p-3">
      <div v-for="(item, idx) in items" :key="idx">
        <div v-if="item.kind === 'user'" class="ml-auto w-fit max-w-[80%] rounded bg-blue-50 px-3 py-2">
          {{ item.text }}
        </div>
        <div v-else-if="item.kind === 'assistant'" class="w-fit max-w-[80%] whitespace-pre-wrap rounded bg-gray-50 px-3 py-2">
          {{ item.text }}
        </div>
        <div
          v-else-if="item.kind === 'approval'"
          class="w-fit max-w-[80%] rounded border border-amber-300 bg-amber-50 px-3 py-2"
        >
          <div class="mb-1 font-medium text-amber-800">🔐 审批请求</div>
          <div class="mb-2 font-mono text-xs text-amber-700">{{ item.text }}</div>
          <div class="flex gap-2">
            <button
              class="rounded bg-green-600 px-3 py-1 text-xs text-white disabled:opacity-50"
              :disabled="item.text.startsWith('✅') || item.text.startsWith('❌')"
              @click="onApprove(item)"
            >
              批准
            </button>
            <button
              class="rounded bg-red-600 px-3 py-1 text-xs text-white disabled:opacity-50"
              :disabled="item.text.startsWith('✅') || item.text.startsWith('❌')"
              @click="onReject(item)"
            >
              拒绝
            </button>
          </div>
        </div>
        <div
          v-else
          class="w-fit max-w-[80%] rounded border px-3 py-1 font-mono text-xs"
          :class="item.isError ? 'border-red-300 bg-red-50' : 'border-gray-300 bg-gray-100'"
        >
          🔧 {{ item.toolName }} → {{ item.text }}
        </div>
      </div>
    </div>

    <div v-if="error" class="rounded border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700">
      {{ error }}
    </div>

    <form class="flex gap-2" @submit.prevent="send">
      <input
        v-model="input"
        :disabled="busy"
        class="flex-1 rounded border border-gray-300 px-3 py-2"
        placeholder="对 Agent 说点什么…"
        data-testid="agent-v2-input"
      />
      <button
        type="submit"
        :disabled="busy || !input.trim()"
        class="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
      >
        发送
      </button>
    </form>
  </div>
</template>
