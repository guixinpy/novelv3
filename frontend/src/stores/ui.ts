import { defineStore } from 'pinia'
import { ref } from 'vue'

export type Workspace = 'hermes' | 'athena' | 'manuscript'
export type AthenaSection =
  | 'characters' | 'locations' | 'factions' | 'items' | 'relations' | 'rules'
  | 'projection' | 'timeline' | 'knowledge'
  | 'outline' | 'storyline' | 'proposals' | 'consistency'

export const useUiStore = defineStore('ui', () => {
  const activeWorkspace = ref<Workspace>('hermes')
  const subNavCollapsed = ref(false)
  const activeAthenaSection = ref<AthenaSection>('characters')
  const modals = ref<string[]>([])

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

  function setAthenaSection(section: AthenaSection) {
    activeAthenaSection.value = section
  }

  return {
    activeWorkspace,
    subNavCollapsed,
    activeAthenaSection,
    modals,
    toggleSubNav,
    openModal,
    closeModal,
    setWorkspace,
    setAthenaSection,
  }
})
