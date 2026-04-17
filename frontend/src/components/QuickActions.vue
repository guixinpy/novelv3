<template>
  <div v-if="actions.length" class="quick-actions">
    <button
      v-for="a in actions"
      :key="a.type"
      @click="$emit('action', a.type)"
      :disabled="disabled"
      class="quick-actions__button"
    >
      {{ a.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ diagnosis: any; disabled: boolean }>()
defineEmits<{ action: [type: string] }>()

const ACTION_MAP: Record<string, string> = {
  preview_setup: '生成设定',
  preview_storyline: '生成故事线',
  preview_outline: '生成大纲',
}

const actions = computed(() => {
  if (!props.diagnosis) return []
  const items: { type: string; label: string }[] = []
  for (const item of props.diagnosis.missing_items || []) {
    const type = `preview_${item}`
    if (ACTION_MAP[type]) {
      items.push({ type, label: ACTION_MAP[type] })
    }
  }
  return items
})
</script>

<style scoped>
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  padding: 0.95rem 1.25rem 0;
}

.quick-actions__button {
  border: 1px solid rgba(111, 69, 31, 0.14);
  background:
    linear-gradient(180deg, rgba(255, 251, 244, 0.95) 0%, rgba(245, 236, 221, 0.9) 100%);
  color: var(--accent-strong);
  border-radius: 999px;
  padding: 0.5rem 0.95rem;
  font-size: 0.76rem;
  font-weight: 700;
  transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.quick-actions__button:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: rgba(111, 69, 31, 0.28);
  box-shadow: 0 10px 18px rgba(79, 55, 27, 0.1);
}

.quick-actions__button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>
