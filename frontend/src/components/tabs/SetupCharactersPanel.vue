<template>
  <div class="setup-characters-panel">
    <div class="setup-characters-panel__list" role="list" aria-label="角色列表">
      <button
        v-for="entry in items"
        :key="entry.key"
        :data-testid="entry.testId"
        class="setup-characters-panel__item"
        :class="{ 'is-active': entry.token === activeCharacterToken }"
        :aria-pressed="entry.token === activeCharacterToken"
        type="button"
        @click="$emit('select', entry.token)"
      >
        <span class="setup-characters-panel__item-name">{{ entry.character.name }}</span>
        <span class="setup-characters-panel__item-summary">{{ buildCharacterSummary(entry.character) }}</span>
      </button>
    </div>

    <article class="setup-character-detail" data-testid="setup-character-detail">
      <template v-if="currentCharacter">
        <header class="setup-character-detail__header">
          <div>
            <h5 class="setup-character-detail__name">{{ currentCharacter.name }}</h5>
            <p v-if="meta.length" class="setup-character-detail__meta">{{ meta.join(' / ') }}</p>
          </div>
        </header>

        <dl class="setup-character-detail__sections">
          <div class="setup-character-detail__section">
            <dt>性格</dt>
            <dd>{{ getDisplayText(currentCharacter.personality) }}</dd>
          </div>
          <div class="setup-character-detail__section">
            <dt>背景</dt>
            <dd>{{ getDisplayText(currentCharacter.background) }}</dd>
          </div>
          <div class="setup-character-detail__section">
            <dt>目标</dt>
            <dd>{{ getDisplayText(currentCharacter.goals) }}</dd>
          </div>
        </dl>
      </template>

      <p v-else class="setup-character-detail__empty">暂无角色</p>
    </article>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SetupCharacter } from '../../api/types'
import { EMPTY_SETUP_TEXT, buildCharacterSummary, getCharacterMeta } from './setupPresentation'

type SetupCharacterItem = {
  key: string
  token: string
  testId: string
  character: SetupCharacter
}

const props = defineProps<{
  items: SetupCharacterItem[]
  activeCharacterToken: string | null
}>()

defineEmits<{
  select: [characterToken: string]
}>()

const currentCharacter = computed(() => {
  const matchedEntry = props.items.find((item) => item.token === props.activeCharacterToken)
  return matchedEntry?.character ?? null
})

const meta = computed(() => {
  if (!currentCharacter.value) {
    return []
  }

  return getCharacterMeta(currentCharacter.value)
})

function getDisplayText(value: string | null | undefined): string {
  const text = typeof value === 'string' ? value.trim() : ''
  return text || EMPTY_SETUP_TEXT
}
</script>

<style scoped>
.setup-characters-panel {
  display: grid;
  grid-template-columns: minmax(13rem, 17rem) minmax(0, 1fr);
  gap: 1rem;
}

.setup-characters-panel__list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.setup-characters-panel__item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  width: 100%;
  border: 1px solid rgba(111, 69, 31, 0.12);
  border-radius: 0.9rem;
  padding: 0.78rem 0.86rem;
  background:
    linear-gradient(180deg, rgba(255, 251, 243, 0.88) 0%, rgba(244, 237, 223, 0.82) 100%);
  color: var(--ink-strong);
  text-align: left;
  box-shadow: inset 0 1px 0 rgba(255, 251, 242, 0.72);
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    background 0.18s ease;
}

.setup-characters-panel__item:hover {
  transform: translateY(-1px);
  border-color: rgba(111, 69, 31, 0.24);
}

.setup-characters-panel__item.is-active {
  border-color: rgba(111, 69, 31, 0.3);
  background:
    linear-gradient(180deg, rgba(239, 224, 194, 0.96) 0%, rgba(226, 204, 166, 0.9) 100%);
  box-shadow:
    0 10px 18px rgba(94, 66, 34, 0.08),
    inset 0 1px 0 rgba(255, 247, 231, 0.76);
}

.setup-characters-panel__item-name {
  font-size: 0.96rem;
  font-weight: 700;
  line-height: 1.3;
}

.setup-characters-panel__item-summary {
  color: var(--ink-muted);
  font-size: 0.84rem;
  line-height: 1.5;
}

.setup-character-detail {
  min-height: 100%;
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 1rem;
  padding: 0.95rem 1rem;
  background:
    linear-gradient(180deg, rgba(255, 251, 243, 0.86) 0%, rgba(247, 240, 227, 0.88) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 251, 242, 0.82),
    0 10px 22px rgba(85, 58, 29, 0.06);
}

.setup-character-detail__header {
  margin-bottom: 0.95rem;
}

.setup-character-detail__name {
  color: var(--accent-strong);
  font-size: 1.02rem;
  font-weight: 700;
  line-height: 1.3;
}

.setup-character-detail__meta {
  margin-top: 0.28rem;
  color: var(--ink-muted);
  font-size: 0.83rem;
  line-height: 1.4;
}

.setup-character-detail__sections {
  display: flex;
  flex-direction: column;
  gap: 0.78rem;
}

.setup-character-detail__section {
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
}

.setup-character-detail__section dt {
  color: var(--accent-strong);
  font-size: 0.8rem;
  font-weight: 700;
  line-height: 1.3;
}

.setup-character-detail__section dd {
  margin: 0;
  color: var(--ink-strong);
  font-size: 0.9rem;
  line-height: 1.6;
  white-space: pre-wrap;
}

.setup-character-detail__empty {
  color: var(--ink-muted);
  font-size: 0.88rem;
}

@media (max-width: 860px) {
  .setup-characters-panel {
    grid-template-columns: 1fr;
  }
}
</style>
