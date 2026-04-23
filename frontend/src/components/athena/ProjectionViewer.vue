<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{
  projection: any
}>()

const expandedEntities = ref<Set<string>>(new Set())

const groups = computed(() => {
  if (!props.projection) return []
  const facts = props.projection.facts || props.projection.entries || []
  const grouped: Record<string, any[]> = {}
  for (const fact of facts) {
    const entity = fact.subject || fact.entity || '未知'
    if (!grouped[entity]) grouped[entity] = []
    grouped[entity].push(fact)
  }
  return Object.entries(grouped).map(([entity, items]) => ({ entity, items }))
})

function toggle(entity: string) {
  if (expandedEntities.value.has(entity)) {
    expandedEntities.value.delete(entity)
  } else {
    expandedEntities.value.add(entity)
  }
}
</script>

<template>
  <div class="projection-viewer">
    <div v-if="groups.length === 0" class="projection-viewer__empty">暂无投影数据</div>
    <div v-for="group in groups" :key="group.entity" class="projection-viewer__group">
      <button class="projection-viewer__header" @click="toggle(group.entity)">
        <span class="projection-viewer__entity">{{ group.entity }}</span>
        <span class="projection-viewer__count">{{ group.items.length }}</span>
        <span class="projection-viewer__chevron">{{ expandedEntities.has(group.entity) ? '▾' : '▸' }}</span>
      </button>
      <div v-if="expandedEntities.has(group.entity)" class="projection-viewer__facts">
        <div v-for="(fact, i) in group.items" :key="i" class="projection-viewer__fact">
          <span class="projection-viewer__predicate">{{ fact.predicate || fact.key || '' }}</span>
          <span class="projection-viewer__value">{{ fact.value || fact.object || '' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>
<style scoped>
.projection-viewer__group {
  border-bottom: 1px solid var(--color-border);
}

.projection-viewer__header {
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

.projection-viewer__entity {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.projection-viewer__count {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  background: var(--color-bg-tertiary);
  padding: 1px 6px;
  border-radius: var(--radius-full);
}

.projection-viewer__chevron {
  margin-left: auto;
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.projection-viewer__facts {
  padding: 0 0 var(--space-3) var(--space-4);
}

.projection-viewer__fact {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-1) 0;
  font-size: var(--text-sm);
}

.projection-viewer__predicate {
  color: var(--color-text-secondary);
  min-width: 100px;
}

.projection-viewer__value {
  color: var(--color-text-primary);
}

.projection-viewer__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
