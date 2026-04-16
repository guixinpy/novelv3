import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<any[]>([])
  const currentProject = ref<any>(null)
  const setup = ref<any>(null)
  const chapter = ref<any>(null)
  const storyline = ref<any>(null)
  const outline = ref<any>(null)
  const topology = ref<any>(null)

  async function loadProjects() {
    projects.value = await api.listProjects()
  }

  async function createProject(data: any) {
    const p = await api.createProject(data)
    projects.value.unshift(p)
    return p
  }

  async function loadProject(id: string) {
    currentProject.value = await api.getProject(id)
  }

  async function generateSetup(id: string) {
    setup.value = await api.generateSetup(id)
    await loadProject(id)
  }

  async function loadSetup(id: string) {
    setup.value = await api.getSetup(id)
  }

  async function generateChapter(id: string, index: number) {
    chapter.value = await api.generateChapter(id, index)
    await loadProject(id)
  }

  async function loadChapter(id: string, index: number) {
    chapter.value = await api.getChapter(id, index)
  }

  async function generateStoryline(id: string) {
    storyline.value = await api.generateStoryline(id)
    await loadProject(id)
  }

  async function loadStoryline(id: string) {
    storyline.value = await api.getStoryline(id)
  }

  async function generateOutline(id: string) {
    outline.value = await api.generateOutline(id)
    await loadProject(id)
  }

  async function loadOutline(id: string) {
    outline.value = await api.getOutline(id)
  }

  async function loadTopology(id: string) {
    topology.value = await api.getTopology(id)
  }

  return {
    projects, currentProject, setup, chapter, storyline, outline, topology,
    loadProjects, createProject, loadProject,
    generateSetup, loadSetup, generateChapter, loadChapter,
    generateStoryline, loadStoryline, generateOutline, loadOutline, loadTopology,
  }
})
