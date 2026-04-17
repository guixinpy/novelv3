<template>
  <div v-if="project.currentProject" class="flex gap-4 h-[calc(100vh-5rem)]">
    <div class="w-72 flex-shrink-0 overflow-y-auto">
      <ProjectSidebar
        :project="project.currentProject"
        :setup="project.setup"
        :storyline="project.storyline"
        :outline="project.outline"
        :completed-items="chat.diagnosis?.completed_items || []"
        :missing-items="chat.diagnosis?.missing_items || []"
      />
    </div>

    <div class="flex-1 flex flex-col bg-white rounded-lg shadow overflow-hidden">
      <div class="flex-1 overflow-y-auto p-4 space-y-3" ref="msgContainer">
        <ChatMessage
          v-for="(m, i) in chat.messages"
          :key="i"
          :msg="m"
          :is-latest="i === chat.messages.length - 1"
          :loading="chat.loading"
          @decide="onDecide"
        />
        <div v-if="chat.loading" class="flex justify-start">
          <div class="bg-gray-100 rounded-lg px-4 py-2 text-sm text-gray-500 animate-pulse">
            墨舟正在思考...
          </div>
        </div>
      </div>

      <QuickActions
        :diagnosis="chat.diagnosis"
        :disabled="chat.loading || !!chat.pendingAction"
        @action="onQuickAction"
      />

      <div class="border-t border-gray-200 p-3">
        <div class="flex gap-2">
          <input
            v-model="input"
            @keyup.enter="send"
            :disabled="chat.loading"
            class="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-50"
            placeholder="和墨舟聊聊你的创作想法..."
          />
          <button
            @click="send"
            :disabled="chat.loading || !input.trim()"
            class="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  </div>

  <div v-else class="text-center text-gray-500 py-12">加载中...</div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { useChatStore } from '../stores/chat'
import ChatMessage from '../components/ChatMessage.vue'
import QuickActions from '../components/QuickActions.vue'
import ProjectSidebar from '../components/ProjectSidebar.vue'

const route = useRoute()
const project = useProjectStore()
const chat = useChatStore()
const pid = route.params.id as string
const input = ref('')
const msgContainer = ref<HTMLElement>()

onMounted(async () => {
  await project.loadProject(pid)
  chat.init(pid)
  if (project.currentProject?.status !== 'draft') {
    await project.loadSetup(pid).catch(() => {})
    await project.loadStoryline(pid).catch(() => {})
    await project.loadOutline(pid).catch(() => {})
  }
})

watch(() => chat.messages.length, () => {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
})

async function send() {
  if (!input.value.trim() || chat.loading) return
  const text = input.value
  input.value = ''
  await chat.sendText(text)
  await refreshProjectData()
}

async function onQuickAction(type: string) {
  await chat.sendButtonAction(type)
}

async function onDecide(decision: string, comment?: string) {
  await chat.resolveAction(decision as any, comment)
  await refreshProjectData()
}

async function refreshProjectData() {
  await project.loadProject(pid)
  await project.loadSetup(pid).catch(() => {})
  await project.loadStoryline(pid).catch(() => {})
  await project.loadOutline(pid).catch(() => {})
}
</script>
