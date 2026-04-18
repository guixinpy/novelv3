<template>
  <div class="setup-section-tabs" data-testid="setup-section-tabs" role="tablist" aria-label="设定分区">
    <button
      v-for="(tab, index) in tabs"
      :key="tab.id"
      :id="getTabId(tab.id)"
      :ref="(element) => setTabRef(element, index)"
      :data-testid="tab.testId"
      class="setup-section-tabs__button"
      :class="{ 'is-active': active === tab.id }"
      :aria-selected="active === tab.id"
      :aria-controls="getPanelId(tab.id)"
      :tabindex="active === tab.id ? 0 : -1"
      role="tab"
      type="button"
      @click="$emit('select', tab.id)"
      @keydown="onKeydown($event, index)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { nextTick } from 'vue'

type SetupSection = 'characters' | 'world' | 'concept'

const props = defineProps<{
  active: SetupSection
}>()

const emit = defineEmits<{
  select: [section: SetupSection]
}>()

const tabs: Array<{ id: SetupSection; label: string; testId: string }> = [
  { id: 'characters', label: '角色', testId: 'setup-section-tab-characters' },
  { id: 'world', label: '世界观', testId: 'setup-section-tab-world' },
  { id: 'concept', label: '核心概念', testId: 'setup-section-tab-concept' },
]

const tabRefs: Array<HTMLButtonElement | null> = []

function getTabId(section: SetupSection): string {
  return `setup-section-tab-${section}`
}

function getPanelId(section: SetupSection): string {
  return `setup-section-panel-${section}`
}

function setTabRef(element: Element | object | null, index: number) {
  tabRefs[index] = element instanceof HTMLButtonElement ? element : null
}

function moveToTab(index: number) {
  const nextTab = tabs[index]
  if (!nextTab) {
    return
  }

  emit('select', nextTab.id)
  nextTick(() => {
    tabRefs[index]?.focus()
  })
}

function onKeydown(event: KeyboardEvent, index: number) {
  if (event.key === 'ArrowRight') {
    event.preventDefault()
    moveToTab((index + 1) % tabs.length)
    return
  }

  if (event.key === 'ArrowLeft') {
    event.preventDefault()
    moveToTab((index - 1 + tabs.length) % tabs.length)
    return
  }

  if (event.key === 'Home') {
    event.preventDefault()
    moveToTab(0)
    return
  }

  if (event.key === 'End') {
    event.preventDefault()
    moveToTab(tabs.length - 1)
  }
}
</script>

<style scoped>
.setup-section-tabs {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 0.38rem;
  padding: 0.28rem;
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 999px;
  background:
    linear-gradient(180deg, rgba(255, 251, 243, 0.82) 0%, rgba(235, 219, 190, 0.72) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 251, 241, 0.75),
    0 10px 20px rgba(94, 66, 34, 0.08);
}

.setup-section-tabs__button {
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 0.38rem 0.8rem;
  color: var(--ink-muted);
  font-size: 0.78rem;
  font-weight: 600;
  line-height: 1.1;
  white-space: nowrap;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    background-color 0.18s ease,
    color 0.18s ease;
}

.setup-section-tabs__button:hover {
  transform: translateY(-1px);
  border-color: rgba(111, 69, 31, 0.2);
  color: var(--accent-strong);
}

.setup-section-tabs__button.is-active {
  border-color: rgba(111, 69, 31, 0.24);
  background: linear-gradient(180deg, rgba(176, 129, 76, 0.18) 0%, rgba(111, 69, 31, 0.22) 100%);
  color: var(--accent-strong);
  box-shadow: inset 0 1px 0 rgba(255, 247, 231, 0.46);
}
</style>
