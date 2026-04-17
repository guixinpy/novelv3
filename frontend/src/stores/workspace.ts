import { defineStore } from 'pinia'
import { reactive, toRefs } from 'vue'
import type { ActiveAction, UiHint } from '../api/types'

export type WorkspaceMode = 'auto' | 'locked'
export type WorkspaceSource = 'ai' | 'user'
export type WorkspacePanel = string

export interface WorkspaceState {
  mode: WorkspaceMode
  panel: WorkspacePanel
  source: WorkspaceSource
  lockedPanel: WorkspacePanel | null
  dialogState: string
  activeAction: ActiveAction | null
}

export function createWorkspaceState(): WorkspaceState {
  return {
    mode: 'auto',
    panel: 'setup',
    source: 'user',
    lockedPanel: null,
    dialogState: 'IDLE',
    activeAction: null,
  }
}

export function applyUserPanel(state: WorkspaceState, panel: WorkspacePanel) {
  state.mode = 'locked'
  state.panel = panel
  state.lockedPanel = panel
  state.source = 'user'
}

function isCompletedStatus(status: string) {
  return status === 'completed' || status === 'success'
}

export function settleUiAction(state: WorkspaceState, action: ActiveAction) {
  state.activeAction = action
  if (state.mode === 'locked' && isCompletedStatus(action.status) && state.lockedPanel) {
    state.panel = state.lockedPanel
    state.source = 'user'
    return
  }

  if (state.mode === 'auto' && action.target_panel) {
    state.panel = action.target_panel
    state.source = 'ai'
  }
}

export function applyUiHint(state: WorkspaceState, uiHint: UiHint | null | undefined) {
  if (!uiHint) return
  state.dialogState = uiHint.dialog_state
  state.activeAction = uiHint.active_action

  const action = uiHint.active_action
  if (isCompletedStatus(action.status)) {
    settleUiAction(state, action)
    return
  }

  if (state.mode === 'auto' && action.target_panel) {
    state.panel = action.target_panel
    state.source = 'ai'
  }
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const state = reactive(createWorkspaceState())

  function setAutoMode() {
    state.mode = 'auto'
    state.lockedPanel = null
  }

  return {
    ...toRefs(state),
    setAutoMode,
    applyUserPanel: (panel: WorkspacePanel) => applyUserPanel(state, panel),
    applyUiHint: (uiHint: UiHint | null | undefined) => applyUiHint(state, uiHint),
    settleUiAction: (action: ActiveAction) => settleUiAction(state, action),
  }
})
