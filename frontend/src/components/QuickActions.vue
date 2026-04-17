<template>
  <div v-if="actions.length" class="flex flex-wrap gap-2 px-4 py-2 border-t border-gray-100 bg-gray-50">
    <button
      v-for="a in actions"
      :key="a.type"
      @click="$emit('action', a.type)"
      :disabled="disabled"
      class="rounded-full bg-white border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-indigo-50 hover:border-indigo-300 hover:text-indigo-700 disabled:opacity-50 transition-colors"
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
