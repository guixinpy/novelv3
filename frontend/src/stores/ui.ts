import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AthenaNodeTypeFilter, AthenaPrimarySection, AthenaSubview } from '../views/athenaNavigation'

export type Workspace = 'hermes' | 'athena' | 'manuscript'

export interface AthenaUiState {
  section: AthenaPrimarySection
  view: AthenaSubview
  nodeType: AthenaNodeTypeFilter
}

export const useUiStore = defineStore('ui', () => {
  const activeWorkspace = ref<Workspace>('hermes')
  const subNavCollapsed = ref(false)
  const activeAthenaState = ref<AthenaUiState>({ section: 'overview', view: 'dashboard', nodeType: 'all' })
  const modals = ref<string[]>([])
  const lastProjectRoute = ref<string | null>(null)
  function toggleSubNav() {
    subNavCollapsed.value = !subNavCollapsed.value
  }

  function openModal(id: string) {
    if (!modals.value.includes(id)) modals.value.push(id)
  }

  function closeModal(id?: string) {
    if (id) {
      modals.value = modals.value.filter(m => m !== id)
    } else {
      modals.value.pop()
    }
  }

  function setWorkspace(ws: Workspace) {
    activeWorkspace.value = ws
  }

  function setAthenaState(state: AthenaUiState) {
    activeAthenaState.value = state
  }

  return {
    activeWorkspace,
    subNavCollapsed,
    activeAthenaState,
    modals,
    lastProjectRoute,
    toggleSubNav,
    openModal,
    closeModal,
    setWorkspace,
    setAthenaState,
  }
})
