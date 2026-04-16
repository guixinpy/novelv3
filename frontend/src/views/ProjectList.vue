<template>
  <div>
    <h2>项目列表</h2>
    <button @click="showForm = true" style="margin-bottom: 1rem;">新建项目</button>
    <div v-if="showForm" style="border: 1px solid #ccc; padding: 1rem; margin-bottom: 1rem;">
      <input v-model="form.name" placeholder="项目名称" />
      <input v-model="form.genre" placeholder="类型" style="margin-left: 0.5rem;" />
      <button @click="create" style="margin-left: 0.5rem;">创建</button>
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
