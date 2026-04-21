import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type { RefreshTarget } from '../api/types'

type ProjectRequestLane =
  | 'project'
  | 'setup'
  | 'chapter'
  | 'storyline'
  | 'outline'
  | 'topology'
  | 'chapters'
  | 'versions'
  | 'preferences'

interface ProjectRequestSnapshot {
  projectId: string
  version: number
  requestId: number
}

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
  const nextRequestId = ref(0)
  const latestLaneRequest = ref<Record<ProjectRequestLane, number>>({
    project: 0,
    setup: 0,
    chapter: 0,
    storyline: 0,
    outline: 0,
    topology: 0,
    chapters: 0,
    versions: 0,
    preferences: 0,
  })

  function ensureProjectScope(projectId: string) {
    if (!currentProjectScope.value) {
      currentProjectScope.value = projectId
      return
    }
    if (currentProjectScope.value !== projectId) {
      resetProjectScopedState(projectId)
    }
  }

  function captureProjectRequest(projectId: string, lanes: ProjectRequestLane[]): ProjectRequestSnapshot {
    ensureProjectScope(projectId)
    const requestId = nextRequestId.value + 1
    nextRequestId.value = requestId
    for (const lane of lanes) {
      latestLaneRequest.value[lane] = requestId
    }
    return {
      projectId,
      version: scopeVersion.value,
      requestId,
    }
  }

  function isLatestProjectRequest(snapshot: ProjectRequestSnapshot, lane: ProjectRequestLane) {
    return currentProjectScope.value === snapshot.projectId
      && scopeVersion.value === snapshot.version
      && latestLaneRequest.value[lane] === snapshot.requestId
  }

  async function loadProjects() {
    projects.value = await api.listProjects()
  }

  function resetProjectScopedState(nextProjectId = '') {
    scopeVersion.value += 1
    currentProjectScope.value = nextProjectId
    latestLaneRequest.value = {
      project: 0,
      setup: 0,
      chapter: 0,
      storyline: 0,
      outline: 0,
      topology: 0,
      chapters: 0,
      versions: 0,
      preferences: 0,
    }
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

  async function deleteProject(id: string) {
    await api.deleteProject(id)
    projects.value = projects.value.filter((project) => project.id !== id)
    if (currentProject.value?.id === id) {
      resetProjectScopedState()
    }
  }

  async function loadProject(id: string) {
    const snapshot = captureProjectRequest(id, ['project'])
    const nextProject = await api.getProject(id)
    if (!isLatestProjectRequest(snapshot, 'project')) return
    currentProject.value = nextProject
  }

  async function generateSetup(id: string) {
    setup.value = await api.generateSetup(id)
    await loadProject(id)
  }

  async function loadSetup(id: string) {
    const snapshot = captureProjectRequest(id, ['setup'])
    const nextSetup = await api.getSetup(id)
    if (!isLatestProjectRequest(snapshot, 'setup')) return
    setup.value = nextSetup
  }

  async function generateChapter(id: string, index: number) {
    chapter.value = await api.generateChapter(id, index)
    await loadProject(id)
  }

  async function loadChapter(id: string, index: number) {
    const snapshot = captureProjectRequest(id, ['chapter'])
    const nextChapter = await api.getChapter(id, index)
    if (!isLatestProjectRequest(snapshot, 'chapter')) return
    chapter.value = nextChapter
  }

  async function generateStoryline(id: string) {
    storyline.value = await api.generateStoryline(id)
    await loadProject(id)
  }

  async function loadStoryline(id: string) {
    const snapshot = captureProjectRequest(id, ['storyline'])
    const nextStoryline = await api.getStoryline(id)
    if (!isLatestProjectRequest(snapshot, 'storyline')) return
    storyline.value = nextStoryline
  }

  async function generateOutline(id: string) {
    outline.value = await api.generateOutline(id)
    await loadProject(id)
  }

  async function loadOutline(id: string) {
    const snapshot = captureProjectRequest(id, ['outline'])
    const nextOutline = await api.getOutline(id)
    if (!isLatestProjectRequest(snapshot, 'outline')) return
    outline.value = nextOutline
  }

  async function loadTopology(id: string) {
    const snapshot = captureProjectRequest(id, ['topology'])
    const nextTopology = await api.getTopology(id)
    if (!isLatestProjectRequest(snapshot, 'topology')) return
    topology.value = nextTopology
  }

  async function loadChapters(id: string) {
    const snapshot = captureProjectRequest(id, ['chapters'])
    const res = await api.listChapters(id)
    if (!isLatestProjectRequest(snapshot, 'chapters')) return
    chapters.value = res.chapters || []
  }

  async function loadVersions(id: string, nodeType?: string) {
    const snapshot = captureProjectRequest(id, ['versions'])
    const nextVersions = await api.listVersions(id, nodeType)
    if (!isLatestProjectRequest(snapshot, 'versions')) return
    versionsNodeType.value = nodeType
    versions.value = nextVersions
  }

  async function loadPreferences(id: string) {
    const snapshot = captureProjectRequest(id, ['preferences'])
    const nextPreferences = await api.getPreferences(id)
    if (!isLatestProjectRequest(snapshot, 'preferences')) return
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
    loadProjects, createProject, deleteProject, loadProject,
    generateSetup, loadSetup, generateChapter, loadChapter,
    generateStoryline, loadStoryline, generateOutline, loadOutline, loadTopology,
    loadChapters, loadVersions, loadPreferences, updatePreferences, resetPreferences, refreshTargets,
    createVersion, rollbackVersion, exportProject,
  }
})
