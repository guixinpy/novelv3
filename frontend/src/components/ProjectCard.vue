<template>
  <div style="border: 1px solid #ddd; padding: 1rem; border-radius: 4px; margin-bottom: 0.5rem;">
    <h3>{{ project.name }}</h3>
    <p style="color: #666;">{{ project.genre }} | {{ project.current_word_count }} 字</p>
    <router-link :to="`/projects/${project.id}`">查看详情</router-link>
  </div>
</template>

<script setup lang="ts">
defineProps<{ project: any }>()
</script>
