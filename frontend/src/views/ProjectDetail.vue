<template>
  <div v-if="store.currentProject">
    <h2>{{ store.currentProject.name }}</h2>
    <p>状态：{{ store.currentProject.status }} | 字数：{{ store.currentProject.current_word_count }}</p>

    <div style="margin-top: 1rem;">
      <h3>设定</h3>
      <button @click="genSetup">生成设定</button>
      <pre v-if="store.setup" style="background: #f5f5f5; padding: 1rem; overflow: auto;">{{ JSON.stringify(store.setup, null, 2) }}</pre>
    </div>

    <div style="margin-top: 1rem;">
      <h3>第 1 章</h3>
      <button @click="genChapter">生成第 1 章</button>
      <div v-if="store.chapter">
        <h4>{{ store.chapter.title }}</h4>
        <div style="white-space: pre-wrap;">{{ store.chapter.content }}</div>
      </div>
    </div>
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
