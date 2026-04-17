<script setup lang="ts">
import { computed } from 'vue'
import AppTopNav from './AppTopNav.vue'

type ShellMode = 'default' | 'workspace'
type ShellSurface = 'panel' | 'none'

const props = withDefaults(
  defineProps<{
    mode?: ShellMode
    surface?: ShellSurface
  }>(),
  {
    mode: 'default',
    surface: 'panel',
  },
)

const containerClass = computed(() =>
  props.mode === 'workspace'
    ? 'app-shell__container app-shell__container--workspace'
    : 'app-shell__container app-shell__container--default',
)
</script>

<template>
  <div class="app-shell">
    <AppTopNav />
    <main class="app-shell__viewport">
      <div :class="containerClass">
        <section v-if="surface === 'panel'" class="app-shell__surface">
          <slot />
        </section>
        <slot v-else />
      </div>
    </main>
  </div>
</template>
