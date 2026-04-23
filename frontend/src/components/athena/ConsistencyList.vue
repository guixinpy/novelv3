<script setup lang="ts">
import { ref } from 'vue'
import BaseBadge from '../base/BaseBadge.vue'

defineProps<{
  issues: any[]
}>()

const expandedIdx = ref<number | null>(null)

function toggle(idx: number) {
  expandedIdx.value = expandedIdx.value === idx ? null : idx
}

const severityVariant: Record<string, 'success' | 'warning' | 'error' | 'neutral'> = {
  pass: 'success',
  warning: 'warning',
  error: 'error',
  info: 'neutral',
}
</script>

<template>
  <div class="consistency-list">
    <div v-if="issues.length === 0" class="consistency-list__empty">暂无一致性检查结果</div>
    <div
      v-for="(issue, idx) in issues"
      :key="idx"
      class="consistency-list__item"
    >
      <button class="consistency-list__header" @click="toggle(idx)">
        <BaseBadge :variant="severityVariant[issue.severity || issue.status] || 'neutral'" size="sm">
          {{ issue.severity || issue.status || 'info' }}
        </BaseBadge>
        <span class="consistency-list__type">{{ issue.check_type || issue.type || '' }}</span>
        <span class="consistency-list__desc">{{ issue.description || issue.message || '' }}</span>
        <span class="consistency-list__chevron">{{ expandedIdx === idx ? '▾' : '▸' }}</span>
      </button>
      <div v-if="expandedIdx === idx && issue.evidence" class="consistency-list__evidence">
        {{ typeof issue.evidence === 'string' ? issue.evidence : JSON.stringify(issue.evidence) }}
      </div>
    </div>
  </div>
</template>
<style scoped>
.consistency-list__item {
  border-bottom: 1px solid var(--color-border);
}

.consistency-list__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-3) 0;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.consistency-list__type {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  min-width: 80px;
}

.consistency-list__desc {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  flex: 1;
}

.consistency-list__chevron {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.consistency-list__evidence {
  padding: var(--space-2) var(--space-4) var(--space-3);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-2);
}

.consistency-list__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
