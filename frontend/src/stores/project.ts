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
  const versionsNodeType = ref<string | undefined>(undefined)
  const currentProjectScope = ref<string>('')
  const scopeVersion = ref(0)

  function captureProjectSnapshot(requestProjectId: string) {
    if (!currentProjectScope.value) {
      currentProjectScope.value = requestProjectId
    }
    return {
      requestProjectId,
      versionSnapshot: scopeVersion.value,
    }
  }

  function isActiveProjectSnapshot(requestProjectId: string, versionSnapshot: number) {
    return currentProjectScope.value === requestProjectId && scopeVersion.value === versionSnapshot
  }

  async function loadProjects() {
    projects.value = await api.listProjects()
  }

  function resetProjectScopedState(nextProjectId = '') {
    scopeVersion.value += 1
    currentProjectScope.value = nextProjectId
    currentProject.value = null
    setup.value = null
    chapter.value = null
    storyline.value = null
    outline.value = null
    topology.value = null
    chapters.value = []
    versions.value = []
    preferences.value = null
    versionsNodeType.value = undefined
  }

  async function createProject(data: any) {
    const p = await api.createProject(data)
    projects.value.unshift(p)
    return p
  }

  async function loadProject(id: string) {
    const { requestProjectId, versionSnapshot } = captureProjectSnapshot(id)
    const nextProject = await api.getProject(id)
    if (!isActiveProjectSnapshot(requestProjectId, versionSnapshot)) return
    currentProject.value = nextProject
  }

  async function generateSetup(id: string) {
    setup.value = await api.generateSetup(id)
    await loadProject(id)
  }

  async function loadSetup(id: string) {
    const { requestProjectId, versionSnapshot } = captureProjectSnapshot(id)
    const nextSetup = await api.getSetup(id)
    if (!isActiveProjectSnapshot(requestProjectId, versionSnapshot)) return
    setup.value = nextSetup
  }

  async function generateChapter(id: string, index: number) {
    chapter.value = await api.generateChapter(id, index)
    await loadProject(id)
  }

  async function loadChapter(id: string, index: number) {
    const { requestProjectId, versionSnapshot } = captureProjectSnapshot(id)
    const nextChapter = await api.getChapter(id, index)
    if (!isActiveProjectSnapshot(requestProjectId, versionSnapshot)) return
    chapter.value = nextChapter
  }

  async function generateStoryline(id: string) {
    storyline.value = await api.generateStoryline(id)
    await loadProject(id)
  }

  async function loadStoryline(id: string) {
    const { requestProjectId, versionSnapshot } = captureProjectSnapshot(id)
    const nextStoryline = await api.getStoryline(id)
    if (!isActiveProjectSnapshot(requestProjectId, versionSnapshot)) return
    storyline.value = nextStoryline
  }

  async function generateOutline(id: string) {
    outline.value = await api.generateOutline(id)
    await loadProject(id)
  }

  async function loadOutline(id: string) {
    const { requestProjectId, versionSnapshot } = captureProjectSnapshot(id)
    const nextOutline = await api.getOutline(id)
    if (!isActiveProjectSnapshot(requestProjectId, versionSnapshot)) return
    outline.value = nextOutline
  }

  async function loadTopology(id: string) {
    const { requestProjectId, versionSnapshot } = captureProjectSnapshot(id)
    const nextTopology = await api.getTopology(id)
    if (!isActiveProjectSnapshot(requestProjectId, versionSnapshot)) return
    topology.value = nextTopology
  }

  async function loadChapters(id: string) {
    const { requestProjectId, versionSnapshot } = captureProjectSnapshot(id)
    const res = await api.listChapters(id)
    if (!isActiveProjectSnapshot(requestProjectId, versionSnapshot)) return
    chapters.value = res.chapters || []
  }

  async function loadVersions(id: string, nodeType?: string) {
    const { requestProjectId, versionSnapshot } = captureProjectSnapshot(id)
    const nextVersions = await api.listVersions(id, nodeType)
    if (!isActiveProjectSnapshot(requestProjectId, versionSnapshot)) return
    versionsNodeType.value = nodeType
    versions.value = nextVersions
  }

  async function loadPreferences(id: string) {
    const { requestProjectId, versionSnapshot } = captureProjectSnapshot(id)
    const nextPreferences = await api.getPreferences(id)
    if (!isActiveProjectSnapshot(requestProjectId, versionSnapshot)) return
    preferences.value = nextPreferences
  }

  async function updatePreferences(id: string, data: any) {
    preferences.value = await api.updatePreferences(id, data)
    return preferences.value
  }

  async function resetPreferences(id: string) {
    preferences.value = await api.resetPreferences(id)
    return preferences.value
  }

  async function refreshTargets(id: string, targets: RefreshTarget[]): Promise<RefreshTarget[]> {
    const uniqueTargets = [...new Set(targets)]
    const successTargets: RefreshTarget[] = []

    async function runSafe(target: RefreshTarget, task: () => Promise<unknown>) {
      try {
        await task()
        successTargets.push(target)
      } catch {
        // Keep refreshing remaining targets even if one target fails.
      }
    }

    for (const target of uniqueTargets) {
      switch (target) {
        case 'setup':
          await runSafe(target, () => loadSetup(id))
          break
        case 'project':
          await runSafe(target, () => loadProject(id))
          break
        case 'storyline':
          await runSafe(target, () => loadStoryline(id))
          break
        case 'outline':
          await runSafe(target, () => loadOutline(id))
          break
        case 'content':
          await runSafe(target, () => loadChapters(id))
          break
        case 'topology':
          await runSafe(target, () => loadTopology(id))
          break
        case 'versions':
          await runSafe(target, () => loadVersions(id, versionsNodeType.value))
          break
        case 'preferences':
          await runSafe(target, () => loadPreferences(id))
          break
        default:
          break
      }
    }

    return successTargets
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
    projects, currentProject, setup, chapter, storyline, outline, topology, chapters, versions, preferences, versionsNodeType,
    resetProjectScopedState,
    loadProjects, createProject, loadProject,
    generateSetup, loadSetup, generateChapter, loadChapter,
    generateStoryline, loadStoryline, generateOutline, loadOutline, loadTopology,
    loadChapters, loadVersions, loadPreferences, updatePreferences, resetPreferences, refreshTargets,
    createVersion, rollbackVersion, exportProject,
  }
})
