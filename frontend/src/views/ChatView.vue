<template>
  <div class="flex flex-col h-[80vh] bg-white rounded-lg shadow">
    <div class="flex-1 overflow-y-auto p-4 space-y-2">
      <ChatMessage v-for="(m, i) in chat.messages" :key="i" :msg="m" />
    </div>
    <div class="border-t border-gray-200 p-3">
      <div class="flex gap-2">
        <input
          v-model="input"
          @keyup.enter="send"
          class="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          placeholder="输入消息..."
        />
        <button
          @click="send"
          class="inline-flex items-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useChatStore } from '../stores/chat'
import ChatMessage from '../components/ChatMessage.vue'

const chat = useChatStore()
const input = ref('')

function send() {
  if (!input.value.trim()) return
  const text = input.value
  input.value = ''
  chat.sendText(text)
}
</script>
