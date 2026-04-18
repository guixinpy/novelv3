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
        @select="handleCharacterSelect"
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

type CharacterSelectionSnapshot = {
  name: string
  background: string
  personality: string
  goals: string
  age: string
  gender: string
  characterStatus: string
}

const props = defineProps<{
  setup: SetupData | null
}>()

const activeSection = ref<SetupSection>('characters')
const activeCharacterToken = ref<string | null>(null)
const activeCharacterSnapshot = ref<CharacterSelectionSnapshot | null>(null)

const characterItems = computed<SetupCharacterItem[]>(() => {
  const nameCount = new Map<string, number>()

  return (props.setup?.characters ?? []).map((character) => {
    const name = normalizeCharacterField(character.name)
    const occurrence = (nameCount.get(name) ?? 0) + 1
    nameCount.set(name, occurrence)
    const token = buildCharacterToken(name, occurrence)

    return {
      key: token,
      token,
      testId: buildCharacterTestId(character.name, occurrence),
      character,
    }
  })
})

activeCharacterToken.value = characterItems.value[0]?.token ?? null
activeCharacterSnapshot.value = buildCharacterSnapshot(characterItems.value[0]?.character ?? null)

watch(() => props.setup?.id, () => {
  activeSection.value = 'characters'
  activeCharacterToken.value = characterItems.value[0]?.token ?? null
  activeCharacterSnapshot.value = buildCharacterSnapshot(characterItems.value[0]?.character ?? null)
})

watch(characterItems, (items) => {
  if (!items.length) {
    activeCharacterToken.value = null
    activeCharacterSnapshot.value = null
    return
  }

  const nextActiveCharacter = resolveActiveCharacter(items)
  activeCharacterToken.value = nextActiveCharacter.token
  activeCharacterSnapshot.value = buildCharacterSnapshot(nextActiveCharacter.character)
})

function isSectionActive(section: SetupSection): boolean {
  return activeSection.value === section
}

function handleCharacterSelect(token: string): void {
  const matchedItem = characterItems.value.find((item) => item.token === token)
  activeCharacterToken.value = token
  activeCharacterSnapshot.value = buildCharacterSnapshot(matchedItem?.character ?? null)
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

function buildCharacterToken(name: string, occurrence: number): string {
  if (occurrence === 1) {
    return name
  }

  return `${name}::${occurrence}`
}

function buildCharacterTestId(name: string, occurrence: number): string {
  if (occurrence === 1) {
    return `setup-character-item-${name}`
  }

  return `setup-character-item-${name}-${occurrence}`
}

function buildCharacterSnapshot(character: SetupCharacter | null): CharacterSelectionSnapshot | null {
  if (!character) {
    return null
  }

  return {
    name: normalizeCharacterField(character.name),
    background: normalizeCharacterField(character.background),
    personality: normalizeCharacterField(character.personality),
    goals: normalizeCharacterField(character.goals),
    age: normalizeCharacterField(character.age),
    gender: normalizeCharacterField(character.gender),
    characterStatus: normalizeCharacterField(character.character_status),
  }
}

function resolveActiveCharacter(items: SetupCharacterItem[]): SetupCharacterItem {
  const snapshot = activeCharacterSnapshot.value

  if (snapshot) {
    const matchedItem = findSnapshotMatchedCharacter(items, snapshot)

    if (matchedItem) {
      return matchedItem
    }

    return items[0]
  }

  const token = activeCharacterToken.value

  if (token) {
    const tokenMatchedItem = items.find((item) => item.token === token)

    if (tokenMatchedItem) {
      return tokenMatchedItem
    }
  }

  return items[0]
}

function findSnapshotMatchedCharacter(
  items: SetupCharacterItem[],
  snapshot: CharacterSelectionSnapshot,
): SetupCharacterItem | null {
  const sameNameItems = items.filter(
    (item) => normalizeCharacterField(item.character.name) === snapshot.name,
  )

  if (!sameNameItems.length) {
    return null
  }

  if (sameNameItems.length === 1) {
    return sameNameItems[0]
  }

  const exactMatches = sameNameItems.filter((item) => isExactSnapshotMatch(item.character, snapshot))

  if (exactMatches.length === 1) {
    return exactMatches[0]
  }

  const scoredCandidates = sameNameItems
    .map((item) => ({
      item,
      score: countSnapshotMatchScore(item.character, snapshot),
    }))
    .filter((candidate) => candidate.score > 0)
    .sort((left, right) => right.score - left.score)

  if (!scoredCandidates.length) {
    return null
  }

  if (scoredCandidates.length === 1 || scoredCandidates[0].score > scoredCandidates[1].score) {
    return scoredCandidates[0].item
  }

  return null
}

function isExactSnapshotMatch(
  character: SetupCharacter,
  snapshot: CharacterSelectionSnapshot,
): boolean {
  const currentSnapshot = buildCharacterSnapshot(character)

  return currentSnapshot !== null
    && currentSnapshot.name === snapshot.name
    && currentSnapshot.background === snapshot.background
    && currentSnapshot.personality === snapshot.personality
    && currentSnapshot.goals === snapshot.goals
    && currentSnapshot.age === snapshot.age
    && currentSnapshot.gender === snapshot.gender
    && currentSnapshot.characterStatus === snapshot.characterStatus
}

function countSnapshotMatchScore(
  character: SetupCharacter,
  snapshot: CharacterSelectionSnapshot,
): number {
  const currentSnapshot = buildCharacterSnapshot(character)

  if (!currentSnapshot) {
    return 0
  }

  const comparableFields = [
    ['background', currentSnapshot.background, snapshot.background],
    ['personality', currentSnapshot.personality, snapshot.personality],
    ['goals', currentSnapshot.goals, snapshot.goals],
    ['age', currentSnapshot.age, snapshot.age],
    ['gender', currentSnapshot.gender, snapshot.gender],
    ['characterStatus', currentSnapshot.characterStatus, snapshot.characterStatus],
  ] as const

  return comparableFields.reduce((score, [, currentValue, snapshotValue]) => {
    if (!snapshotValue) {
      return score
    }

    return currentValue === snapshotValue ? score + 1 : score
  }, 0)
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
