<script setup lang="ts">
import type { CatalogRelation } from './catalogNodeModel'

defineProps<{
  relations: CatalogRelation[]
}>()
</script>

<template>
  <section class="catalog-graph-panel">
    <header class="catalog-graph-panel__header">
      <h2>图谱</h2>
      <span>{{ relations.length }} 条关系</span>
    </header>

    <div v-if="relations.length === 0" class="catalog-graph-panel__empty">暂无关系</div>
    <div v-else class="catalog-graph-panel__relations">
      <div v-for="relation in relations" :key="relation.id || `${relation.source_ref}-${relation.target_ref}-${relation.relation_type}`" class="catalog-graph-panel__row">
        <span>{{ relation.source_ref || '未知来源' }}</span>
        <strong>{{ relation.relation_type || '关联' }}</strong>
        <span>{{ relation.target_ref || '未知目标' }}</span>
      </div>
    </div>
  </section>
</template>

<style scoped>
.catalog-graph-panel {
  height: 100%;
  overflow: auto;
  padding: var(--space-5);
}

.catalog-graph-panel__header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.catalog-graph-panel__header h2 {
  color: var(--color-text-primary);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.catalog-graph-panel__header span,
.catalog-graph-panel__empty {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.catalog-graph-panel__empty {
  padding: var(--space-8) 0;
  text-align: center;
}

.catalog-graph-panel__relations {
  display: grid;
}

.catalog-graph-panel__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.catalog-graph-panel__row strong {
  color: var(--color-brand);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}
</style>
