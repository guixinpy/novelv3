<template>
  <div v-if="storyline" class="space-y-4">
    <div v-for="p in (storyline.plotlines || [])" :key="p.name" class="bg-white rounded-lg shadow p-4">
      <div class="flex items-center gap-2 mb-2">
        <span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="typeClass(p.type)">{{ typeLabel(p.type) }}</span>
        <h4 class="text-sm font-semibold text-gray-900">{{ p.name }}</h4>
      </div>
      <div v-if="p.milestones?.length" class="space-y-1 ml-4 border-l-2 border-gray-200 pl-3">
        <div v-for="(m, i) in p.milestones" :key="i" class="text-xs text-gray-600">
          <span class="font-medium">{{ m.chapter_index ? `第${m.chapter_index}章` : m.title || '' }}</span>
          {{ m.event || m.description || '' }}
        </div>
      </div>
    </div>
    <div v-if="storyline.foreshadowing?.length" class="bg-white rounded-lg shadow p-4">
      <h4 class="text-sm font-semibold text-gray-700 mb-2">伏笔</h4>
      <div v-for="f in storyline.foreshadowing" :key="f.hint" class="text-sm text-gray-600 mb-1">
        <span class="font-medium">{{ f.hint }}</span>
        <span class="text-xs text-gray-400 ml-2">第{{ f.planted_chapter }}章埋下{{ f.resolved_chapter ? ` → 第${f.resolved_chapter}章揭示` : '' }}</span>
      </div>
    </div>
  </div>
  <p v-else class="text-gray-500 text-sm p-4">暂无故事线数据。</p>
</template>

<script setup lang="ts">
defineProps<{ storyline: any }>()
function typeClass(t: string) {
  if (t === 'main') return 'bg-indigo-100 text-indigo-700'
  if (t === 'romance') return 'bg-pink-100 text-pink-700'
  return 'bg-gray-100 text-gray-700'
}
function typeLabel(t: string) {
  if (t === 'main') return '主线'
  if (t === 'romance') return '感情线'
  return '支线'
}
</script>
