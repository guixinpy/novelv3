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
}

export function createProjectWorkspaceState(): ProjectWorkspaceState {
  return {
    activeProjectId: '',
    activeWorkspace: 'hermes',
    dirtyTargets: new Set<RefreshTarget>(),
    lastWorkspaceRouteByProject: {},
    lastManuscriptChapterByProject: {},
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

export const useProjectWorkspaceStore = defineStore('projectWorkspace', () => {
  const state = reactive(createProjectWorkspaceState())

  return {
    ...toRefs(state),
    enterProject: (projectId: string) => enterProject(state, projectId),
    markDirty: (targets: RefreshTarget[]) => markDirty(state, targets),
    consumeDirty: (target: RefreshTarget) => consumeDirty(state, target),
    rememberWorkspaceRoute: (projectId: string, route: string) => rememberWorkspaceRoute(state, projectId, route),
    rememberManuscriptChapter: (projectId: string, chapterIndex: number) => rememberManuscriptChapter(state, projectId, chapterIndex),
  }
})
