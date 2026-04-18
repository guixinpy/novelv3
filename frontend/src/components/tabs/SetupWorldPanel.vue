<template>
  <div class="setup-world-panel">
    <article
      v-for="section in sections"
      :key="section.key"
      class="setup-world-panel__card"
      data-testid="setup-world-card"
    >
      <h5 class="setup-world-panel__label" data-testid="setup-world-label">{{ section.label }}</h5>
      <p class="setup-world-panel__value" data-testid="setup-world-value">{{ section.value }}</p>
    </article>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { SetupWorldBuilding } from '../../api/types'
import { getWorldSections } from './setupPresentation'

const props = defineProps<{
  world: SetupWorldBuilding
}>()

const sections = computed(() => getWorldSections(props.world))
</script>

<style scoped>
.setup-world-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.85rem;
}

.setup-world-panel__card {
  border: 1px solid rgba(111, 69, 31, 0.12);
  border-radius: 0.95rem;
  padding: 0.9rem 0.95rem;
  background:
    linear-gradient(180deg, rgba(255, 251, 243, 0.9) 0%, rgba(247, 240, 227, 0.9) 100%);
  box-shadow:
    inset 0 1px 0 rgba(255, 251, 242, 0.82),
    0 10px 22px rgba(85, 58, 29, 0.05);
}

.setup-world-panel__label {
  color: var(--accent-strong);
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1.35;
}

.setup-world-panel__value {
  margin-top: 0.42rem;
  color: var(--ink-strong);
  font-size: 0.9rem;
  line-height: 1.6;
  white-space: pre-wrap;
}

@media (max-width: 720px) {
  .setup-world-panel {
    grid-template-columns: 1fr;
  }
}
</style>
