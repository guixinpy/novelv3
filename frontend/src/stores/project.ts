import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type { RefreshTarget, WorkspaceBootstrap } from '../api/types'
import { useRequestCacheStore } from './requestCache'

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
  const requestCache = useRequestCacheStore()
  const PROJECT_CACHE_TTL_MS = 5 * 60 * 1000
  const VERSION_PAGE_LIMIT = 50
  const projects = ref<any[]>([])
  const currentProject = ref<any>(null)
  const setup = ref<any>(null)
  const chapter = ref<any>(null)
  const storyline = ref<any>(null)
  const outline = ref<any>(null)
  const topology = ref<any>(null)
  const chapters = ref<any[]>([])
  const chaptersTotal = ref(0)
  const chaptersOffset = ref(0)
  const chaptersLimit = ref(0)
  const chaptersHasMore = ref(false)
  const chaptersLatestIndex = ref<number | null>(null)
  const versions = ref<any[]>([])
  const versionsTotal = ref(0)
  const versionsOffset = ref(0)
  const versionsLimit = ref(0)
  const versionsHasMore = ref(false)
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

  function chaptersCacheKey(projectId: string, params?: { offset?: number; limit?: number }) {
    const offset = params?.offset ?? 0
    const limit = params?.limit
    return `project:${projectId}:chapters:${offset}:${limit ?? 'default'}`
  }

  function versionsCacheKey(projectId: string, nodeType?: string, params?: { offset?: number; limit?: number }) {
    const offset = params?.offset ?? 0
    const limit = params?.limit
    return `project:${projectId}:versions:${nodeType || 'all'}:${offset}:${limit ?? 'default'}`
  }

  function normalizeVersionPage(value: any, fallbackOffset: number, fallbackLimit: number) {
    if (Array.isArray(value)) {
      return {
        versions: value,
        total: value.length,
        offset: fallbackOffset,
        limit: fallbackLimit || value.length,
        hasMore: false,
      }
    }
    const items = Array.isArray(value?.versions) ? value.versions : []
    return {
      versions: items,
      total: value?.total ?? items.length,
      offset: value?.offset ?? fallbackOffset,
      limit: value?.limit ?? fallbackLimit,
      hasMore: value?.has_more ?? false,
    }
  }

  function maxLoadedChapterIndex() {
    const indexes = chapters.value
      .map((chapter) => Number(chapter.chapter_index))
      .filter((index) => Number.isFinite(index))
    return indexes.length ? Math.max(...indexes) : null
  }

  function resolveLatestChapterIndex(value: number | null | undefined) {
    if (value === null || value === undefined) return maxLoadedChapterIndex()
    const index = Number(value)
    return Number.isFinite(index) ? index : maxLoadedChapterIndex()
  }

  async function loadProjects() {
    projects.value = await api.listProjects()
  }

  function applyWorkspaceBootstrap(bootstrap: WorkspaceBootstrap) {
    const id = bootstrap.project.id
    if (currentProjectScope.value !== id) {
      resetProjectScopedState(id)
    } else {
      ensureProjectScope(id)
    }
    currentProject.value = bootstrap.project
    setup.value = bootstrap.setup || null
    storyline.value = bootstrap.storyline || null
    outline.value = bootstrap.outline || null
    chapters.value = bootstrap.chapters || []
    chaptersTotal.value = bootstrap.chapters_total ?? chapters.value.length
    chaptersOffset.value = bootstrap.chapters_offset ?? 0
    chaptersLimit.value = bootstrap.chapters_limit ?? chapters.value.length
    chaptersHasMore.value = bootstrap.chapters_has_more ?? false
    chaptersLatestIndex.value = resolveLatestChapterIndex(bootstrap.chapters_latest_index)
    versions.value = bootstrap.versions || []
    versionsTotal.value = bootstrap.versions_total ?? versions.value.length
    versionsOffset.value = bootstrap.versions_offset ?? 0
    versionsLimit.value = bootstrap.versions_limit ?? VERSION_PAGE_LIMIT
    versionsHasMore.value = bootstrap.versions_has_more ?? false
    versionsNodeType.value = undefined
    requestCache.markFresh(`project:${id}:project`)
    if (bootstrap.setup) requestCache.markFresh(`project:${id}:setup`)
    if (bootstrap.storyline && !bootstrap.storyline_partial) requestCache.markFresh(`project:${id}:storyline`)
    if (bootstrap.outline && !bootstrap.outline_partial) requestCache.markFresh(`project:${id}:outline`)
    requestCache.markFresh(chaptersCacheKey(id))
    requestCache.markFresh(versionsCacheKey(id, undefined, { offset: 0, limit: versionsLimit.value || VERSION_PAGE_LIMIT }))
  }

  function resetProjectScopedState(nextProjectId = '') {
    if (currentProjectScope.value) requestCache.invalidate(`project:${currentProjectScope.value}`)
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
    chaptersTotal.value = 0
    chaptersOffset.value = 0
    chaptersLimit.value = 0
    chaptersHasMore.value = false
    chaptersLatestIndex.value = null
    versions.value = []
    versionsTotal.value = 0
    versionsOffset.value = 0
    versionsLimit.value = 0
    versionsHasMore.value = false
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
    const key = `project:${id}:project`
    if (currentProject.value?.id === id && requestCache.isFresh(key, PROJECT_CACHE_TTL_MS)) return
    const snapshot = captureProjectRequest(id, ['project'])
    const nextProject = await requestCache.dedupe(key, () => api.getProject(id))
    if (!isLatestProjectRequest(snapshot, 'project')) return
    currentProject.value = nextProject
  }

  async function generateSetup(id: string) {
    setup.value = await api.generateSetup(id)
    await loadProject(id)
  }

  async function loadSetup(id: string) {
    const key = `project:${id}:setup`
    if (setup.value && requestCache.isFresh(key, PROJECT_CACHE_TTL_MS)) return
    const snapshot = captureProjectRequest(id, ['setup'])
    const nextSetup = await requestCache.dedupe(key, () => api.getSetup(id))
    if (!isLatestProjectRequest(snapshot, 'setup')) return
    setup.value = nextSetup
  }

  async function generateChapter(id: string, index: number) {
    chapter.value = await api.generateChapter(id, index)
    await loadProject(id)
  }

  async function loadChapter(id: string, index: number) {
    const key = `project:${id}:chapter:${index}`
    if (chapter.value?.chapter_index === index && requestCache.isFresh(key, PROJECT_CACHE_TTL_MS)) return
    const snapshot = captureProjectRequest(id, ['chapter'])
    const nextChapter = await requestCache.dedupe(key, () => api.getChapter(id, index))
    if (!isLatestProjectRequest(snapshot, 'chapter')) return
    chapter.value = nextChapter
  }

  async function generateStoryline(id: string) {
    storyline.value = await api.generateStoryline(id)
    await loadProject(id)
  }

  async function loadStoryline(id: string) {
    const key = `project:${id}:storyline`
    if (storyline.value && requestCache.isFresh(key, PROJECT_CACHE_TTL_MS)) return
    const snapshot = captureProjectRequest(id, ['storyline'])
    const nextStoryline = await requestCache.dedupe(key, () => api.getStoryline(id))
    if (!isLatestProjectRequest(snapshot, 'storyline')) return
    storyline.value = nextStoryline
  }

  async function generateOutline(id: string) {
    outline.value = await api.generateOutline(id)
    await loadProject(id)
  }

  async function loadOutline(id: string) {
    const key = `project:${id}:outline`
    if (outline.value && requestCache.isFresh(key, PROJECT_CACHE_TTL_MS)) return
    const snapshot = captureProjectRequest(id, ['outline'])
    const nextOutline = await requestCache.dedupe(key, () => api.getOutline(id))
    if (!isLatestProjectRequest(snapshot, 'outline')) return
    outline.value = nextOutline
  }

  async function loadTopology(id: string) {
    const key = `project:${id}:topology`
    if (topology.value && requestCache.isFresh(key, PROJECT_CACHE_TTL_MS)) return
    const snapshot = captureProjectRequest(id, ['topology'])
    const nextTopology = await requestCache.dedupe(key, () => api.getTopology(id))
    if (!isLatestProjectRequest(snapshot, 'topology')) return
    topology.value = nextTopology
  }

  async function loadChapters(id: string, force = false, params?: { offset?: number; limit?: number }) {
    const offset = params?.offset ?? 0
    const key = chaptersCacheKey(id, params)
    if (!force && requestCache.isFresh(key, PROJECT_CACHE_TTL_MS)) return
    const snapshot = captureProjectRequest(id, ['chapters'])
    const res = await requestCache.dedupe(key, () => api.listChapters(id, params))
    if (!isLatestProjectRequest(snapshot, 'chapters')) return
    chapters.value = res.chapters || []
    chaptersTotal.value = res.total ?? chapters.value.length
    chaptersOffset.value = res.offset ?? offset
    chaptersLimit.value = res.limit ?? chapters.value.length
    chaptersHasMore.value = res.has_more ?? false
    chaptersLatestIndex.value = resolveLatestChapterIndex(res.latest_chapter_index)
  }

  async function loadMoreChapters(id: string) {
    if (!chaptersHasMore.value) return
    const offset = chapters.value.length
    const limit = chaptersLimit.value || 200
    const params = { offset, limit }
    const key = chaptersCacheKey(id, params)
    const snapshot = captureProjectRequest(id, ['chapters'])
    const res = await requestCache.dedupe(key, () => api.listChapters(id, params))
    if (!isLatestProjectRequest(snapshot, 'chapters')) return
    chapters.value = [...chapters.value, ...(res.chapters || [])]
    chaptersTotal.value = res.total ?? chaptersTotal.value
    chaptersOffset.value = res.offset ?? offset
    chaptersLimit.value = res.limit ?? limit
    chaptersHasMore.value = res.has_more ?? false
    chaptersLatestIndex.value = resolveLatestChapterIndex(res.latest_chapter_index)
  }

  async function loadVersions(id: string, nodeType?: string) {
    const params = { offset: 0, limit: VERSION_PAGE_LIMIT }
    const key = versionsCacheKey(id, nodeType, params)
    if (versionsNodeType.value === nodeType && requestCache.isFresh(key, PROJECT_CACHE_TTL_MS)) return
    const snapshot = captureProjectRequest(id, ['versions'])
    const response = await requestCache.dedupe(key, () => api.listVersions(id, nodeType, params))
    if (!isLatestProjectRequest(snapshot, 'versions')) return
    const page = normalizeVersionPage(response, params.offset, params.limit)
    versionsNodeType.value = nodeType
    versions.value = page.versions
    versionsTotal.value = page.total
    versionsOffset.value = page.offset
    versionsLimit.value = page.limit
    versionsHasMore.value = page.hasMore
  }

  async function loadMoreVersions(id: string) {
    if (!versionsHasMore.value) return
    const offset = versions.value.length
    const limit = versionsLimit.value || VERSION_PAGE_LIMIT
    const params = { offset, limit }
    const nodeType = versionsNodeType.value
    const key = versionsCacheKey(id, nodeType, params)
    const snapshot = captureProjectRequest(id, ['versions'])
    const response = await requestCache.dedupe(key, () => api.listVersions(id, nodeType, params))
    if (!isLatestProjectRequest(snapshot, 'versions')) return
    const page = normalizeVersionPage(response, offset, limit)
    versions.value = [...versions.value, ...page.versions]
    versionsTotal.value = page.total
    versionsOffset.value = page.offset
    versionsLimit.value = page.limit
    versionsHasMore.value = page.hasMore
  }

  async function loadPreferences(id: string) {
    const key = `project:${id}:preferences`
    if (preferences.value && requestCache.isFresh(key, PROJECT_CACHE_TTL_MS)) return
    const snapshot = captureProjectRequest(id, ['preferences'])
    const nextPreferences = await requestCache.dedupe(key, () => api.getPreferences(id))
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
          await runSafe(target, () => loadChapters(id, true))
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
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '导出失败' }))
      throw new Error(err.detail || '导出失败')
    }
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `export.${format === 'markdown' ? 'md' : 'txt'}`
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    projects, currentProject, setup, chapter, storyline, outline, topology,
    chapters, chaptersTotal, chaptersOffset, chaptersLimit, chaptersHasMore, chaptersLatestIndex,
    versions, versionsTotal, versionsOffset, versionsLimit, versionsHasMore, preferences, versionsNodeType,
    resetProjectScopedState,
    applyWorkspaceBootstrap,
    loadProjects, createProject, deleteProject, loadProject,
    generateSetup, loadSetup, generateChapter, loadChapter,
    generateStoryline, loadStoryline, generateOutline, loadOutline, loadTopology,
    loadChapters, loadMoreChapters, loadVersions, loadMoreVersions, loadPreferences, updatePreferences, resetPreferences, refreshTargets,
    createVersion, rollbackVersion, exportProject,
  }
})
