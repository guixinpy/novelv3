<template>
  <div class="flex flex-col gap-1">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      @click="$emit('select', tab.id)"
      class="text-left px-3 py-2 rounded-md text-sm transition-colors"
      :class="active === tab.id ? 'bg-indigo-100 text-indigo-700 font-medium' : 'text-gray-600 hover:bg-gray-100'"
    >
      {{ tab.label }}
    </button>
  </div>
</template>

<script setup lang="ts">
defineProps<{ active: string; tabs: { id: string; label: string }[] }>()
defineEmits<{ select: [id: string] }>()
</script>
