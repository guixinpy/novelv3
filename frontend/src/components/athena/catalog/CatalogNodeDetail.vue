<script setup lang="ts">
import { computed } from 'vue'
import type { CatalogNode } from './catalogNodeModel'

const props = withDefaults(defineProps<{
  node: CatalogNode | null
  pendingCountsAvailable?: boolean
}>(), {
  pendingCountsAvailable: true,
})

const typeLabels: Record<CatalogNode['type'], string> = {
  characters: '角色',
  locations: '地点',
  factions: '势力',
  items: '物品',
  resources: '资源',
  concepts: '概念',
}

const fieldEntries = computed(() => Object.entries(props.node?.raw || {}))
const factEntries = computed(() => Object.entries(props.node?.facts || {}))

const summaryRows = computed(() => {
  const raw = props.node?.raw || {}

  return [
    { label: '定位', value: firstPresent(raw, ['role_type', 'location_type', 'faction_type', 'artifact_type', 'resource_type', 'rule_type', 'type']) },
    { label: '动机/目标', value: firstPresent(raw, ['core_drives', 'mission_or_doctrine', 'function_summary']) },
    { label: '限制/危险', value: firstPresent(raw, ['core_fears', 'hazards', 'usage_constraints', 'constraints']) },
    { label: '隐藏信息', value: firstPresent(raw, ['hidden_truths', 'hidden_agenda', 'risk_or_side_effects']) },
  ]
})

function firstPresent(record: Record<string, unknown>, keys: string[]) {
  for (const key of keys) {
    if (record[key] !== undefined && record[key] !== null && record[key] !== '') return record[key]
  }

  return null
}

function formatValue(value: unknown, seen = new WeakSet<object>()): string {
  if (value === null || value === undefined) return '无'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  if (Array.isArray(value)) return value.map((item) => formatValue(item, seen)).join('、') || '无'
  if (typeof value === 'object') {
    if (seen.has(value)) return '[Circular]'

    seen.add(value)
    try {
      return JSON.stringify(value, (_key, entry) => typeof entry === 'bigint' ? String(entry) : entry)
    } catch (_error) {
      return String(value)
    }
  }

  return String(value)
}
</script>

<template>
  <section class="catalog-node-detail">
    <div v-if="!node" class="catalog-node-detail__empty">选择一个节点查看完整信息</div>
    <template v-else>
      <header class="catalog-node-detail__header">
        <div>
          <div class="catalog-node-detail__eyebrow">{{ typeLabels[node.type] }} / {{ node.ref }}</div>
          <h2 class="catalog-node-detail__title">{{ node.label }}</h2>
          <div v-if="node.aliases.length" class="catalog-node-detail__aliases">
            <span v-for="alias in node.aliases" :key="alias">{{ alias }}</span>
          </div>
        </div>
        <div class="catalog-node-detail__badges">
          <span>事实 {{ node.factCount }}</span>
          <span>关系 {{ node.relationCount }}</span>
          <span v-if="props.pendingCountsAvailable">待审 {{ node.pendingCount }}</span>
        </div>
      </header>

      <section class="catalog-node-detail__section">
        <h3>完整节点信息</h3>
        <div class="catalog-node-detail__summary">
          <div v-for="row in summaryRows" :key="row.label" class="catalog-node-detail__summary-row">
            <span>{{ row.label }}</span>
            <strong>{{ formatValue(row.value) }}</strong>
          </div>
        </div>
      </section>

      <section class="catalog-node-detail__section">
        <h3>创作理解</h3>
        <div class="catalog-node-detail__field-grid">
          <div v-for="[key, value] in fieldEntries" :key="key" class="catalog-node-detail__field">
            <span>{{ key }}</span>
            <strong>{{ formatValue(value) }}</strong>
          </div>
        </div>
      </section>

      <section class="catalog-node-detail__section">
        <h3>事实账本</h3>
        <div v-if="factEntries.length === 0" class="catalog-node-detail__empty-line">暂无确认事实</div>
        <div v-else class="catalog-node-detail__field-grid">
          <div v-for="[key, value] in factEntries" :key="key" class="catalog-node-detail__field">
            <span>{{ key }}</span>
            <strong>{{ formatValue(value) }}</strong>
          </div>
        </div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.catalog-node-detail {
  min-width: 0;
  overflow: auto;
  padding: var(--space-4) var(--space-5);
}

.catalog-node-detail__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.catalog-node-detail__header {
  display: flex;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.catalog-node-detail__eyebrow {
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}

.catalog-node-detail__title {
  margin-top: var(--space-1);
  color: var(--color-text-primary);
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  line-height: var(--leading-tight);
}

.catalog-node-detail__aliases,
.catalog-node-detail__badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.catalog-node-detail__aliases {
  margin-top: var(--space-2);
}

.catalog-node-detail__aliases span,
.catalog-node-detail__badges span {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.catalog-node-detail__section {
  padding: var(--space-4) 0;
  border-bottom: 1px solid var(--color-border);
}

.catalog-node-detail__section h3 {
  margin-bottom: var(--space-3);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.catalog-node-detail__summary,
.catalog-node-detail__field-grid {
  display: grid;
  gap: var(--space-2);
}

.catalog-node-detail__summary {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.catalog-node-detail__summary-row,
.catalog-node-detail__field {
  min-width: 0;
  border-left: 2px solid var(--color-border);
  padding-left: var(--space-3);
}

.catalog-node-detail__summary-row span,
.catalog-node-detail__field span {
  display: block;
  margin-bottom: var(--space-1);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.catalog-node-detail__summary-row strong,
.catalog-node-detail__field strong {
  display: block;
  overflow-wrap: anywhere;
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-normal);
  line-height: var(--leading-normal);
}

.catalog-node-detail__empty-line {
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

@media (max-width: 720px) {
  .catalog-node-detail__header,
  .catalog-node-detail__summary {
    grid-template-columns: minmax(0, 1fr);
  }

  .catalog-node-detail__header {
    display: grid;
  }
}
</style>
