<template>
  <section class="bundle-list" data-testid="world-proposal-bundle-list">
    <header class="bundle-list__header">
      <div>
        <p class="bundle-list__eyebrow">Proposal Bundles</p>
        <h3 class="bundle-list__title">待审变更</h3>
      </div>
      <span class="bundle-list__count">{{ bundles.length }} 个</span>
    </header>

    <ul v-if="bundles.length" class="bundle-list__items">
      <li v-for="bundle in bundles" :key="bundle.id">
        <button
          type="button"
          class="bundle-list__item"
          :class="{ 'is-active': bundle.id === selectedBundleId }"
          @click="$emit('select', bundle.id)"
        >
          <strong>{{ bundle.title }}</strong>
          <span>{{ bundle.bundle_status }}</span>
        </button>
      </li>
    </ul>
    <p v-else class="bundle-list__empty">暂无待审 proposal bundle。</p>
  </section>
</template>

<script setup lang="ts">
import type { ProposalBundle } from '../../api/types'

defineProps<{
  bundles: ProposalBundle[]
  selectedBundleId: string | null
}>()

defineEmits<{
  select: [bundleId: string]
}>()
</script>

<style scoped>
.bundle-list {
  display: grid;
  gap: 0.8rem;
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 1rem;
  padding: 1rem;
  background: rgba(250, 245, 236, 0.82);
}

.bundle-list__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.bundle-list__eyebrow {
  margin: 0;
  color: var(--ink-muted);
  font-size: 0.72rem;
}

.bundle-list__title {
  margin: 0.12rem 0 0;
  color: var(--accent-strong);
  font-size: 0.96rem;
}

.bundle-list__count {
  color: var(--ink-muted);
  font-size: 0.76rem;
}

.bundle-list__items {
  display: grid;
  gap: 0.55rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.bundle-list__item {
  width: 100%;
  display: grid;
  gap: 0.15rem;
  text-align: left;
  border: 1px solid rgba(111, 69, 31, 0.12);
  border-radius: 0.85rem;
  padding: 0.75rem 0.85rem;
  background: rgba(255, 252, 246, 0.92);
}

.bundle-list__item strong {
  color: var(--ink-strong);
  font-size: 0.82rem;
}

.bundle-list__item span,
.bundle-list__empty {
  color: var(--ink-muted);
  font-size: 0.76rem;
}

.bundle-list__item.is-active {
  border-color: rgba(118, 74, 27, 0.32);
  box-shadow: inset 0 0 0 1px rgba(118, 74, 27, 0.12);
}
</style>
