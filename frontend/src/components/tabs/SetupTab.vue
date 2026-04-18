<template>
  <div v-if="setup" class="setup-tab">
    <SetupSectionTabs :active="activeSection" @select="activeSection = $event" />

    <section
      id="setup-section-panel-characters"
      class="setup-panel"
      data-testid="setup-section-panel-characters"
      role="tabpanel"
      aria-labelledby="setup-section-tab-characters"
      :aria-hidden="!isSectionActive('characters')"
      :hidden="!isSectionActive('characters')"
      v-show="isSectionActive('characters')"
    >
      <div class="setup-panel__header">
        <h4 class="setup-panel__title">角色</h4>
      </div>
      <div class="setup-character-list">
        <div
          v-for="(character, index) in setup.characters"
          :key="`${character.name}-${index}`"
          class="setup-character-list__item"
        >
          {{ character.name }}
        </div>
      </div>
    </section>

    <section
      id="setup-section-panel-world"
      class="setup-panel"
      data-testid="setup-section-panel-world"
      role="tabpanel"
      aria-labelledby="setup-section-tab-world"
      :aria-hidden="!isSectionActive('world')"
      :hidden="!isSectionActive('world')"
      v-show="isSectionActive('world')"
    >
      <div class="setup-panel__header">
        <h4 class="setup-panel__title">时代背景</h4>
      </div>
    </section>

    <section
      id="setup-section-panel-concept"
      class="setup-panel"
      data-testid="setup-section-panel-concept"
      role="tabpanel"
      aria-labelledby="setup-section-tab-concept"
      :aria-hidden="!isSectionActive('concept')"
      :hidden="!isSectionActive('concept')"
      v-show="isSectionActive('concept')"
    >
      <div class="setup-panel__header">
        <h4 class="setup-panel__title">主题</h4>
      </div>
    </section>
  </div>
  <p v-else class="setup-tab__empty">暂无设定数据。</p>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import type { SetupData } from '../../api/types'
import SetupSectionTabs from './SetupSectionTabs.vue'

type SetupSection = 'characters' | 'world' | 'concept'

const props = defineProps<{
  setup: SetupData | null
}>()

const activeSection = ref<SetupSection>('characters')

watch(() => props.setup?.id, () => {
  activeSection.value = 'characters'
})

function isSectionActive(section: SetupSection): boolean {
  return activeSection.value === section
}
</script>

<style scoped>
.setup-tab {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.setup-panel {
  border: 1px solid rgba(111, 69, 31, 0.16);
  border-radius: 1rem;
  padding: 1rem;
  background:
    linear-gradient(180deg, rgba(252, 249, 241, 0.94) 0%, rgba(244, 237, 223, 0.92) 100%);
  box-shadow:
    0 14px 30px rgba(85, 58, 29, 0.08),
    inset 0 1px 0 rgba(255, 251, 242, 0.82);
}

.setup-panel__header {
  margin-bottom: 0.75rem;
}

.setup-panel__title {
  color: var(--accent-strong);
  font-size: 0.95rem;
  font-weight: 700;
  line-height: 1.3;
}

.setup-character-list {
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}

.setup-character-list__item {
  border: 1px solid rgba(111, 69, 31, 0.12);
  border-radius: 0.8rem;
  padding: 0.72rem 0.82rem;
  background: rgba(255, 251, 243, 0.72);
  color: var(--ink-strong);
  font-size: 0.92rem;
  font-weight: 600;
  line-height: 1.35;
}

.setup-tab__empty {
  padding: 1rem;
  color: var(--ink-muted);
  font-size: 0.875rem;
}
</style>
