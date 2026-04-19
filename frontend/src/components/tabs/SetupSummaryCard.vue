<template>
  <article class="setup-summary-card" :data-testid="testId">
    <header class="setup-summary-card__header">
      <div class="setup-summary-card__heading">
        <h4 class="setup-summary-card__title">{{ title }}</h4>
        <p v-if="description" class="setup-summary-card__description">{{ description }}</p>
      </div>
      <button
        type="button"
        class="setup-summary-card__action"
        data-testid="setup-summary-open"
        @click="$emit('open')"
      >
        查看完整
      </button>
    </header>
    <div class="setup-summary-card__body" :data-testid="bodyTestId">
      <slot />
    </div>
  </article>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  testId: string
  bodyTestId?: string
  description?: string
}>()

defineEmits<{
  open: []
}>()
</script>

<style scoped>
.setup-summary-card {
  display: grid;
  gap: 0.9rem;
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 1rem;
  padding: 1rem;
  background:
    linear-gradient(180deg, rgba(252, 249, 241, 0.96) 0%, rgba(245, 238, 225, 0.92) 100%);
  box-shadow:
    0 10px 24px rgba(85, 58, 29, 0.07),
    inset 0 1px 0 rgba(255, 251, 242, 0.82);
}

.setup-summary-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
}

.setup-summary-card__heading {
  display: grid;
  gap: 0.2rem;
}

.setup-summary-card__title {
  color: var(--accent-strong);
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.3;
}

.setup-summary-card__description {
  color: var(--ink-muted);
  font-size: 0.78rem;
  line-height: 1.4;
}

.setup-summary-card__action {
  border: 1px solid rgba(111, 69, 31, 0.18);
  border-radius: 999px;
  background: rgba(255, 252, 246, 0.9);
  color: var(--accent-strong);
  padding: 0.38rem 0.72rem;
  font-size: 0.78rem;
  font-weight: 700;
  white-space: nowrap;
}

.setup-summary-card__body {
  min-width: 0;
}
</style>
