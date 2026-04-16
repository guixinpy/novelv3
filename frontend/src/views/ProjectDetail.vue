<template>
  <div v-if="store.currentProject">
    <div class="bg-white rounded-lg shadow p-4 mb-4">
      <h2 class="text-xl font-semibold text-gray-900">{{ store.currentProject.name }}</h2>
      <p class="text-sm text-gray-600 mt-1">
        状态：{{ store.currentProject.status }} | 字数：{{ store.currentProject.current_word_count }}
      </p>
    </div>

    <div class="bg-white rounded-lg shadow p-4 mb-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-lg font-medium text-gray-900">设定</h3>
        <button
          @click="genSetup"
          class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          生成设定
        </button>
      </div>
      <pre
        v-if="store.setup"
        class="bg-gray-50 rounded-md p-3 overflow-auto text-sm text-gray-800"
      >{{ JSON.stringify(store.setup, null, 2) }}</pre>
      <p v-else class="text-gray-500 text-sm">暂无设定，点击上方按钮生成。</p>
    </div>

    <div class="bg-white rounded-lg shadow p-4">
      <div class="flex items-center justify-between mb-3">
        <h3 class="text-lg font-medium text-gray-900">第 1 章</h3>
        <button
          @click="genChapter"
          class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          生成第 1 章
        </button>
      </div>
      <div v-if="store.chapter">
        <h4 class="text-base font-semibold text-gray-900 mb-2">{{ store.chapter.title }}</h4>
        <div class="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap">
          {{ store.chapter.content }}
        </div>
      </div>
      <p v-else class="text-gray-500 text-sm">暂无章节内容，点击上方按钮生成。</p>
    </div>
  </div>

  <div v-else class="text-center text-gray-500 py-12">
    加载中...
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '../stores/project'

const route = useRoute()
const store = useProjectStore()
const pid = route.params.id as string

onMounted(async () => {
  await store.loadProject(pid)
  if (store.currentProject?.status !== 'draft') {
    await store.loadSetup(pid).catch(() => {})
    await store.loadChapter(pid, 1).catch(() => {})
  }
})

async function genSetup() {
  await store.generateSetup(pid)
}

async function genChapter() {
  await store.generateChapter(pid, 1)
}
</script>
