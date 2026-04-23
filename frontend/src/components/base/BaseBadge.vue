<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'success' | 'warning' | 'error' | 'neutral'
    size?: 'sm' | 'md'
  }>(),
  { variant: 'neutral', size: 'sm' },
)
</script>

<template>
  <span class="base-badge" :class="[`base-badge--${variant}`, `base-badge--${size}`]">
    <slot />
  </span>
</template>

<style scoped>
.base-badge { display: inline-flex; align-items: center; border-radius: var(--radius-full); font-size: var(--text-xs); font-weight: var(--font-medium); white-space: nowrap; }
.base-badge--sm { padding: 2px 8px; }
.base-badge--md { padding: 4px 10px; }
.base-badge--success { background: var(--color-success-light); color: var(--color-success); }
.base-badge--warning { background: var(--color-warning-light); color: var(--color-warning); }
.base-badge--error { background: var(--color-error-light); color: var(--color-error); }
.base-badge--neutral { background: var(--color-bg-tertiary); color: var(--color-text-secondary); }
</style>
