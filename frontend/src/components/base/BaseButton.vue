<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
    size?: 'sm' | 'md'
    disabled?: boolean
    loading?: boolean
    iconOnly?: boolean
  }>(),
  { variant: 'secondary', size: 'md', disabled: false, loading: false, iconOnly: false },
)
</script>

<template>
  <button
    class="base-button"
    :class="[`base-button--${variant}`, `base-button--${size}`, { 'base-button--icon-only': iconOnly, 'base-button--loading': loading }]"
    :disabled="disabled || loading"
  >
    <span v-if="loading" class="base-button__spinner" aria-hidden="true" />
    <slot />
  </button>
</template>

<style scoped>
.base-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  border-radius: var(--radius-md);
  font-weight: var(--font-medium);
  font-size: var(--text-sm);
  transition: all var(--transition-fast);
  cursor: pointer;
  border: 1px solid transparent;
  white-space: nowrap;
}
.base-button:disabled { opacity: 0.5; cursor: not-allowed; }
.base-button--sm { height: 32px; padding: 0 var(--space-3); }
.base-button--md { height: 36px; padding: 0 var(--space-4); }
.base-button--icon-only.base-button--sm { width: 32px; padding: 0; }
.base-button--icon-only.base-button--md { width: 36px; padding: 0; }
.base-button--primary { background: var(--color-brand); color: var(--color-text-inverse); }
.base-button--primary:hover:not(:disabled) { background: var(--color-brand-hover); }
.base-button--primary:active:not(:disabled) { background: var(--color-brand-active); }
.base-button--secondary { background: transparent; border-color: var(--color-border); color: var(--color-text-primary); }
.base-button--secondary:hover:not(:disabled) { background: var(--color-bg-secondary); }
.base-button--ghost { background: transparent; color: var(--color-text-secondary); }
.base-button--ghost:hover:not(:disabled) { color: var(--color-text-primary); background: var(--color-bg-secondary); }
.base-button--danger { background: transparent; border-color: var(--color-error); color: var(--color-error); }
.base-button--danger:hover:not(:disabled) { background: var(--color-error); color: var(--color-text-inverse); }
.base-button__spinner { width: 14px; height: 14px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; animation: spin 0.6s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
