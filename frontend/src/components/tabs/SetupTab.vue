<template>
  <div v-if="setup" class="setup-tab">
    <SetupSummaryCard
      title="角色"
      :description="characterDescription"
      test-id="setup-summary-card-characters"
      body-test-id="setup-summary-card-characters-body"
      @open="openDetail('characters')"
    >
      <ul v-if="characterSummary.entries.length > 0" class="setup-summary-list" aria-label="角色概览">
        <li
          v-for="(entry, index) in characterSummary.entries"
          :key="`${entry.name}-${index}`"
          class="setup-summary-list__item"
        >
          <div class="setup-summary-list__headline">
            <span class="setup-summary-list__label">{{ entry.name }}</span>
            <span v-if="entry.meta?.length" class="setup-summary-list__meta">{{ entry.meta.join(' / ') }}</span>
          </div>
          <p class="setup-summary-list__value">{{ entry.summary }}</p>
        </li>
      </ul>
      <p
        v-else
        class="setup-summary-empty"
        data-testid="setup-summary-card-characters-empty"
      >
        暂无角色概览
      </p>
    </SetupSummaryCard>

    <SetupSummaryCard
      title="世界观"
      test-id="setup-summary-card-world"
      body-test-id="setup-summary-card-world-body"
      @open="openDetail('world')"
    >
      <ul v-if="worldSummary.length > 0" class="setup-summary-list" aria-label="世界观概览">
        <li
          v-for="(item, index) in worldSummary"
          :key="`${item.label}-${index}`"
          class="setup-summary-list__item"
        >
          <div class="setup-summary-list__headline">
            <span class="setup-summary-list__label">{{ item.label }}</span>
          </div>
          <p class="setup-summary-list__value">{{ item.value }}</p>
        </li>
      </ul>
      <p
        v-else
        class="setup-summary-empty"
        data-testid="setup-summary-card-world-empty"
      >
        世界观待补充
      </p>
    </SetupSummaryCard>

    <SetupSummaryCard
      title="核心概念"
      test-id="setup-summary-card-concept"
      body-test-id="setup-summary-card-concept-body"
      @open="openDetail('concept')"
    >
      <ul v-if="conceptSummary.length > 0" class="setup-summary-list" aria-label="核心概念概览">
        <li
          v-for="(item, index) in conceptSummary"
          :key="`${item.label}-${index}`"
          class="setup-summary-list__item"
        >
          <div class="setup-summary-list__headline">
            <span class="setup-summary-list__label">{{ item.label }}</span>
          </div>
          <p class="setup-summary-list__value">{{ item.value }}</p>
        </li>
      </ul>
      <p
        v-else
        class="setup-summary-empty"
        data-testid="setup-summary-card-concept-empty"
      >
        核心概念待补充
      </p>
    </SetupSummaryCard>

    <SetupDetailModal
      :show="isDetailModalOpen"
      :setup="setup"
      :initial-section="detailModalSection"
      @close="isDetailModalOpen = false"
    />
  </div>
  <p v-else class="setup-tab__empty">暂无设定数据。</p>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { SetupData } from '../../api/types'
import SetupDetailModal from './SetupDetailModal.vue'
import SetupSummaryCard from './SetupSummaryCard.vue'
import {
  buildCharacterSummaryItems,
  buildConceptSummaryItems,
  buildWorldSummaryItems,
} from './setupSummaryPresentation'

type SetupSection = 'characters' | 'world' | 'concept'

const props = defineProps<{
  setup: SetupData | null
}>()

const isDetailModalOpen = ref(false)
const detailModalSection = ref<SetupSection>('characters')

const characterSummary = computed(() => buildCharacterSummaryItems(props.setup?.characters ?? []))
const worldSummary = computed(() => {
  if (!props.setup) {
    return []
  }

  return buildWorldSummaryItems(props.setup.world_building)
})
const conceptSummary = computed(() => {
  if (!props.setup) {
    return []
  }

  return buildConceptSummaryItems(props.setup.core_concept)
})
const characterDescription = computed(() => {
  const count = characterSummary.value.count

  if (count <= 0) {
    return '暂无角色概览'
  }

  return `共 ${count} 名角色`
})

watch(() => props.setup?.id, () => {
  isDetailModalOpen.value = false
  detailModalSection.value = 'characters'
})

function openDetail(section: SetupSection): void {
  detailModalSection.value = section
  isDetailModalOpen.value = true
}
</script>

<style scoped>
.setup-tab {
  display: grid;
  gap: 0.85rem;
}

.setup-summary-list {
  display: grid;
  gap: 0.7rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.setup-summary-list__item {
  display: grid;
  gap: 0.2rem;
}

.setup-summary-list__headline {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
}

.setup-summary-list__label {
  color: var(--ink-strong);
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1.35;
}

.setup-summary-list__meta {
  color: var(--ink-muted);
  font-size: 0.74rem;
  line-height: 1.35;
}

.setup-summary-list__value {
  color: var(--ink-muted);
  font-size: 0.84rem;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.setup-summary-empty {
  color: var(--ink-muted);
  font-size: 0.84rem;
  line-height: 1.55;
}

.setup-tab__empty {
  padding: 1rem;
  color: var(--ink-muted);
  font-size: 0.875rem;
}
</style>
