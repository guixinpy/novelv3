<template>
  <div :class="containerClass">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      type="button"
      @click="$emit('select', tab.id)"
      class="workspace-tabs__button"
      :class="buttonClass(tab.id)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type WorkspaceTabsVariant = 'default' | 'inspector'
type WorkspaceTabsOrientation = 'vertical' | 'horizontal'
type WorkspaceTabsWrap = 'never' | 'always' | 'desktop'

const props = withDefaults(defineProps<{
  active: string
  tabs: { id: string; label: string }[]
  variant?: WorkspaceTabsVariant
  orientation?: WorkspaceTabsOrientation
  wrap?: WorkspaceTabsWrap
}>(), {
  variant: 'default',
  orientation: 'vertical',
  wrap: 'never',
})

defineEmits<{ select: [id: string] }>()

const containerClass = computed(() => [
  'workspace-tabs',
  `workspace-tabs--${props.variant}`,
  `workspace-tabs--${props.orientation}`,
  `workspace-tabs--wrap-${props.wrap}`,
])

function buttonClass(tabId: string) {
  return [props.active === tabId ? 'is-active' : 'is-idle']
}
</script>

<style scoped>
.workspace-tabs {
  display: flex;
  gap: 0.35rem;
}

.workspace-tabs--vertical {
  flex-direction: column;
}

.workspace-tabs--horizontal {
  overflow-x: auto;
  scrollbar-width: none;
}

.workspace-tabs--horizontal::-webkit-scrollbar {
  display: none;
}

.workspace-tabs--wrap-always {
  flex-wrap: wrap;
}

.workspace-tabs__button {
  border-radius: 0.85rem;
  font-size: 0.875rem;
  transition: transform 0.2s ease, background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.workspace-tabs__button:hover {
  transform: translateY(-1px);
}

.workspace-tabs--default .workspace-tabs__button {
  width: 100%;
  padding: 0.5rem 0.75rem;
  text-align: left;
}

.workspace-tabs--default .workspace-tabs__button.is-active {
  background: rgb(224 231 255);
  color: rgb(67 56 202);
  font-weight: 500;
}

.workspace-tabs--default .workspace-tabs__button.is-idle {
  color: rgb(75 85 99);
}

.workspace-tabs--default .workspace-tabs__button.is-idle:hover {
  background: rgb(243 244 246);
}

.workspace-tabs--inspector {
  gap: 0.42rem;
}

.workspace-tabs--inspector .workspace-tabs__button {
  flex: 0 0 auto;
  border: 1px solid rgba(111, 69, 31, 0.12);
  background: rgba(255, 251, 243, 0.88);
  color: var(--ink-muted);
  padding: 0.36rem 0.72rem;
  white-space: nowrap;
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.2;
}

.workspace-tabs--inspector .workspace-tabs__button.is-idle:hover {
  border-color: rgba(111, 69, 31, 0.22);
  color: var(--accent-strong);
}

.workspace-tabs--inspector .workspace-tabs__button.is-active {
  border-color: rgba(111, 69, 31, 0.24);
  background: linear-gradient(180deg, rgba(147, 96, 49, 0.12) 0%, rgba(111, 69, 31, 0.2) 100%);
  color: var(--accent-strong);
}

@media (min-width: 1024px) {
  .workspace-tabs--wrap-desktop {
    flex-wrap: wrap;
    overflow: visible;
  }
}
</style>
