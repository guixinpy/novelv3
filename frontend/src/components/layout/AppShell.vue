<script setup lang="ts">
import { computed } from 'vue'
import AppTopNav from './AppTopNav.vue'

type ShellMode = 'default' | 'workspace'

const props = withDefaults(
  defineProps<{
    mode?: ShellMode
  }>(),
  {
    mode: 'default',
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
        <section class="app-shell__surface">
          <slot />
        </section>
      </div>
    </main>
  </div>
</template>
