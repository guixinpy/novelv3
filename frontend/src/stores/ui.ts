import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  defaultAthenaRouteState,
  type AthenaPrimarySection,
  type AthenaRouteIntent,
} from '../views/athenaNavigation'

export type Workspace = 'hermes' | 'athena' | 'manuscript'

export type AthenaUiState = AthenaRouteIntent
interface AthenaProjectUiState {
  active: AthenaUiState
  sections: Record<AthenaPrimarySection, AthenaUiState>
}

function cloneAthenaState(state: AthenaUiState): AthenaUiState {
  return { ...state }
}

function cloneAthenaSectionStates(
  states: Record<AthenaPrimarySection, AthenaUiState>,
): Record<AthenaPrimarySection, AthenaUiState> {
  return {
    overview: cloneAthenaState(states.overview),
    catalog: cloneAthenaState(states.catalog),
    narrative: cloneAthenaState(states.narrative),
    truth: cloneAthenaState(states.truth),
    review: cloneAthenaState(states.review),
  }
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

function defaultAthenaProjectState(): AthenaProjectUiState {
  const sections = defaultAthenaSectionStates()
  return {
    active: cloneAthenaState(sections.overview),
    sections,
  }
}

export const useUiStore = defineStore('ui', () => {
  const activeWorkspace = ref<Workspace>('hermes')
  const subNavCollapsed = ref(false)
  const initialAthenaProjectState = defaultAthenaProjectState()
  const activeAthenaState = ref<AthenaUiState>(cloneAthenaState(initialAthenaProjectState.active))
  const athenaSectionStates = ref<Record<AthenaPrimarySection, AthenaUiState>>(
    cloneAthenaSectionStates(initialAthenaProjectState.sections),
  )
  const athenaProjectStates = ref<Record<string, AthenaProjectUiState>>({})
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

  function ensureAthenaProjectState(projectId: string) {
    const existing = athenaProjectStates.value[projectId]
    if (existing) return existing

    const projectState = defaultAthenaProjectState()
    athenaProjectStates.value = {
      ...athenaProjectStates.value,
      [projectId]: projectState,
    }
    return projectState
  }

  function setAthenaState(projectId: string, state: AthenaUiState) {
    const current = ensureAthenaProjectState(projectId)
    const normalizedState = cloneAthenaState(state)
    const sections = {
      ...current.sections,
      [normalizedState.section]: normalizedState,
    }
    const nextProjectState: AthenaProjectUiState = {
      active: normalizedState,
      sections,
    }
    athenaProjectStates.value = {
      ...athenaProjectStates.value,
      [projectId]: nextProjectState,
    }
    activeAthenaState.value = normalizedState
    athenaSectionStates.value = cloneAthenaSectionStates(sections)
  }

  function getActiveAthenaState(projectId: string) {
    return cloneAthenaState(ensureAthenaProjectState(projectId).active)
  }

  function getAthenaSectionState(projectId: string, section: AthenaPrimarySection) {
    return cloneAthenaState(ensureAthenaProjectState(projectId).sections[section] ?? defaultAthenaRouteState(section))
  }

  return {
    activeWorkspace,
    subNavCollapsed,
    activeAthenaState,
    athenaSectionStates,
    athenaProjectStates,
    modals,
    lastProjectRoute,
    toggleSubNav,
    openModal,
    closeModal,
    setWorkspace,
    setAthenaState,
    getActiveAthenaState,
    getAthenaSectionState,
  }
})
