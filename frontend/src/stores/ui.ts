import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  defaultAthenaRouteState,
  type AthenaPrimarySection,
  type AthenaRouteIntent,
} from '../views/athenaNavigation'

export type Workspace = 'hermes' | 'athena' | 'manuscript'

export type AthenaUiState = AthenaRouteIntent

function cloneAthenaState(state: AthenaUiState): AthenaUiState {
  return { ...state }
}

function defaultAthenaSectionStates(): Record<AthenaPrimarySection, AthenaUiState> {
  return {
    overview: defaultAthenaRouteState('overview'),
    catalog: defaultAthenaRouteState('catalog'),
    narrative: defaultAthenaRouteState('narrative'),
    truth: defaultAthenaRouteState('truth'),
    review: defaultAthenaRouteState('review'),
  }
}

export const useUiStore = defineStore('ui', () => {
  const activeWorkspace = ref<Workspace>('hermes')
  const subNavCollapsed = ref(false)
  const initialAthenaStates = defaultAthenaSectionStates()
  const activeAthenaState = ref<AthenaUiState>(cloneAthenaState(initialAthenaStates.overview))
  const athenaSectionStates = ref<Record<AthenaPrimarySection, AthenaUiState>>(initialAthenaStates)
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
    const normalizedState = cloneAthenaState(state)
    activeAthenaState.value = normalizedState
    athenaSectionStates.value = {
      ...athenaSectionStates.value,
      [normalizedState.section]: normalizedState,
    }
  }

  function getAthenaSectionState(section: AthenaPrimarySection) {
    return cloneAthenaState(athenaSectionStates.value[section] ?? defaultAthenaRouteState(section))
  }

  return {
    activeWorkspace,
    subNavCollapsed,
    activeAthenaState,
    athenaSectionStates,
    modals,
    lastProjectRoute,
    toggleSubNav,
    openModal,
    closeModal,
    setWorkspace,
    setAthenaState,
    getAthenaSectionState,
  }
})
