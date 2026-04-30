<script setup lang="ts">
import { computed } from 'vue'
import type { CatalogNode, CatalogRelation } from './catalogNodeModel'

const props = withDefaults(defineProps<{
  node: CatalogNode | null
  relations: CatalogRelation[]
  pendingCountsAvailable?: boolean
}>(), {
  pendingCountsAvailable: true,
})

const relatedRelations = computed(() => {
  if (!props.node) return []

  return props.relations.filter((relation) =>
    relation.source_ref === props.node?.ref || relation.target_ref === props.node?.ref,
  )
})

const factEntries = computed(() => Object.entries(props.node?.facts || {}))

function formatValue(value: unknown) {
  if (value === null || value === undefined) return '无'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)

  try {
    return JSON.stringify(value, (_key, entry) => typeof entry === 'bigint' ? String(entry) : entry)
  } catch (_error) {
    return String(value)
  }
}
</script>

<template>
  <aside class="catalog-context-rail" aria-label="节点上下文">
    <section class="catalog-context-rail__section">
      <h3>关系摘要</h3>
      <div v-if="!node" class="catalog-context-rail__empty">未选择节点</div>
      <div v-else-if="relatedRelations.length === 0" class="catalog-context-rail__empty">暂无直接关系</div>
      <div v-for="relation in relatedRelations" v-else :key="relation.id || `${relation.source_ref}-${relation.target_ref}-${relation.relation_type}`" class="catalog-context-rail__line">
        <span>{{ relation.source_ref || '未知' }}</span>
        <strong>{{ relation.relation_type || '关联' }}</strong>
        <span>{{ relation.target_ref || '未知' }}</span>
      </div>
    </section>

    <section class="catalog-context-rail__section">
      <h3>时间与叙事</h3>
      <div v-if="node?.presence" class="catalog-context-rail__meta">
        <span>位置</span>
        <strong>{{ node.presence.location_ref || '未知位置' }}</strong>
        <span>状态</span>
        <strong>{{ node.presence.presence_status || '未标注' }}</strong>
      </div>
      <div v-else class="catalog-context-rail__empty">暂无在场信息</div>
    </section>

    <section class="catalog-context-rail__section">
      <h3>真相/认知状态</h3>
      <div v-if="node" class="catalog-context-rail__meta">
        <span>确认事实</span>
        <strong>{{ node.factCount }}</strong>
      </div>
      <div v-if="factEntries.length" class="catalog-context-rail__facts">
        <div v-for="[key, value] in factEntries" :key="key">
          <span>{{ key }}</span>
          <strong>{{ formatValue(value) }}</strong>
        </div>
      </div>
      <div v-else class="catalog-context-rail__empty">暂无事实摘要</div>
    </section>

    <section class="catalog-context-rail__section">
      <h3>待审变更</h3>
      <div v-if="node && props.pendingCountsAvailable" class="catalog-context-rail__meta">
        <span>待审</span>
        <strong>{{ node.pendingCount }}</strong>
      </div>
      <div v-else-if="node" class="catalog-context-rail__empty">计数待接入</div>
      <div v-else class="catalog-context-rail__empty">未选择节点</div>
    </section>
  </aside>
</template>

<style scoped>
.catalog-context-rail {
  min-width: 0;
  overflow: auto;
  border-left: 1px solid var(--color-border);
  padding: var(--space-4);
}

.catalog-context-rail__section {
  padding-bottom: var(--space-4);
  margin-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.catalog-context-rail__section h3 {
  margin-bottom: var(--space-2);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.catalog-context-rail__empty {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.catalog-context-rail__line {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.catalog-context-rail__line strong,
.catalog-context-rail__meta strong,
.catalog-context-rail__facts strong {
  overflow-wrap: anywhere;
  color: var(--color-text-primary);
  font-weight: var(--font-medium);
}

.catalog-context-rail__meta,
.catalog-context-rail__facts {
  display: grid;
  grid-template-columns: minmax(72px, auto) minmax(0, 1fr);
  gap: var(--space-2);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.catalog-context-rail__facts {
  grid-template-columns: minmax(0, 1fr);
  margin-top: var(--space-2);
}

.catalog-context-rail__facts div {
  display: grid;
  gap: var(--space-1);
}
</style>
