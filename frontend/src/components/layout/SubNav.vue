<script setup lang="ts">
defineProps<{ collapsed: boolean }>()
const emit = defineEmits<{ 'toggle-collapse': [] }>()
</script>

<template>
  <aside class="subnav" :class="{ 'subnav--collapsed': collapsed }">
    <div class="subnav__content"><slot /></div>
    <button class="subnav__toggle" :aria-label="collapsed ? '展开侧栏' : '收起侧栏'" @click="emit('toggle-collapse')">
      {{ collapsed ? '›' : '‹' }}
    </button>
  </aside>
</template>

<style scoped>
.subnav {
  grid-area: subnav; width: var(--subnav-width); background: var(--color-bg-primary);
  border-right: 1px solid var(--color-border); display: flex; flex-direction: column;
  overflow: hidden; transition: width var(--transition-normal); position: relative;
}
.subnav--collapsed { width: 0; border-right: none; }
.subnav__content { flex: 1; overflow-y: auto; padding: var(--space-2) 0; }
.subnav--collapsed .subnav__content { visibility: hidden; }
.subnav__toggle {
  position: absolute; top: var(--space-2); right: var(--space-2);
  width: 20px; height: 20px; display: flex; align-items: center; justify-content: center;
  border-radius: var(--radius-sm); color: var(--color-text-tertiary); font-size: var(--text-sm); z-index: 1;
}
.subnav__toggle:hover { background: var(--color-bg-secondary); color: var(--color-text-primary); }
.subnav--collapsed .subnav__toggle { right: -24px; background: var(--color-bg-white); border: 1px solid var(--color-border); }
</style>
