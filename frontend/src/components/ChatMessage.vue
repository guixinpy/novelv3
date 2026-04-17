<template>
  <div
    class="flex"
    :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
  >
    <div
      class="max-w-[85%] rounded-lg px-4 py-2"
      :class="bubbleClass"
    >
      <div class="text-xs mb-1" :class="msg.role === 'user' ? 'text-indigo-400' : 'text-gray-400'">
        {{ roleName }}
      </div>
      <div class="text-sm whitespace-pre-wrap">{{ msg.content }}</div>
      <ActionCard
        v-if="msg.pending_action && isLatest"
        :action="msg.pending_action"
        :disabled="loading"
        @decide="onDecide"
      />
      <div
        v-if="msg.action_result"
        class="mt-2 text-xs px-2 py-1 rounded"
        :class="msg.action_result.status === 'success' ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-600'"
      >
        {{ resultText }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ActionCard from './ActionCard.vue'

const props = defineProps<{ msg: any; isLatest: boolean; loading: boolean }>()
const emit = defineEmits<{ decide: [decision: string, comment?: string] }>()

const roleName = computed(() => {
  if (props.msg.role === 'user') return '我'
  if (props.msg.role === 'system') return '系统'
  return '墨舟'
})

const bubbleClass = computed(() => {
  if (props.msg.role === 'user') return 'bg-indigo-100 text-gray-900'
  if (props.msg.role === 'system') return 'bg-amber-50 text-gray-800 border border-amber-200'
  return 'bg-gray-100 text-gray-900'
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
  return `${label}: ${r.status}`
})

function onDecide(decision: string, comment?: string) {
  emit('decide', decision, comment)
}
</script>
