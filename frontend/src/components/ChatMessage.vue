<template>
  <div style="margin: 0.5rem 0; text-align: left;">
    <div :style="{ background: msg.role === 'user' ? '#e3f2fd' : '#f5f5f5', padding: '0.75rem', borderRadius: '4px', display: 'inline-block', maxWidth: '80%' }">
      <div style="font-size: 0.75rem; color: #888; margin-bottom: 0.25rem;">{{ msg.role === 'user' ? '我' : '墨舟' }}</div>
      <div style="white-space: pre-wrap;">{{ msg.content }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ msg: any }>()
</script>
