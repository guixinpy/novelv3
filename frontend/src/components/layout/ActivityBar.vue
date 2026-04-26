<script setup lang="ts">
import type { Workspace } from '../../stores/ui'

const { activeWorkspace, projectId } = defineProps<{
  activeWorkspace: Workspace | null
  projectId: string
}>()

const emit = defineEmits<{
  navigate: [target: string]
  'toggle-subnav': []
}>()

function onItemClick(item: typeof workspaceItems[number]) {
  if (activeWorkspace === item.key) {
    emit('toggle-subnav')
  } else {
    emit('navigate', item.route(projectId))
  }
}

const workspaceItems: { key: Workspace; icon: string; label: string; route: (id: string) => string }[] = [
  { key: 'hermes', icon: '☿', label: 'Hermes', route: (id) => `/projects/${id}/hermes` },
  { key: 'athena', icon: '⏣', label: 'Athena', route: (id) => `/projects/${id}/athena` },
  { key: 'manuscript', icon: '📜', label: 'Calliope', route: (id) => `/projects/${id}/manuscript` },
]
</script>

<template>
  <aside class="activity-bar">
    <nav class="activity-bar__top">
      <button
        v-for="item in workspaceItems"
        :key="item.key"
        class="activity-bar__item"
        :class="{ 'activity-bar__item--active': activeWorkspace === item.key }"
        :title="item.label"
        :aria-label="item.label"
        @click="onItemClick(item)"
      >
        <span class="activity-bar__icon">{{ item.icon }}</span>
      </button>
    </nav>
    <nav class="activity-bar__bottom">
      <button class="activity-bar__item" title="设置" aria-label="设置" @click="emit('navigate', '/settings')">
        <span class="activity-bar__icon">&#9881;</span>
      </button>
    </nav>
  </aside>
</template>

<style scoped>
.activity-bar {
  grid-area: activity;
  width: var(--activity-bar-width);
  background: var(--color-activity-bar-bg);
  display: flex; flex-direction: column; align-items: center;
  justify-content: space-between; padding: var(--space-2) 0;
}
.activity-bar__top, .activity-bar__bottom {
  display: flex; flex-direction: column; align-items: center; gap: var(--space-1);
}
.activity-bar__item {
  position: relative; width: var(--activity-bar-width); height: var(--activity-bar-width);
  display: flex; align-items: center; justify-content: center;
  color: var(--color-activity-bar-icon); transition: color var(--transition-fast);
}
.activity-bar__item:hover { color: var(--color-activity-bar-icon-active); }
.activity-bar__item--active {
  color: var(--color-activity-bar-icon-active);
  background: var(--color-activity-bar-item-active-bg);
}
.activity-bar__item--active::before {
  content: ''; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 3px; height: 24px; background: var(--color-activity-bar-accent);
  border-radius: 0 2px 2px 0;
}
.activity-bar__icon { font-size: var(--text-lg); line-height: 1; }
</style>
