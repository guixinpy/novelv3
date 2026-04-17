<template>
  <div v-if="show" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="$emit('close')">
    <div class="bg-white rounded-lg shadow-xl w-[90vw] max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
      <div class="flex items-center justify-between p-4 border-b">
        <h3 class="text-sm font-semibold text-gray-900">版本对比：v{{ versionA?.version_number }} → v{{ versionB?.version_number }}</h3>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 text-lg">✕</button>
      </div>
      <div class="flex-1 overflow-y-auto p-4">
        <div v-for="(part, i) in diffParts" :key="i" class="font-mono text-xs leading-relaxed">
          <span v-if="part.added" class="bg-green-100 text-green-800">{{ part.value }}</span>
          <span v-else-if="part.removed" class="bg-red-100 text-red-800 line-through">{{ part.value }}</span>
          <span v-else class="text-gray-700">{{ part.value }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { diffLines } from 'diff'

const props = defineProps<{ show: boolean; versionA: any; versionB: any }>()
defineEmits<{ close: [] }>()

const diffParts = computed(() => {
  if (!props.versionA || !props.versionB) return []
  const textA = formatContent(props.versionA.content)
  const textB = formatContent(props.versionB.content)
  return diffLines(textA, textB)
})

function formatContent(content: string): string {
  try {
    const obj = JSON.parse(content)
    return JSON.stringify(obj, null, 2)
  } catch {
    return content
  }
}
</script>
