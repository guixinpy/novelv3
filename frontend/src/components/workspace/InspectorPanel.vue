<template>
  <section class="inspector-panel">
    <header class="inspector-panel__toolbar" data-testid="inspector-toolbar">
      <h2 class="inspector-panel__title">{{ activeTabLabel }}</h2>
      <button
        class="inspector-panel__lock"
        :class="{ 'is-locked': mode === 'locked' }"
        :title="lockTitle"
        @click="emit('toggle-lock')"
      >
        {{ mode === 'locked' ? `锁定：${lockedPanelLabel}` : '自动联动' }}
      </button>
    </header>

    <nav class="inspector-panel__tabs" aria-label="Workspace tabs">
      <div class="inspector-panel__tabs-row">
        <div class="inspector-panel__primary-tabs" data-testid="inspector-primary-tabs">
          <WorkspaceTabs
            :active="panel"
            :tabs="primaryTabs"
            variant="inspector"
            orientation="horizontal"
            wrap="never"
            @select="forwardSelectPanel"
          />
        </div>

        <div
          v-if="overflowTabs.length"
          ref="overflowRef"
          class="inspector-panel__overflow"
        >
          <button
            ref="overflowToggleRef"
            type="button"
            class="inspector-panel__overflow-toggle"
            :class="{ 'is-active': overflowOpen || isOverflowActive }"
            aria-haspopup="menu"
            :aria-expanded="overflowOpen ? 'true' : 'false'"
            data-testid="inspector-more-toggle"
            @click="toggleOverflowMenu"
            @keydown="onOverflowToggleKeydown"
          >
            更多
          </button>

          <div
            v-if="overflowOpen"
            class="inspector-panel__overflow-menu"
            data-testid="inspector-overflow-menu"
            role="menu"
            @focusout="handleOverflowFocusOut"
          >
            <button
              v-for="(tab, index) in overflowTabs"
              :key="tab.id"
              ref="overflowItemRefs"
              type="button"
              class="inspector-panel__overflow-item"
              :class="{ 'is-active': panel === tab.id }"
              role="menuitem"
              @click="selectOverflowPanel(tab.id)"
              @keydown="onOverflowItemKeydown($event, index, tab.id)"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>
      </div>
    </nav>

    <div class="inspector-panel__body">
      <OverviewTab
        v-if="panel === 'overview'"
        :project="project"
        :completed="diagnosis?.completed_items || []"
        :missing="diagnosis?.missing_items || []"
        @export="emit('export', $event)"
      />
      <SetupTab v-else-if="panel === 'setup'" :setup="setup" />
      <StorylineTab v-else-if="panel === 'storyline'" :storyline="storyline" />
      <OutlineTab v-else-if="panel === 'outline'" :outline="outline" />
      <ContentTab
        v-else-if="panel === 'content'"
        :chapters="chapters"
        :selected-chapter="selectedChapter"
        :project-id="projectId"
        @select-chapter="emit('select-chapter', $event)"
      />
      <TopologyTab v-else-if="panel === 'topology'" :topology="topology" />
      <VersionsTab
        v-else-if="panel === 'versions'"
        :versions="versions"
        :project-id="projectId"
        @filter="emit('filter-versions', $event)"
        @rollback="emit('rollback-version', $event)"
        @delete-version="emit('delete-version', $event)"
      />
      <PreferencesTab v-else-if="panel === 'preferences'" :project-id="projectId" />
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import type { WorkspacePanel } from '../../api/types'
import type { Diagnosis } from '../../stores/chat'
import type { WorkspaceMode, WorkspaceSource } from '../../stores/workspace'
import WorkspaceTabs from '../WorkspaceTabs.vue'
import ContentTab from '../tabs/ContentTab.vue'
import OutlineTab from '../tabs/OutlineTab.vue'
import OverviewTab from '../tabs/OverviewTab.vue'
import PreferencesTab from '../tabs/PreferencesTab.vue'
import SetupTab from '../tabs/SetupTab.vue'
import StorylineTab from '../tabs/StorylineTab.vue'
import TopologyTab from '../tabs/TopologyTab.vue'
import VersionsTab from '../tabs/VersionsTab.vue'
import type { WorkspaceTab } from './workspaceMeta'

const PRIMARY_PANEL_IDS = new Set<WorkspacePanel>([
  'overview',
  'setup',
  'storyline',
  'outline',
  'content',
])

const props = defineProps<{
  project: any
  projectId: string
  tabs: WorkspaceTab[]
  panel: WorkspacePanel
  mode: WorkspaceMode
  lockedPanel: WorkspacePanel | null
  source: WorkspaceSource
  reason: string
  diagnosis: Diagnosis | null
  setup: any
  storyline: any
  outline: any
  chapters: any[]
  selectedChapter: any
  topology: any
  versions: any[]
}>()

const emit = defineEmits<{
  'select-panel': [panel: WorkspacePanel]
  'toggle-lock': []
  export: [format: string]
  'select-chapter': [index: number]
  'filter-versions': [type: string]
  'rollback-version': [id: string]
  'delete-version': [id: string]
}>()

const overflowOpen = ref(false)
const overflowRef = ref<HTMLElement | null>(null)
const overflowToggleRef = ref<HTMLButtonElement | null>(null)
const overflowItemRefs = ref<HTMLButtonElement[]>([])

const activeTabLabel = computed(() =>
  props.tabs.find((tab) => tab.id === props.panel)?.label ?? '概览',
)

const primaryTabs = computed(() =>
  props.tabs.filter((tab) => PRIMARY_PANEL_IDS.has(tab.id)),
)

const overflowTabs = computed(() =>
  props.tabs.filter((tab) => !PRIMARY_PANEL_IDS.has(tab.id)),
)

const lockedPanelLabel = computed(() =>
  props.tabs.find((tab) => tab.id === props.lockedPanel)?.label ?? activeTabLabel.value,
)

const isOverflowActive = computed(() =>
  overflowTabs.value.some((tab) => tab.id === props.panel),
)

const lockTitle = computed(() =>
  props.mode === 'locked'
    ? `当前锁定在 ${lockedPanelLabel.value}`
    : '右侧会根据上下文自动联动',
)

function forwardSelectPanel(panelId: string) {
  closeOverflowMenu()
  emit('select-panel', panelId as WorkspacePanel)
}

function toggleOverflowMenu() {
  if (overflowOpen.value) {
    closeOverflowMenu()
    return
  }
  openOverflowMenu()
}

function selectOverflowPanel(panelId: WorkspacePanel) {
  closeOverflowMenu()
  emit('select-panel', panelId)
}

function openOverflowMenu(focusIndex?: number) {
  overflowOpen.value = true
  if (focusIndex == null) return
  focusOverflowItem(focusIndex)
}

function closeOverflowMenu({ restoreFocus = false }: { restoreFocus?: boolean } = {}) {
  overflowOpen.value = false
  if (!restoreFocus) return
  nextTick(() => {
    overflowToggleRef.value?.focus()
  })
}

function focusOverflowItem(index: number) {
  const total = overflowTabs.value.length
  if (!total) return
  const normalizedIndex = ((index % total) + total) % total
  nextTick(() => {
    overflowItemRefs.value[normalizedIndex]?.focus()
  })
}

function onOverflowToggleKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    openOverflowMenu(0)
    return
  }

  if (event.key === 'ArrowUp') {
    event.preventDefault()
    openOverflowMenu(overflowTabs.value.length - 1)
    return
  }

  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    if (overflowOpen.value) {
      closeOverflowMenu()
      return
    }
    openOverflowMenu(0)
  }
}

function onOverflowItemKeydown(event: KeyboardEvent, index: number, panelId: WorkspacePanel) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    focusOverflowItem(index + 1)
    return
  }

  if (event.key === 'ArrowUp') {
    event.preventDefault()
    focusOverflowItem(index - 1)
    return
  }

  if (event.key === 'Home') {
    event.preventDefault()
    focusOverflowItem(0)
    return
  }

  if (event.key === 'End') {
    event.preventDefault()
    focusOverflowItem(overflowTabs.value.length - 1)
    return
  }

  if (event.key === 'Escape') {
    event.preventDefault()
    closeOverflowMenu({ restoreFocus: true })
    return
  }

  if (event.key === 'Tab') {
    window.setTimeout(() => {
      closeOverflowMenu()
    }, 0)
    return
  }

  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    selectOverflowPanel(panelId)
  }
}

function handleDocumentPointerDown(event: PointerEvent) {
  if (!overflowOpen.value || !overflowRef.value) return
  if (!(event.target instanceof Node)) return
  if (overflowRef.value.contains(event.target)) return
  closeOverflowMenu()
}

function handleOverflowFocusOut(event: FocusEvent) {
  if (!overflowOpen.value || !overflowRef.value) return
  const nextTarget = event.relatedTarget
  if (nextTarget instanceof Node && overflowRef.value.contains(nextTarget)) return
  closeOverflowMenu()
}

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentPointerDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
})
</script>

<style scoped>
.inspector-panel {
  display: flex;
  height: 100%;
  min-height: 0;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(88, 66, 39, 0.22);
  background:
    linear-gradient(180deg, rgba(250, 246, 238, 0.97) 0%, rgba(245, 239, 228, 0.96) 100%);
  box-shadow:
    0 24px 40px rgba(70, 47, 23, 0.1),
    inset 0 1px 0 rgba(255, 252, 246, 0.82);
  border-radius: 1.7rem;
}

.inspector-panel__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.95rem 1rem 0.75rem;
  border-bottom: 1px solid rgba(111, 69, 31, 0.16);
  background:
    linear-gradient(180deg, rgba(255, 250, 239, 0.95) 0%, rgba(243, 234, 217, 0.86) 100%);
}

.inspector-panel__title {
  color: var(--ink-strong);
  font-family: "Palatino Linotype", "Book Antiqua", serif;
  font-size: 1.18rem;
  font-weight: 700;
  line-height: 1.1;
}

.inspector-panel__lock {
  border: 1px solid rgba(111, 69, 31, 0.18);
  background: rgba(255, 250, 242, 0.82);
  color: var(--ink-muted);
  border-radius: 999px;
  padding: 0.35rem 0.72rem;
  font-size: 0.76rem;
  font-weight: 700;
  line-height: 1.2;
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease;
}

.inspector-panel__lock.is-locked {
  background: rgba(111, 69, 31, 0.92);
  color: #fff6e8;
  border-color: rgba(111, 69, 31, 0.92);
}

.inspector-panel__tabs {
  padding: 0.65rem 1rem 0.75rem;
  border-bottom: 1px solid rgba(111, 69, 31, 0.12);
}

.inspector-panel__tabs-row {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
}

.inspector-panel__primary-tabs {
  min-width: 0;
  flex: 1;
}

.inspector-panel__overflow {
  position: relative;
  flex: 0 0 auto;
}

.inspector-panel__overflow-toggle,
.inspector-panel__overflow-item {
  border: 1px solid rgba(111, 69, 31, 0.12);
  background: rgba(255, 251, 243, 0.9);
  color: var(--ink-muted);
  border-radius: 0.8rem;
  padding: 0.35rem 0.72rem;
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.2;
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease;
}

.inspector-panel__overflow-toggle:hover,
.inspector-panel__overflow-item:hover,
.inspector-panel__overflow-toggle.is-active,
.inspector-panel__overflow-item.is-active {
  border-color: rgba(111, 69, 31, 0.24);
  background: linear-gradient(180deg, rgba(147, 96, 49, 0.12) 0%, rgba(111, 69, 31, 0.2) 100%);
  color: var(--accent-strong);
}

.inspector-panel__overflow-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 0.45rem);
  z-index: 20;
  display: grid;
  gap: 0.35rem;
  min-width: 9rem;
  padding: 0.45rem;
  border: 1px solid rgba(111, 69, 31, 0.16);
  border-radius: 1rem;
  background:
    linear-gradient(180deg, rgba(255, 250, 241, 0.98) 0%, rgba(246, 239, 228, 0.98) 100%);
  box-shadow:
    0 18px 28px rgba(70, 47, 23, 0.14),
    inset 0 1px 0 rgba(255, 252, 246, 0.8);
}

.inspector-panel__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0.95rem 1rem 1rem;
}

@media (min-width: 768px) {
  .inspector-panel__toolbar {
    padding: 1rem 1.1rem 0.8rem;
  }

  .inspector-panel__tabs {
    padding: 0.7rem 1.1rem 0.8rem;
  }

  .inspector-panel__body {
    padding: 1rem 1.1rem 1.1rem;
  }
}
</style>
