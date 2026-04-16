<template>
  <div
    class="flex"
    :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
  >
    <div
      class="max-w-[80%] rounded-lg px-4 py-2"
      :class="msg.role === 'user' ? 'bg-indigo-100 text-gray-900' : 'bg-gray-100 text-gray-900'"
    >
      <div class="text-xs text-gray-500 mb-1">
        {{ msg.role === 'user' ? '我' : '墨舟' }}
      </div>
      <div class="text-sm whitespace-pre-wrap">{{ msg.content }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ msg: any }>()
</script>
