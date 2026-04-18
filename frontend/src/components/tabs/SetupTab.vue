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
      <SetupCharactersPanel
        :items="characterItems"
        :active-character-token="activeCharacterToken"
        @select="activeCharacterToken = $event"
      />
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
      <SetupWorldPanel :world="setup.world_building" />
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
      <SetupConceptPanel :concept="setup.core_concept" />
    </section>
  </div>
  <p v-else class="setup-tab__empty">暂无设定数据。</p>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { SetupCharacter, SetupData } from '../../api/types'
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
  setup: SetupData | null
}>()

const activeSection = ref<SetupSection>('characters')
const activeCharacterToken = ref<string | null>(null)

const characterItems = computed<SetupCharacterItem[]>(() => {
  const signatureCount = new Map<string, number>()

  return (props.setup?.characters ?? []).map((character) => {
    const signature = buildCharacterSignature(character)
    const occurrence = signatureCount.get(signature) ?? 0
    signatureCount.set(signature, occurrence + 1)

    const token = `${signature}::${occurrence + 1}`

    return {
      key: token,
      token,
      testId: buildCharacterTestId(character.name, occurrence),
      character,
    }
  })
})

activeCharacterToken.value = characterItems.value[0]?.token ?? null

watch(() => props.setup?.id, () => {
  activeSection.value = 'characters'
  activeCharacterToken.value = characterItems.value[0]?.token ?? null
})

watch(characterItems, (items) => {
  if (!items.length) {
    activeCharacterToken.value = null
    return
  }

  const hasActiveCharacter = activeCharacterToken.value !== null
    && items.some((item) => item.token === activeCharacterToken.value)

  if (!hasActiveCharacter) {
    activeCharacterToken.value = items[0].token
  }
})

function isSectionActive(section: SetupSection): boolean {
  return activeSection.value === section
}

function buildCharacterSignature(character: SetupCharacter): string {
  return [
    normalizeCharacterField(character.name),
    normalizeCharacterField(character.age),
    normalizeCharacterField(character.gender),
    normalizeCharacterField(character.personality),
    normalizeCharacterField(character.background),
    normalizeCharacterField(character.goals),
    normalizeCharacterField(character.character_status),
  ].join('|')
}

function normalizeCharacterField(value: string | number | null | undefined): string {
  if (typeof value === 'string') {
    return value.trim()
  }

  if (typeof value === 'number') {
    return String(value)
  }

  return ''
}

function buildCharacterTestId(name: string, occurrence: number): string {
  if (occurrence === 0) {
    return `setup-character-item-${name}`
  }

  return `setup-character-item-${name}-${occurrence + 1}`
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

.setup-tab__empty {
  padding: 1rem;
  color: var(--ink-muted);
  font-size: 0.875rem;
}
</style>
