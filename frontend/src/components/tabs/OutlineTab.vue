<template>
  <div v-if="outline && outline.chapters?.length" class="space-y-2">
    <p class="text-sm text-gray-500 mb-2">共 {{ outline.total_chapters }} 章</p>
    <div v-for="ch in outline.chapters" :key="ch.chapter_index" class="bg-white rounded-lg shadow p-3">
      <div class="flex items-start justify-between">
        <div>
          <h4 class="text-sm font-medium text-gray-900">{{ ch.chapter_index }}. {{ ch.title }}</h4>
          <p class="text-xs text-gray-600 mt-1">{{ ch.summary }}</p>
        </div>
      </div>
      <div v-if="ch.characters?.length" class="mt-2 flex flex-wrap gap-1">
        <span v-for="c in ch.characters" :key="c" class="rounded-full bg-blue-50 text-blue-700 px-2 py-0.5 text-xs">{{ c }}</span>
      </div>
    </div>
  </div>
  <p v-else class="text-gray-500 text-sm p-4">暂无大纲数据。</p>
</template>

<script setup lang="ts">
defineProps<{ outline: any }>()
</script>
