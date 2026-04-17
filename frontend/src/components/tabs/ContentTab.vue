<template>
  <div v-if="chapters.length" class="space-y-2">
    <div v-for="ch in chapters" :key="ch.id" class="bg-white rounded-lg shadow p-3 cursor-pointer hover:bg-gray-50" @click="$emit('select-chapter', ch.chapter_index)">
      <div class="flex items-center justify-between">
        <h4 class="text-sm font-medium text-gray-900">{{ ch.title }}</h4>
        <span class="text-xs text-gray-500">{{ ch.word_count }} 字</span>
      </div>
    </div>
    <div v-if="selectedChapter" class="bg-white rounded-lg shadow p-4 mt-4">
      <h3 class="text-base font-semibold text-gray-900 mb-2">{{ selectedChapter.title }}</h3>
      <div class="prose prose-sm max-w-none text-gray-800 whitespace-pre-wrap">{{ selectedChapter.content }}</div>
    </div>
  </div>
  <p v-else class="text-gray-500 text-sm p-4">暂无章节内容。</p>
</template>

<script setup lang="ts">
defineProps<{ chapters: any[]; selectedChapter: any }>()
defineEmits<{ 'select-chapter': [index: number] }>()
</script>
