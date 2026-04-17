import { defineStore } from 'pinia'
import { reactive, toRefs } from 'vue'
import type { ActionStatus, UiHint, WorkspacePanel } from '../api/types'

export type WorkspaceMode = 'auto' | 'locked'
export type WorkspaceSource = 'ai' | 'user' | 'system'

export interface WorkspaceState {
  mode: WorkspaceMode
  panel: WorkspacePanel
  lockedPanel: WorkspacePanel | null
  source: WorkspaceSource
  reason: string
  lastUserPanel: WorkspacePanel | null
  returnPanel: WorkspacePanel | null
}

export function createWorkspaceState(): WorkspaceState {
  return {
    mode: 'auto',
    panel: 'overview',
    lockedPanel: null,
    source: 'system',
    reason: '',
    lastUserPanel: null,
    returnPanel: null,
  }
}

function isCompletedStatus(status: string) {
  return status === 'completed' || status === 'success'
}

export function applyUserPanel(state: WorkspaceState, panel: WorkspacePanel, reason: string): WorkspaceState {
  return {
    ...state,
    panel,
    lockedPanel: state.mode === 'locked' ? panel : state.lockedPanel,
    source: 'user',
    reason,
    lastUserPanel: panel,
    returnPanel: state.mode === 'locked' ? null : state.returnPanel,
  }
}

export function settleUiAction(state: WorkspaceState, status: ActionStatus): WorkspaceState {
  if (state.mode === 'locked' && isCompletedStatus(status) && state.lockedPanel) {
    return {
      ...state,
      panel: state.lockedPanel,
      source: 'system',
      returnPanel: null,
    }
  }
  if (state.mode === 'locked' && status === 'failed') {
    return {
      ...state,
      returnPanel: null,
    }
  }
  return { ...state }
}

export function applyUiHint(state: WorkspaceState, uiHint: UiHint | null | undefined): WorkspaceState {
  if (!uiHint) return { ...state }

  const { active_action: action } = uiHint
  let next: WorkspaceState = {
    ...state,
    reason: action.reason || state.reason,
  }

  if (action.target_panel) {
    if (state.mode === 'auto') {
      next = {
        ...next,
        panel: action.target_panel,
        source: 'ai',
      }
    } else {
      next = {
        ...next,
        panel: action.target_panel,
        lockedPanel: state.lockedPanel ?? state.panel,
        returnPanel: state.lockedPanel ?? state.returnPanel ?? state.panel,
        source: 'ai',
      }
    }
  }

  return settleUiAction(next, action.status)
}

function toggleLockState(state: WorkspaceState): WorkspaceState {
  if (state.mode === 'auto') {
    return {
      ...state,
      mode: 'locked',
      lockedPanel: state.panel,
      returnPanel: null,
      source: 'user',
      reason: 'toggle-lock',
    }
  }
  return {
    ...state,
    mode: 'auto',
    lockedPanel: null,
    returnPanel: null,
    source: 'user',
    reason: 'toggle-lock',
  }
}

export const useWorkspaceStore = defineStore('workspace', () => {
  const state = reactive(createWorkspaceState())

  function toggleLock() {
    Object.assign(state, toggleLockState(state))
  }

  function reset() {
    Object.assign(state, createWorkspaceState())
  }

  return {
    ...toRefs(state),
    toggleLock,
    reset,
    applyUserPanel: (panel: WorkspacePanel, reason: string) => Object.assign(state, applyUserPanel(state, panel, reason)),
    applyUiHint: (uiHint: UiHint | null | undefined) => Object.assign(state, applyUiHint(state, uiHint)),
    settleUiAction: (status: ActionStatus) => Object.assign(state, settleUiAction(state, status)),
  }
})
