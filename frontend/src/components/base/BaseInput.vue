<script setup lang="ts">
defineProps<{
  modelValue: string
  label?: string
  placeholder?: string
  error?: string
  disabled?: boolean
  type?: 'text' | 'password' | 'email'
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function onInput(e: Event) {
  emit('update:modelValue', (e.target as HTMLInputElement).value)
}
</script>

<template>
  <div class="base-input">
    <label v-if="label" class="base-input__label">{{ label }}</label>
    <input
      class="base-input__field"
      :class="{ 'base-input__field--error': error }"
      :type="type ?? 'text'"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="onInput"
    />
    <p v-if="error" class="base-input__error">{{ error }}</p>
  </div>
</template>

<style scoped>
.base-input { display: flex; flex-direction: column; }
.base-input__label { font-size: var(--text-sm); font-weight: var(--font-medium); margin-bottom: var(--space-1); color: var(--color-text-primary); }
.base-input__field { height: 36px; padding: 0 var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-md); font-size: var(--text-sm); background: var(--color-bg-white); transition: border-color var(--transition-fast); outline: none; }
.base-input__field:focus { border-color: var(--color-brand); box-shadow: 0 0 0 2px var(--color-brand-subtle); }
.base-input__field--error { border-color: var(--color-error); }
.base-input__field:disabled { opacity: 0.5; cursor: not-allowed; background: var(--color-bg-secondary); }
.base-input__error { font-size: var(--text-xs); color: var(--color-error); margin-top: var(--space-1); }
</style>
