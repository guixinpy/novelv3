<template>
  <div class="space-y-3 overflow-y-auto">
    <div class="bg-white rounded-lg shadow p-3">
      <h3 class="text-sm font-semibold text-gray-900">{{ project.name }}</h3>
      <p class="text-xs text-gray-500 mt-1">{{ project.genre }} | {{ project.current_word_count }} 字</p>
      <div class="mt-2 flex flex-wrap gap-1">
        <span
          v-for="item in completedItems"
          :key="item"
          class="inline-block rounded-full bg-green-100 text-green-700 px-2 py-0.5 text-xs"
        >
          {{ ITEM_LABELS[item] || item }} ✓
        </span>
        <span
          v-for="item in missingItems"
          :key="item"
          class="inline-block rounded-full bg-gray-100 text-gray-500 px-2 py-0.5 text-xs"
        >
          {{ ITEM_LABELS[item] || item }}
        </span>
      </div>
    </div>

    <div v-if="setup" class="bg-white rounded-lg shadow p-3">
      <h4 class="text-xs font-semibold text-gray-700 mb-1">设定摘要</h4>
      <p v-if="setup.characters?.length" class="text-xs text-gray-600">
        角色：{{ setup.characters.map((c: any) => c.name).join('、') }}
      </p>
    </div>

    <div v-if="storyline" class="bg-white rounded-lg shadow p-3">
      <h4 class="text-xs font-semibold text-gray-700 mb-1">故事线</h4>
      <div v-for="p in (storyline.plotlines || []).slice(0, 3)" :key="p.name" class="text-xs text-gray-600">
        {{ p.type === 'main' ? '主线' : '支线' }}：{{ p.name }}
      </div>
    </div>

    <div v-if="outline" class="bg-white rounded-lg shadow p-3">
      <h4 class="text-xs font-semibold text-gray-700 mb-1">大纲 ({{ outline.total_chapters }} 章)</h4>
      <div v-for="ch in (outline.chapters || []).slice(0, 5)" :key="ch.chapter_index" class="text-xs text-gray-600 truncate">
        {{ ch.chapter_index }}. {{ ch.title }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  project: any
  setup: any
  storyline: any
  outline: any
  completedItems: string[]
  missingItems: string[]
}>()

const ITEM_LABELS: Record<string, string> = {
  setup: '设定',
  storyline: '故事线',
  outline: '大纲',
  content: '正文',
}
</script>
