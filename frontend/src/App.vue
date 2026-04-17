<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from './components/layout/AppShell.vue'

const route = useRoute()

const shellMode = computed<'default' | 'workspace'>(() =>
  route.path.startsWith('/projects/') ? 'workspace' : 'default',
)
</script>

<template>
  <AppShell :mode="shellMode">
    <router-view />
  </AppShell>
</template>
