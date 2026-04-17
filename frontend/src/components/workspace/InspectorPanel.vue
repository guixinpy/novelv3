<template>
  <section class="inspector-panel">
    <header class="inspector-panel__toolbar">
      <div class="space-y-2">
        <p class="inspector-panel__eyebrow">Inspector</p>
        <div class="flex flex-wrap items-center gap-3">
          <h2 class="inspector-panel__title">{{ activeTabLabel }}</h2>
          <span class="inspector-panel__source">{{ sourceLabel }}</span>
        </div>
        <p class="inspector-panel__reason">{{ reasonCopy }}</p>
      </div>
      <button
        class="inspector-panel__lock"
        :class="{ 'is-locked': mode === 'locked' }"
        @click="emit('toggle-lock')"
      >
        {{ mode === 'locked' ? `已锁定 · ${lockedPanelLabel}` : '自动联动' }}
      </button>
    </header>

    <nav class="inspector-panel__tabs" aria-label="Workspace tabs">
      <WorkspaceTabs
        :active="panel"
        :tabs="tabs"
        variant="inspector"
        orientation="horizontal"
        wrap="desktop"
        @select="forwardSelectPanel"
      />
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
import { computed } from 'vue'
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

const activeTabLabel = computed(() =>
  props.tabs.find((tab) => tab.id === props.panel)?.label ?? '概览',
)

const lockedPanelLabel = computed(() =>
  props.tabs.find((tab) => tab.id === props.lockedPanel)?.label ?? activeTabLabel.value,
)

const sourceLabel = computed(() => {
  if (props.source === 'user') return '来自你的焦点'
  if (props.source === 'ai') return '来自 AI 动作'
  return '系统状态'
})

const reasonCopy = computed(() => {
  if (props.reason) return props.reason
  if (props.mode === 'locked') return `锁定在 ${lockedPanelLabel.value}，关键动作会临时借道。`
  return '右侧会根据你的操作和 AI 状态自动切换。'
})

function forwardSelectPanel(panelId: string) {
  emit('select-panel', panelId as WorkspacePanel)
}
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
  flex-direction: column;
  gap: 0.9rem;
  padding: 1.15rem 1.15rem 1rem;
  border-bottom: 1px solid rgba(111, 69, 31, 0.16);
  background:
    linear-gradient(180deg, rgba(255, 250, 239, 0.95) 0%, rgba(243, 234, 217, 0.86) 100%);
}

.inspector-panel__eyebrow {
  color: var(--ink-muted);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.inspector-panel__title {
  color: var(--ink-strong);
  font-family: "Palatino Linotype", "Book Antiqua", serif;
  font-size: 1.5rem;
  font-weight: 700;
}

.inspector-panel__source {
  border: 1px solid rgba(111, 69, 31, 0.15);
  background: rgba(255, 248, 233, 0.82);
  color: var(--accent-strong);
  border-radius: 999px;
  padding: 0.2rem 0.65rem;
  font-size: 0.74rem;
  font-weight: 600;
}

.inspector-panel__reason {
  color: var(--ink-muted);
  font-size: 0.92rem;
  line-height: 1.5;
}

.inspector-panel__lock {
  align-self: flex-start;
  border: 1px solid rgba(111, 69, 31, 0.18);
  background: rgba(255, 250, 242, 0.82);
  color: var(--ink-muted);
  border-radius: 999px;
  padding: 0.45rem 0.85rem;
  font-size: 0.82rem;
  font-weight: 700;
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease;
}

.inspector-panel__lock.is-locked {
  background: rgba(111, 69, 31, 0.92);
  color: #fff6e8;
  border-color: rgba(111, 69, 31, 0.92);
}

.inspector-panel__tabs {
  padding: 0.9rem 1.15rem 1rem;
  border-bottom: 1px solid rgba(111, 69, 31, 0.12);
}

.inspector-panel__body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 1rem 1.15rem 1.15rem;
}

@media (min-width: 768px) {
  .inspector-panel__toolbar {
    padding: 1.25rem 1.25rem 1rem;
  }

  .inspector-panel__tabs {
    padding: 1rem 1.25rem 1rem;
  }

  .inspector-panel__body {
    padding: 1rem 1.25rem 1.25rem;
  }
}

@media (min-width: 1280px) {
  .inspector-panel__toolbar {
    flex-direction: row;
    align-items: flex-start;
    justify-content: space-between;
  }

  .inspector-panel__lock {
    align-self: center;
  }
}
</style>
