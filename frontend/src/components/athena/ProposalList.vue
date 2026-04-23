<script setup lang="ts">
import { ref } from 'vue'
import BaseBadge from '../base/BaseBadge.vue'

defineProps<{
  proposals: any
}>()

const expandedId = ref<string | null>(null)

function toggle(id: string) {
  expandedId.value = expandedId.value === id ? null : id
}

const statusVariant: Record<string, 'success' | 'warning' | 'error' | 'neutral'> = {
  draft: 'neutral',
  pending: 'warning',
  approved: 'success',
  rejected: 'error',
}
</script>

<template>
  <div class="proposal-list">
    <div v-if="!proposals?.bundles?.length" class="proposal-list__empty">暂无提案</div>
    <div
      v-for="bundle in (proposals?.bundles || [])"
      :key="bundle.id"
      class="proposal-list__item"
    >
      <button class="proposal-list__header" @click="toggle(bundle.id)">
        <span class="proposal-list__title">{{ bundle.title || bundle.id }}</span>
        <BaseBadge :variant="statusVariant[bundle.status] || 'neutral'" size="sm">
          {{ bundle.status }}
        </BaseBadge>
        <span class="proposal-list__meta">{{ bundle.items?.length || 0 }} 项</span>
        <span class="proposal-list__chevron">{{ expandedId === bundle.id ? '▾' : '▸' }}</span>
      </button>
      <div v-if="expandedId === bundle.id" class="proposal-list__detail">
        <div v-for="(item, i) in (bundle.items || [])" :key="i" class="proposal-list__detail-item">
          {{ item.description || item.content || JSON.stringify(item) }}
        </div>
      </div>
    </div>
  </div>
</template>
<style scoped>
.proposal-list__item {
  border-bottom: 1px solid var(--color-border);
}

.proposal-list__header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-3) 0;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.proposal-list__title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
  flex: 1;
}

.proposal-list__meta {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.proposal-list__chevron {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.proposal-list__detail {
  padding: 0 0 var(--space-3) var(--space-4);
}

.proposal-list__detail-item {
  padding: var(--space-2) 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
}

.proposal-list__detail-item:last-child {
  border-bottom: none;
}

.proposal-list__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
