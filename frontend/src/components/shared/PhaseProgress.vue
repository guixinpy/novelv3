<script setup lang="ts">
export interface PhaseItem {
  key: string
  label: string
  status: 'done' | 'current' | 'pending'
}

defineProps<{
  phases: PhaseItem[]
}>()
</script>

<template>
  <div class="phase-progress">
    <div
      v-for="(phase, index) in phases"
      :key="phase.key"
      class="phase-progress__item"
    >
      <div class="phase-progress__indicator">
        <span
          class="phase-progress__dot"
          :class="`phase-progress__dot--${phase.status}`"
        >
          <svg
            v-if="phase.status === 'done'"
            width="10"
            height="10"
            viewBox="0 0 10 10"
            fill="none"
          >
            <path
              d="M2 5L4.5 7.5L8 3"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round"
            />
          </svg>
        </span>
        <div
          v-if="index < phases.length - 1"
          class="phase-progress__line"
          :class="{
            'phase-progress__line--done': phase.status === 'done',
          }"
        />
      </div>
      <span
        class="phase-progress__label"
        :class="`phase-progress__label--${phase.status}`"
      >
        {{ phase.label }}
      </span>
      <span v-if="phase.status === 'current'" class="phase-progress__arrow">→</span>
    </div>
  </div>
</template>

<style scoped>
.phase-progress {
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: var(--space-3);
}

.phase-progress__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 32px;
}

.phase-progress__indicator {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 16px;
  flex-shrink: 0;
}

.phase-progress__dot {
  width: 12px;
  height: 12px;
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.phase-progress__dot--done {
  background: var(--color-success);
  color: var(--color-text-inverse);
}

.phase-progress__dot--current {
  background: var(--color-brand);
  box-shadow: 0 0 0 3px var(--color-brand-subtle);
  animation: pulse-dot 2s ease-in-out infinite;
}

.phase-progress__dot--pending {
  background: transparent;
  border: 2px solid var(--color-border-strong);
}

.phase-progress__line {
  width: 2px;
  height: 16px;
  background: var(--color-border);
}

.phase-progress__line--done {
  background: var(--color-success);
}

.phase-progress__label {
  font-size: var(--text-sm);
  flex: 1;
}

.phase-progress__label--done {
  color: var(--color-text-secondary);
}

.phase-progress__label--current {
  color: var(--color-brand);
  font-weight: var(--font-medium);
}

.phase-progress__label--pending {
  color: var(--color-text-tertiary);
}

.phase-progress__arrow {
  color: var(--color-brand);
  font-size: var(--text-sm);
}

@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 3px var(--color-brand-subtle); }
  50% { box-shadow: 0 0 0 5px var(--color-brand-subtle); }
}
</style>
