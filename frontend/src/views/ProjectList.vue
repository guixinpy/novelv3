<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-semibold text-gray-900">项目列表</h2>
      <button
        @click="showForm = true"
        class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
      >
        新建项目
      </button>
    </div>

    <div v-if="showForm" class="bg-white rounded-lg shadow p-4 mb-4">
      <div class="flex flex-col sm:flex-row gap-3">
        <input
          v-model="form.name"
          placeholder="项目名称"
          class="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <input
          v-model="form.genre"
          placeholder="类型"
          class="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <div class="flex gap-2">
          <button
            @click="create"
            class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            创建
          </button>
          <button
            @click="showForm = false"
            class="inline-flex items-center rounded-md bg-white border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            取消
          </button>
        </div>
      </div>
    </div>

    <div v-if="store.projects.length === 0" class="text-center text-gray-500 py-12">
      暂无项目，点击上方按钮创建第一个项目
    </div>

    <ProjectCard v-for="p in store.projects" :key="p.id" :project="p" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useProjectStore } from '../stores/project'
import ProjectCard from '../components/ProjectCard.vue'

const store = useProjectStore()
const showForm = ref(false)
const form = ref({ name: '', genre: '' })

onMounted(() => store.loadProjects())

async function create() {
  await store.createProject(form.value)
  showForm.value = false
  form.value = { name: '', genre: '' }
}
</script>
