<script setup lang="ts">
import BaseButton from '../base/BaseButton.vue'
import type { AthenaNavItem, AthenaPrimarySection } from '../../views/athenaNavigation'

defineProps<{
  items: AthenaNavItem[]
  activeSection: AthenaPrimarySection
  canImportSetup: boolean
  hasLatestChapter: boolean
}>()

const emit = defineEmits<{
  navigate: [section: AthenaPrimarySection]
  importSetup: []
  analyzeLatestChapter: []
  openChat: []
}>()
</script>

<template>
  <div class="athena-subnav">
    <div class="athena-subnav__section">
      <div class="athena-subnav__section-label">Athena</div>
      <button
        v-for="item in items"
        :key="item.section"
        class="athena-subnav__item"
        :class="{ 'athena-subnav__item--active': activeSection === item.section }"
        @click="emit('navigate', item.section)"
      >
        {{ item.label }}
      </button>
    </div>
    <div class="athena-subnav__divider" />
    <div class="athena-subnav__actions">
      <BaseButton
        v-if="canImportSetup"
        variant="ghost"
        size="sm"
        @click="emit('importSetup')"
      >
        导入 Setup
      </BaseButton>
      <BaseButton
        v-if="hasLatestChapter"
        variant="ghost"
        size="sm"
        @click="emit('analyzeLatestChapter')"
      >
        分析最新章节
      </BaseButton>
      <BaseButton variant="ghost" size="sm" @click="emit('openChat')">
        Athena 对话
      </BaseButton>
    </div>
  </div>
</template>

<style scoped>
.athena-subnav {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.athena-subnav__section {
  margin-bottom: var(--space-1);
}

.athena-subnav__section-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-tertiary);
  padding: var(--space-3) var(--space-3) var(--space-1);
}

.athena-subnav__item {
  display: block;
  width: 100%;
  text-align: left;
  font-size: var(--text-sm);
  padding: var(--space-1) var(--space-3) var(--space-1) var(--space-5);
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.athena-subnav__item:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}

.athena-subnav__item--active {
  color: var(--color-brand);
  font-weight: var(--font-medium);
  background: var(--color-brand-light);
}

.athena-subnav__divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-2) 0;
}

.athena-subnav__actions {
  position: sticky;
  bottom: 0;
  margin-top: auto;
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-primary);
  border-top: 1px solid var(--color-border);
}
</style>
