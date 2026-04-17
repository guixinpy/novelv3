<template>
  <div class="space-y-4">
    <div class="bg-white rounded-lg shadow p-4">
      <h3 class="text-lg font-semibold text-gray-900">{{ project.name }}</h3>
      <p class="text-sm text-gray-500 mt-1">{{ project.genre }} | {{ project.current_word_count }} 字 | {{ project.status }}</p>
    </div>
    <div class="bg-white rounded-lg shadow p-4">
      <h4 class="text-sm font-semibold text-gray-700 mb-2">项目进度</h4>
      <div class="flex flex-wrap gap-2">
        <span v-for="item in completed" :key="item" class="rounded-full bg-green-100 text-green-700 px-3 py-1 text-xs">{{ labels[item] || item }} ✓</span>
        <span v-for="item in missing" :key="item" class="rounded-full bg-gray-100 text-gray-500 px-3 py-1 text-xs">{{ labels[item] || item }}</span>
      </div>
    </div>
    <div class="flex gap-2">
      <button @click="$emit('export', 'markdown')" class="rounded-md bg-white border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">导出 Markdown</button>
      <button @click="$emit('export', 'txt')" class="rounded-md bg-white border border-gray-300 px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50">导出 TXT</button>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ project: any; completed: string[]; missing: string[] }>()
defineEmits<{ export: [format: string] }>()
const labels: Record<string, string> = { setup: '设定', storyline: '故事线', outline: '大纲', content: '正文' }
</script>
