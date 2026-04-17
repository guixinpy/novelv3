<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppShell from './components/layout/AppShell.vue'

const route = useRoute()

const pageMeta = computed(() => route.matched[route.matched.length - 1]?.meta ?? {})

const shellMode = computed<'default' | 'workspace'>(() =>
  pageMeta.value.shellMode === 'workspace' ? 'workspace' : 'default',
)

const shellSurface = computed<'panel' | 'none'>(() =>
  pageMeta.value.shellSurface === 'none' ? 'none' : 'panel',
)
</script>

<template>
  <AppShell :mode="shellMode" :surface="shellSurface">
    <router-view />
  </AppShell>
</template>
