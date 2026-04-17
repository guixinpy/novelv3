<template>
  <div v-if="project.currentProject" class="flex gap-4 h-[calc(100vh-5rem)]">
    <div class="w-48 flex-shrink-0 flex flex-col gap-4">
      <WorkspaceTabs :active="activeTab" :tabs="tabs" @select="activeTab = $event" />
      <div class="flex-1 flex flex-col bg-white rounded-lg shadow overflow-hidden min-h-0">
        <div class="flex-1 overflow-y-auto p-3 space-y-2" ref="msgContainer">
          <ChatMessage
            v-for="(m, i) in chat.messages" :key="i" :msg="m"
            :is-latest="i === chat.messages.length - 1" :loading="chat.loading"
            @decide="onDecide"
          />
          <div v-if="chat.loading" class="flex justify-start">
            <div class="bg-gray-100 rounded-lg px-3 py-1.5 text-xs text-gray-500 animate-pulse">思考中...</div>
          </div>
        </div>
        <QuickActions :diagnosis="chat.diagnosis" :disabled="chat.loading || !!chat.pendingAction" @action="onQuickAction" />
        <div class="border-t border-gray-200 p-2">
          <div class="flex gap-1">
            <input v-model="input" @keyup.enter="send" :disabled="chat.loading"
              class="flex-1 border border-gray-300 rounded-md px-2 py-1 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:bg-gray-50"
              placeholder="和墨舟聊聊..." />
            <button @click="send" :disabled="chat.loading || !input.trim()"
              class="rounded-md bg-indigo-600 px-2 py-1 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50">发送</button>
          </div>
        </div>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto">
      <OverviewTab v-if="activeTab === 'overview'" :project="project.currentProject"
        :completed="chat.diagnosis?.completed_items || []" :missing="chat.diagnosis?.missing_items || []"
        @export="onExport" />
      <SetupTab v-else-if="activeTab === 'setup'" :setup="project.setup" />
      <StorylineTab v-else-if="activeTab === 'storyline'" :storyline="project.storyline" />
      <OutlineTab v-else-if="activeTab === 'outline'" :outline="project.outline" />
      <ContentTab v-else-if="activeTab === 'content'" :chapters="project.chapters" :selected-chapter="project.chapter"
        :project-id="pid" @select-chapter="loadChapter" />
      <TopologyTab v-else-if="activeTab === 'topology'" :topology="project.topology" />
      <VersionsTab v-else-if="activeTab === 'versions'" :versions="project.versions" :project-id="pid"
        @filter="onFilterVersions" @rollback="onRollback" @delete-version="onDeleteVersion" />
      <PreferencesTab v-else-if="activeTab === 'preferences'" :project-id="pid" />
    </div>
  </div>
  <div v-else class="text-center text-gray-500 py-12">加载中...</div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { useChatStore } from '../stores/chat'
import WorkspaceTabs from '../components/WorkspaceTabs.vue'
import ChatMessage from '../components/ChatMessage.vue'
import QuickActions from '../components/QuickActions.vue'
import OverviewTab from '../components/tabs/OverviewTab.vue'
import SetupTab from '../components/tabs/SetupTab.vue'
import StorylineTab from '../components/tabs/StorylineTab.vue'
import OutlineTab from '../components/tabs/OutlineTab.vue'
import ContentTab from '../components/tabs/ContentTab.vue'
import VersionsTab from '../components/tabs/VersionsTab.vue'
import PreferencesTab from '../components/tabs/PreferencesTab.vue'
import TopologyTab from '../components/tabs/TopologyTab.vue'

const route = useRoute()
const project = useProjectStore()
const chat = useChatStore()
const pid = route.params.id as string
const input = ref('')
const activeTab = ref('overview')
const msgContainer = ref<HTMLElement>()

const tabs = [
  { id: 'overview', label: '概览' },
  { id: 'setup', label: '设定' },
  { id: 'storyline', label: '故事线' },
  { id: 'outline', label: '大纲' },
  { id: 'content', label: '正文' },
  { id: 'topology', label: '拓扑图' },
  { id: 'versions', label: '版本历史' },
  { id: 'preferences', label: '偏好设置' },
]

onMounted(async () => {
  await project.loadProject(pid)
  chat.init(pid)
  await loadAllData()
})

watch(() => chat.messages.length, () => {
  nextTick(() => { if (msgContainer.value) msgContainer.value.scrollTop = msgContainer.value.scrollHeight })
})

async function loadAllData() {
  await project.loadSetup(pid).catch(() => {})
  await project.loadStoryline(pid).catch(() => {})
  await project.loadOutline(pid).catch(() => {})
  await project.loadChapters(pid).catch(() => {})
  await project.loadVersions(pid).catch(() => {})
  await project.loadTopology(pid).catch(() => {})
}

async function send() {
  if (!input.value.trim() || chat.loading) return
  const text = input.value
  input.value = ''
  await chat.sendText(text)
  await loadAllData()
}

async function onQuickAction(type: string) {
  await chat.sendButtonAction(type)
}

async function onDecide(decision: string, comment?: string) {
  await chat.resolveAction(decision as any, comment)
  await loadAllData()
}

async function loadChapter(index: number) {
  await project.loadChapter(pid, index)
}

async function onExport(format: string) {
  await project.exportProject(pid, format)
}

async function onFilterVersions(type: string) {
  await project.loadVersions(pid, type || undefined)
}

async function onRollback(versionId: string) {
  await project.rollbackVersion(pid, versionId)
  await loadAllData()
}

async function onDeleteVersion(versionId: string) {
  const { api } = await import('../api/client')
  await api.deleteVersion(pid, versionId)
  await project.loadVersions(pid)
}
</script>
