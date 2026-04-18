<template>
  <div
    class="message-row"
    :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
  >
    <ChatSummaryCard
      v-if="msg.message_type === 'summary'"
      :content="msg.content"
    />
    <div
      v-else
      class="message-bubble"
      :class="bubbleClass"
    >
      <div class="message-role" :class="msg.role === 'user' ? 'message-role--user' : ''">
        {{ roleName }}
      </div>
      <div class="message-copy">{{ msg.content }}</div>
      <ActionCard
        v-if="msg.pending_action && isLatest"
        :action="msg.pending_action"
        :disabled="loading"
        @decide="onDecide"
      />
      <div
        v-if="msg.action_result"
        class="message-result"
        :class="resultClass"
      >
        {{ resultText }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ActionCard from './ActionCard.vue'
import ChatSummaryCard from './ChatSummaryCard.vue'

const props = defineProps<{ msg: any; isLatest: boolean; loading: boolean }>()
const emit = defineEmits<{ decide: [decision: string, comment?: string] }>()

const roleName = computed(() => {
  if (props.msg.role === 'user') return '我'
  if (props.msg.role === 'system') return '系统'
  return '墨舟'
})

const bubbleClass = computed(() => {
  if (props.msg.role === 'user') return 'message-bubble--user'
  if (props.msg.role === 'system') return 'message-bubble--system'
  return 'message-bubble--assistant'
})

const TYPE_LABELS: Record<string, string> = {
  generate_setup: '生成设定',
  generate_storyline: '生成故事线',
  generate_outline: '生成大纲',
  preview_setup: '生成设定',
  preview_storyline: '生成故事线',
  preview_outline: '生成大纲',
}

const resultText = computed(() => {
  const r = props.msg.action_result
  if (!r) return ''
  const label = TYPE_LABELS[r.type] || r.type
  if (r.status === 'success') return `✓ ${label}执行成功`
  if (r.status === 'cancelled') return `✗ 操作已取消`
  if (r.status === 'generating') return `⏳ ${label}生成中...`
  if (r.status === 'failed') return `✗ ${label}失败`
  return `${label}: ${r.status}`
})

const resultClass = computed(() => {
  const status = props.msg.action_result?.status
  if (status === 'success') return 'message-result--success'
  if (status === 'failed') return 'message-result--failed'
  return 'message-result--neutral'
})

function onDecide(decision: string, comment?: string) {
  emit('decide', decision, comment)
}
</script>

<style scoped>
.message-row {
  display: flex;
}

.message-bubble {
  max-width: 85%;
  border-radius: 1.35rem;
  padding: 0.95rem 1rem;
  border: 1px solid rgba(111, 69, 31, 0.14);
  box-shadow: 0 14px 28px rgba(78, 53, 26, 0.08);
}

.message-bubble--assistant {
  background:
    linear-gradient(180deg, rgba(255, 250, 242, 0.97) 0%, rgba(245, 236, 220, 0.94) 100%);
  color: var(--ink-strong);
}

.message-bubble--system {
  background:
    linear-gradient(180deg, rgba(245, 232, 201, 0.95) 0%, rgba(237, 223, 194, 0.92) 100%);
  color: var(--ink-strong);
}

.message-bubble--user {
  background:
    linear-gradient(180deg, rgba(130, 85, 45, 0.94) 0%, rgba(98, 62, 31, 0.98) 100%);
  color: #fff8ef;
  border-color: rgba(88, 55, 25, 0.36);
}

.message-role {
  margin-bottom: 0.4rem;
  color: var(--ink-muted);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.message-role--user {
  color: rgba(255, 242, 220, 0.78);
}

.message-copy {
  white-space: pre-wrap;
  font-size: 0.94rem;
  line-height: 1.65;
}

.message-result {
  margin-top: 0.75rem;
  border-radius: 0.9rem;
  padding: 0.5rem 0.7rem;
  font-size: 0.76rem;
  font-weight: 600;
}

.message-result--success {
  background: rgba(108, 134, 93, 0.14);
  color: #4b5f3f;
}

.message-result--failed {
  background: rgba(154, 95, 69, 0.14);
  color: #8d4c34;
}

.message-result--neutral {
  background: rgba(111, 69, 31, 0.08);
  color: var(--ink-muted);
}
</style>
