import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  pending_action?: any
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([
    { role: 'assistant', content: '你好，我是墨舟。请告诉我你想写什么类型的小说？' },
  ])

  function sendUserMessage(text: string) {
    messages.value.push({ role: 'user', content: text })
  }

  function appendAssistantMessage(text: string, pending_action?: any) {
    messages.value.push({ role: 'assistant', content: text, pending_action })
  }

  function clear() {
    messages.value = []
  }

  return { messages, sendUserMessage, appendAssistantMessage, clear }
})
