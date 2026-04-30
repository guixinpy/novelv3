<script setup lang="ts">
import type { AthenaNodeTypeFilter } from '../../../views/athenaNavigation'
import type { CatalogNode } from './catalogNodeModel'

defineProps<{
  nodes: CatalogNode[]
  nodeType: AthenaNodeTypeFilter
  selectedRef: string | null
  search: string
}>()

const emit = defineEmits<{
  select: [nodeRef: string]
  filterType: [nodeType: AthenaNodeTypeFilter]
  updateSearch: [search: string]
}>()

const typeFilters: Array<{ value: AthenaNodeTypeFilter; label: string }> = [
  { value: 'all', label: '全部' },
  { value: 'characters', label: '角色' },
  { value: 'locations', label: '地点' },
  { value: 'factions', label: '势力' },
  { value: 'items', label: '物品' },
  { value: 'resources', label: '资源' },
  { value: 'concepts', label: '概念' },
]

function selectNode(nodeRef: string) {
  emit('select', nodeRef)
}

function updateFilter(nodeType: AthenaNodeTypeFilter) {
  emit('filterType', nodeType)
}

function updateSearch(event: Event) {
  emit('updateSearch', (event.target as HTMLInputElement).value)
}
</script>

<template>
  <aside class="catalog-node-list" aria-label="设定节点">
    <div class="catalog-node-list__filters">
      <button
        v-for="filter in typeFilters"
        :key="filter.value"
        type="button"
        class="catalog-node-list__filter"
        :class="{ 'catalog-node-list__filter--active': filter.value === nodeType }"
        :aria-pressed="filter.value === nodeType"
        @click="updateFilter(filter.value)"
      >
        {{ filter.label }}
      </button>
    </div>

    <label class="catalog-node-list__search">
      <span>搜索</span>
      <input :value="search" type="search" placeholder="名称 / ref / 事实" @input="updateSearch" />
    </label>

    <div v-if="nodes.length === 0" class="catalog-node-list__empty">暂无匹配节点</div>
    <button
      v-for="node in nodes"
      :key="node.ref"
      type="button"
      class="catalog-node-list__item"
      :class="{ 'catalog-node-list__item--active': node.ref === selectedRef }"
      :aria-current="node.ref === selectedRef ? 'true' : undefined"
      @click="selectNode(node.ref)"
    >
      <span class="catalog-node-list__label">{{ node.label }}</span>
      <span class="catalog-node-list__ref">{{ node.ref }}</span>
      <span class="catalog-node-list__stats">
        事实 {{ node.factCount }} / 关系 {{ node.relationCount }} / 待审 {{ node.pendingCount }}
      </span>
    </button>
  </aside>
</template>

<style scoped>
.catalog-node-list {
  min-width: 0;
  overflow: auto;
  border-right: 1px solid var(--color-border);
  padding: var(--space-4);
}

.catalog-node-list__filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.catalog-node-list__filter {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2);
  background: var(--color-bg-white);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}

.catalog-node-list__filter--active {
  border-color: var(--color-brand);
  background: var(--color-brand-light);
  color: var(--color-brand-active);
  font-weight: var(--font-semibold);
}

.catalog-node-list__search {
  display: grid;
  gap: var(--space-1);
  margin-bottom: var(--space-3);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.catalog-node-list__search input {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-2);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.catalog-node-list__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.catalog-node-list__item {
  display: grid;
  gap: var(--space-1);
  width: 100%;
  border: 0;
  border-bottom: 1px solid var(--color-border);
  padding: var(--space-3) 0;
  background: transparent;
  text-align: left;
}

.catalog-node-list__item--active {
  border-color: var(--color-brand-subtle);
}

.catalog-node-list__item--active .catalog-node-list__label {
  color: var(--color-brand-active);
}

.catalog-node-list__label {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.catalog-node-list__ref,
.catalog-node-list__stats {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}
</style>
