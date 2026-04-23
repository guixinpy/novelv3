<script setup lang="ts">
defineProps<{
  knowledge: any
}>()
</script>

<template>
  <div class="knowledge-viewer">
    <div v-if="!knowledge" class="knowledge-viewer__empty">暂无主体认知数据</div>
    <template v-else>
      <div
        v-for="(subject, key) in (knowledge.subjects || knowledge)"
        :key="String(key)"
        class="knowledge-viewer__subject"
      >
        <h4 class="knowledge-viewer__name">{{ typeof key === 'string' ? key : subject.name || '' }}</h4>
        <div
          v-for="(item, i) in (subject.beliefs || subject.items || [])"
          :key="i"
          class="knowledge-viewer__item"
          :class="{ 'knowledge-viewer__item--discrepancy': item.discrepancy }"
        >
          <span class="knowledge-viewer__belief">{{ item.belief || item.content || '' }}</span>
          <span v-if="item.ground_truth" class="knowledge-viewer__truth">真相: {{ item.ground_truth }}</span>
        </div>
      </div>
    </template>
  </div>
</template>
<style scoped>
.knowledge-viewer__subject {
  margin-bottom: var(--space-4);
}

.knowledge-viewer__name {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.knowledge-viewer__item {
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-sm);
  border-bottom: 1px solid var(--color-border);
}

.knowledge-viewer__item--discrepancy {
  background: var(--color-warning-light);
}

.knowledge-viewer__belief {
  color: var(--color-text-primary);
}

.knowledge-viewer__truth {
  display: block;
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-warning);
}

.knowledge-viewer__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
