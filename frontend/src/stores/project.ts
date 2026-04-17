import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type { RefreshTarget } from '../api/types'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<any[]>([])
  const currentProject = ref<any>(null)
  const setup = ref<any>(null)
  const chapter = ref<any>(null)
  const storyline = ref<any>(null)
  const outline = ref<any>(null)
  const topology = ref<any>(null)
  const chapters = ref<any[]>([])
  const versions = ref<any[]>([])
  const preferences = ref<any>(null)

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

  async function loadChapters(id: string) {
    const res = await api.listChapters(id)
    chapters.value = res.chapters || []
  }

  async function loadVersions(id: string, nodeType?: string) {
    versions.value = await api.listVersions(id, nodeType)
  }

  async function loadPreferences(id: string) {
    preferences.value = await api.getPreferences(id)
  }

  async function updatePreferences(id: string, data: any) {
    preferences.value = await api.updatePreferences(id, data)
    return preferences.value
  }

  async function resetPreferences(id: string) {
    preferences.value = await api.resetPreferences(id)
    return preferences.value
  }

  async function refreshTargets(id: string, targets: RefreshTarget[]) {
    const jobs: Promise<unknown>[] = []
    const uniqueTargets = [...new Set(targets)]
    for (const target of uniqueTargets) {
      switch (target) {
        case 'setup':
          jobs.push(loadSetup(id))
          break
        case 'storyline':
          jobs.push(loadStoryline(id))
          break
        case 'outline':
          jobs.push(loadOutline(id))
          break
        case 'content':
          jobs.push(loadChapters(id))
          break
        case 'versions':
          jobs.push(loadVersions(id))
          break
        default:
          break
      }
    }
    await Promise.all(jobs)
  }

  async function createVersion(id: string, data: any) {
    return await api.createVersion(id, data)
  }

  async function rollbackVersion(id: string, versionId: string) {
    return await api.rollbackVersion(id, versionId)
  }

  async function exportProject(id: string, format: string) {
    const res = await api.exportProject(id, { format, include_setup: true, include_outline: true })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `export.${format === 'markdown' ? 'md' : 'txt'}`
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    projects, currentProject, setup, chapter, storyline, outline, topology, chapters, versions, preferences,
    loadProjects, createProject, loadProject,
    generateSetup, loadSetup, generateChapter, loadChapter,
    generateStoryline, loadStoryline, generateOutline, loadOutline, loadTopology,
    loadChapters, loadVersions, loadPreferences, updatePreferences, resetPreferences, refreshTargets,
    createVersion, rollbackVersion, exportProject,
  }
})
