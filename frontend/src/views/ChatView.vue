<template>
  <div style="display: flex; flex-direction: column; height: 80vh;">
    <div style="flex: 1; overflow-y: auto; border: 1px solid #ddd; padding: 1rem;">
      <ChatMessage v-for="(m, i) in chat.messages" :key="i" :msg="m" />
    </div>
    <div style="display: flex; margin-top: 0.5rem;">
      <input v-model="input" @keyup.enter="send" style="flex: 1; padding: 0.5rem;" placeholder="输入消息..." />
      <button @click="send" style="padding: 0.5rem 1rem;">发送</button>
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
  chat.sendUserMessage(input.value)
  // Phase 1: echo a simple assistant reply
  setTimeout(() => {
    chat.appendAssistantMessage('收到。你可以在项目详情页中生成设定和章节。')
  }, 300)
  input.value = ''
}
</script>
