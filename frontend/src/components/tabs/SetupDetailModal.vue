<template>
  <InspectorDetailModal :show="show" title="设定详情" @close="$emit('close')">
    <div v-if="show" class="setup-detail-modal" data-testid="setup-detail-modal">
      <div ref="tabsRoot" class="setup-detail-modal__tabs">
        <SetupSectionTabs :active="activeSection" @select="activeSection = $event" />
      </div>

      <section
        id="setup-detail-panel-characters"
        class="setup-detail-modal__panel"
        data-testid="setup-detail-panel-characters"
      role="tabpanel"
      aria-labelledby="setup-detail-tab-characters"
      :aria-hidden="activeSection !== 'characters'"
      :hidden="activeSection !== 'characters'"
      v-show="activeSection === 'characters'"
    >
        <div class="setup-detail-modal__panel-head">
          <h3 class="setup-detail-modal__panel-title">角色</h3>
        </div>
        <SetupCharactersPanel
          :items="characterItems"
          :active-character-token="activeCharacterToken"
          @select="activeCharacterToken = $event"
        />
      </section>

      <section
        id="setup-detail-panel-world"
        class="setup-detail-modal__panel"
        data-testid="setup-detail-panel-world"
      role="tabpanel"
      aria-labelledby="setup-detail-tab-world"
      :aria-hidden="activeSection !== 'world'"
      :hidden="activeSection !== 'world'"
      v-show="activeSection === 'world'"
    >
        <div class="setup-detail-modal__panel-head">
          <h3 class="setup-detail-modal__panel-title">世界观</h3>
        </div>
        <SetupWorldPanel :world="setup.world_building" />
      </section>

      <section
        id="setup-detail-panel-concept"
        class="setup-detail-modal__panel"
        data-testid="setup-detail-panel-concept"
      role="tabpanel"
      aria-labelledby="setup-detail-tab-concept"
      :aria-hidden="activeSection !== 'concept'"
      :hidden="activeSection !== 'concept'"
      v-show="activeSection === 'concept'"
    >
        <div class="setup-detail-modal__panel-head">
          <h3 class="setup-detail-modal__panel-title">核心概念</h3>
        </div>
        <SetupConceptPanel :concept="setup.core_concept" />
      </section>
    </div>
  </InspectorDetailModal>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { SetupCharacter, SetupData } from '../../api/types'
import InspectorDetailModal from '../InspectorDetailModal.vue'
import SetupCharactersPanel from './SetupCharactersPanel.vue'
import SetupConceptPanel from './SetupConceptPanel.vue'
import SetupSectionTabs from './SetupSectionTabs.vue'
import SetupWorldPanel from './SetupWorldPanel.vue'

type SetupSection = 'characters' | 'world' | 'concept'
type SetupCharacterItem = {
  key: string
  token: string
  testId: string
  character: SetupCharacter
}

const props = defineProps<{
  show: boolean
  setup: SetupData
  initialSection: SetupSection
}>()

defineEmits<{
  close: []
}>()

const activeSection = ref<SetupSection>(props.initialSection)
const activeCharacterToken = ref<string | null>(null)
const tabsRoot = ref<HTMLElement | null>(null)

const characterItems = computed<SetupCharacterItem[]>(() => {
  const nameCount = new Map<string, number>()

  return props.setup.characters.map((character) => {
    const name = normalizeCharacterField(character.name)
    const occurrence = (nameCount.get(name) ?? 0) + 1
    nameCount.set(name, occurrence)
    const token = occurrence === 1 ? name : `${name}::${occurrence}`
    const testId = occurrence === 1
      ? `setup-character-item-${character.name}`
      : `setup-character-item-${character.name}-${occurrence}`

    return {
      key: token,
      token,
      testId,
      character,
    }
  })
})

watch(
  () => props.initialSection,
  (section) => {
    activeSection.value = section
  },
  { immediate: true },
)

watch(
  characterItems,
  (items) => {
    activeCharacterToken.value = items[0]?.token ?? null
  },
  { immediate: true },
)

watch(
  [() => props.show, activeSection],
  async () => {
    await nextTick()
    syncTabTestIds()
  },
  { immediate: true },
)

function normalizeCharacterField(value: string | number | null | undefined): string {
  if (typeof value === 'string') {
    return value.trim()
  }

  if (typeof value === 'number') {
    return String(value)
  }

  return ''
}

function syncTabTestIds() {
  const root = tabsRoot.value

  if (!root) {
    return
  }

  const mappings: Array<{ source: string; target: string }> = [
    { source: 'setup-section-tab-characters', target: 'setup-detail-tab-characters' },
    { source: 'setup-section-tab-world', target: 'setup-detail-tab-world' },
    { source: 'setup-section-tab-concept', target: 'setup-detail-tab-concept' },
  ]

  for (const mapping of mappings) {
    const element = root.querySelector(`[data-testid="${mapping.source}"]`)
    if (element) {
      element.setAttribute('data-testid', mapping.target)
      element.setAttribute('id', mapping.target)
      element.setAttribute('aria-controls', `setup-detail-panel-${mapping.target.replace('setup-detail-tab-', '')}`)
    }
  }
}
</script>

<style scoped>
.setup-detail-modal {
  display: grid;
  gap: 1rem;
}

.setup-detail-modal__tabs {
  display: flex;
  justify-content: flex-start;
}

.setup-detail-modal__panel {
  display: grid;
  gap: 0.9rem;
}

.setup-detail-modal__panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.setup-detail-modal__panel-title {
  color: var(--accent-strong);
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.3;
}
</style>
