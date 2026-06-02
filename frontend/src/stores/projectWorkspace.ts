import { defineStore } from 'pinia'
import { reactive, toRefs } from 'vue'
import type { RefreshTarget } from '../api/types'
import type { Workspace } from './ui'

export interface ProjectWorkspaceState {
  activeProjectId: string
  activeWorkspace: Workspace
  dirtyTargets: Set<RefreshTarget>
  lastWorkspaceRouteByProject: Record<string, string>
  lastManuscriptChapterByProject: Record<string, number>
  memoryTreeHistoryByProject: Record<string, MemoryTreeNavigationHistoryItem[]>
}

export interface MemoryTreeNavigationHistoryItem {
  key: string
  label: string
  runId?: string
}

export function createProjectWorkspaceState(): ProjectWorkspaceState {
  return {
    activeProjectId: '',
    activeWorkspace: 'hermes',
    dirtyTargets: new Set<RefreshTarget>(),
    lastWorkspaceRouteByProject: {},
    lastManuscriptChapterByProject: {},
    memoryTreeHistoryByProject: {},
  }
}

export function enterProject(state: ProjectWorkspaceState, projectId: string) {
  const changed = state.activeProjectId !== projectId
  if (changed) {
    state.activeProjectId = projectId
    state.dirtyTargets.clear()
  }
  return changed
}

export function markDirty(state: ProjectWorkspaceState, targets: RefreshTarget[]) {
  for (const target of targets) state.dirtyTargets.add(target)
}

export function consumeDirty(state: ProjectWorkspaceState, target: RefreshTarget) {
  const dirty = state.dirtyTargets.has(target)
  state.dirtyTargets.delete(target)
  return dirty
}

export function rememberWorkspaceRoute(state: ProjectWorkspaceState, projectId: string, route: string) {
  state.lastWorkspaceRouteByProject[projectId] = route
}

export function rememberManuscriptChapter(state: ProjectWorkspaceState, projectId: string, chapterIndex: number) {
  state.lastManuscriptChapterByProject[projectId] = chapterIndex
}

export function memoryTreeHistoryForProject(state: ProjectWorkspaceState, projectId: string) {
  return state.memoryTreeHistoryByProject[projectId] || []
}

export function appendMemoryTreeHistory(
  state: ProjectWorkspaceState,
  projectId: string,
  item: MemoryTreeNavigationHistoryItem,
  limit = 8,
) {
  const targetProjectId = cleanMemoryTreeHistoryText(projectId)
  const label = safeMemoryTreeHistoryLabel(item.label)
  if (!targetProjectId || !label) return
  const key = cleanMemoryTreeHistoryText(item.key) || `memory-tree-history:${Date.now()}`
  const runId = cleanMemoryTreeHistoryText(item.runId)
  state.memoryTreeHistoryByProject[targetProjectId] = [
    ...memoryTreeHistoryForProject(state, targetProjectId),
    runId ? { key, label, runId } : { key, label },
  ].slice(-Math.max(1, limit))
}

export function clearMemoryTreeHistory(state: ProjectWorkspaceState, projectId: string) {
  const targetProjectId = cleanMemoryTreeHistoryText(projectId)
  if (!targetProjectId) return
  delete state.memoryTreeHistoryByProject[targetProjectId]
}

function safeMemoryTreeHistoryLabel(label: unknown) {
  const value = cleanMemoryTreeHistoryText(label)
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_-]+/.test(value)) return ''
  if (/source_refs|source_id|approval_contract|approval:|chapter-content-\d+|memory-\d+/i.test(value)) return ''
  return value.slice(0, 64)
}

function cleanMemoryTreeHistoryText(value: unknown) {
  return typeof value === 'string' ? value.trim().replace(/\s+/g, ' ') : ''
}

export const useProjectWorkspaceStore = defineStore('projectWorkspace', () => {
  const state = reactive(createProjectWorkspaceState())

  return {
    ...toRefs(state),
    enterProject: (projectId: string) => enterProject(state, projectId),
    markDirty: (targets: RefreshTarget[]) => markDirty(state, targets),
    consumeDirty: (target: RefreshTarget) => consumeDirty(state, target),
    rememberWorkspaceRoute: (projectId: string, route: string) => rememberWorkspaceRoute(state, projectId, route),
    rememberManuscriptChapter: (projectId: string, chapterIndex: number) => rememberManuscriptChapter(state, projectId, chapterIndex),
    memoryTreeHistoryForProject: (projectId: string) => memoryTreeHistoryForProject(state, projectId),
    appendMemoryTreeHistory: (projectId: string, item: MemoryTreeNavigationHistoryItem, limit?: number) => (
      appendMemoryTreeHistory(state, projectId, item, limit)
    ),
    clearMemoryTreeHistory: (projectId: string) => clearMemoryTreeHistory(state, projectId),
  }
})
