<script setup lang="ts">
import BaseTable from '../base/BaseTable.vue'
import type { BaseTableColumn } from '../base/BaseTable.vue'

defineProps<{
  entities: any[]
  entityType?: string
  notice?: string
}>()

const columns: BaseTableColumn[] = [
  { key: 'name', label: '名称', width: '160px' },
  { key: 'type', label: '类型', width: '100px' },
  { key: 'description', label: '描述' },
]
</script>

<template>
  <div class="entity-table">
    <div v-if="notice" class="entity-table__notice">{{ notice }}</div>
    <BaseTable
      :columns="columns"
      :data="entities"
      row-key="id"
      :empty-text="`暂无${entityType || ''}数据`"
    />
  </div>
</template>

<style scoped>
.entity-table__notice {
  padding: var(--space-2) var(--space-3);
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  font-size: var(--text-xs);
}
</style>
