<template>
  <div class="bg-white rounded-lg shadow p-4 mb-3">
    <div class="flex items-start justify-between">
      <div>
        <h3 class="text-base font-semibold text-gray-900">{{ project.name }}</h3>
        <p class="text-sm text-gray-600 mt-1">{{ project.genre }} | {{ project.current_word_count }} 字</p>
      </div>
      <router-link
        :to="`/projects/${project.id}`"
        class="inline-flex items-center rounded-md bg-white border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        查看详情
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ project: any }>()
</script>
