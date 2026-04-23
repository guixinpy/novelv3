<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  projectName?: string
  projects?: { id: string; title: string }[]
}>()

const emit = defineEmits<{
  'select-project': [id: string]
  'navigate-settings': []
}>()

const dropdownOpen = ref(false)
</script>

<template>
  <header class="topbar">
    <div class="topbar__left">
      <router-link to="/" class="topbar__brand">墨舟</router-link>
      <div v-if="projectName" class="topbar__project-selector">
        <button class="topbar__project-btn" @click="dropdownOpen = !dropdownOpen">
          {{ projectName }}
          <span class="topbar__chevron">&#9662;</span>
        </button>
        <div v-if="dropdownOpen && projects?.length" class="topbar__dropdown">
          <button
            v-for="p in projects"
            :key="p.id"
            class="topbar__dropdown-item"
            @click="emit('select-project', p.id); dropdownOpen = false"
          >
            {{ p.title }}
          </button>
        </div>
      </div>
    </div>
    <div class="topbar__right">
      <button class="topbar__icon-btn" aria-label="设置" @click="emit('navigate-settings')">
        &#9881;
      </button>
    </div>
  </header>
</template>

<style scoped>
.topbar {
  grid-area: topbar;
  height: var(--topbar-height);
  background: var(--color-bg-white);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-4);
  z-index: 40;
}
.topbar__left { display: flex; align-items: center; gap: var(--space-4); }
.topbar__brand { font-size: var(--text-lg); font-weight: var(--font-semibold); color: var(--color-brand); }
.topbar__project-selector { position: relative; }
.topbar__project-btn {
  display: flex; align-items: center; gap: var(--space-1);
  font-size: var(--text-sm); color: var(--color-text-primary);
  padding: var(--space-1) var(--space-2); border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}
.topbar__project-btn:hover { background: var(--color-bg-secondary); }
.topbar__chevron { font-size: var(--text-xs); color: var(--color-text-tertiary); }
.topbar__dropdown {
  position: absolute; top: 100%; left: 0; margin-top: var(--space-1);
  background: var(--color-bg-white); border: 1px solid var(--color-border);
  border-radius: var(--radius-md); box-shadow: var(--shadow-md);
  min-width: 200px; z-index: 50; padding: var(--space-1) 0;
}
.topbar__dropdown-item {
  display: block; width: 100%; text-align: left;
  padding: var(--space-2) var(--space-3); font-size: var(--text-sm);
  color: var(--color-text-primary); transition: background var(--transition-fast);
}
.topbar__dropdown-item:hover { background: var(--color-bg-secondary); }
.topbar__right { display: flex; align-items: center; }
.topbar__icon-btn {
  width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
  border-radius: var(--radius-md); color: var(--color-text-secondary);
  font-size: var(--text-lg); transition: all var(--transition-fast);
}
.topbar__icon-btn:hover { background: var(--color-bg-secondary); color: var(--color-text-primary); }
</style>
