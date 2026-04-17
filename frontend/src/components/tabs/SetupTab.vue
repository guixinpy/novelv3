<template>
  <div v-if="setup" class="space-y-4">
    <div class="bg-white rounded-lg shadow p-4">
      <h4 class="text-sm font-semibold text-gray-700 mb-2">角色</h4>
      <div v-for="c in (setup.characters || [])" :key="c.name" class="border border-gray-200 rounded-md p-3 mb-2">
        <p class="font-medium text-gray-900">{{ c.name }}</p>
        <p class="text-sm text-gray-600 mt-1">{{ c.description || c.role || '' }}</p>
      </div>
    </div>
    <div v-if="setup.world_building" class="bg-white rounded-lg shadow p-4">
      <h4 class="text-sm font-semibold text-gray-700 mb-2">世界观</h4>
      <pre class="text-sm text-gray-800 whitespace-pre-wrap">{{ JSON.stringify(setup.world_building, null, 2) }}</pre>
    </div>
    <div v-if="setup.core_concept" class="bg-white rounded-lg shadow p-4">
      <h4 class="text-sm font-semibold text-gray-700 mb-2">核心概念</h4>
      <pre class="text-sm text-gray-800 whitespace-pre-wrap">{{ JSON.stringify(setup.core_concept, null, 2) }}</pre>
    </div>
  </div>
  <p v-else class="text-gray-500 text-sm p-4">暂无设定数据。</p>
</template>

<script setup lang="ts">
defineProps<{ setup: any }>()
</script>
