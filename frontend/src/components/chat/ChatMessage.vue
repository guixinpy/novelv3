<script setup lang="ts">
import { computed } from 'vue'
import ActionCard from '../ActionCard.vue'
import ChatSummaryCard from '../ChatSummaryCard.vue'

const props = defineProps<{
  msg: any
  isLatest: boolean
  loading: boolean
}>()

const emit = defineEmits<{
  decide: [decision: string, comment?: string]
}>()

const roleName = computed(() => {
  if (props.msg.role === 'user') return '我'
  if (props.msg.role === 'system') return '系统'
  return '墨舟'
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

const resultVariant = computed(() => {
  const status = props.msg.action_result?.status
  if (status === 'success') return 'success'
  if (status === 'failed') return 'error'
  return 'neutral'
})

const summaryTitle = computed(() => {
  const title = props.msg.meta?.title
  return typeof title === 'string' && title.trim() ? title : '会话摘要'
})

const summaryCompactedCount = computed(() => {
  const compactedCount = props.msg.meta?.compacted_count
  return typeof compactedCount === 'number' ? compactedCount : 0
})

function onDecide(decision: string, comment?: string) {
  emit('decide', decision, comment)
}
</script>

<template>
  <div
    class="chat-msg"
    :class="msg.role === 'user' ? 'chat-msg--right' : 'chat-msg--left'"
  >
    <ChatSummaryCard
      v-if="msg.message_type === 'summary'"
      :content="msg.content"
      :title="summaryTitle"
      :compacted-count="summaryCompactedCount"
    />
    <div
      v-else
      class="chat-msg__bubble"
      :class="`chat-msg__bubble--${msg.role}`"
    >
      <div class="chat-msg__role">{{ roleName }}</div>
      <div class="chat-msg__content">{{ msg.content }}</div>
      <ActionCard
        v-if="msg.pending_action && isLatest"
        :action="msg.pending_action"
        :disabled="loading"
        @decide="onDecide"
      />
      <div
        v-if="msg.action_result"
        class="chat-msg__result"
        :class="`chat-msg__result--${resultVariant}`"
      >
        {{ resultText }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-msg {
  display: flex;
}

.chat-msg--left {
  justify-content: flex-start;
}

.chat-msg--right {
  justify-content: flex-end;
}

.chat-msg__bubble {
  max-width: 85%;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
}

.chat-msg__bubble--assistant {
  background: var(--color-bg-white);
  border-left: 3px solid var(--color-brand);
}

.chat-msg__bubble--system {
  background: var(--color-bg-secondary);
  border-left: 3px solid var(--color-border-strong);
}

.chat-msg__bubble--user {
  background: var(--color-brand-light);
  max-width: 80%;
}

.chat-msg__role {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-1);
}

.chat-msg__content {
  white-space: pre-wrap;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text-primary);
}

.chat-msg__result {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.chat-msg__result--success {
  background: var(--color-success-light);
  color: var(--color-success);
}

.chat-msg__result--error {
  background: var(--color-error-light);
  color: var(--color-error);
}

.chat-msg__result--neutral {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}
</style>
