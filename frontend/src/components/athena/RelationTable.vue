<script setup lang="ts">
import BaseTable from '../base/BaseTable.vue'
import type { BaseTableColumn } from '../base/BaseTable.vue'

defineProps<{
  relations: any[]
}>()

const columns: BaseTableColumn[] = [
  { key: 'source', label: '源实体', width: '160px' },
  { key: 'arrow', label: '', width: '40px', align: 'center' },
  { key: 'relation_type', label: '关系类型', width: '120px' },
  { key: 'target', label: '目标实体', width: '160px' },
]
</script>

<template>
  <BaseTable :columns="columns" :data="relations" row-key="id" empty-text="暂无关系数据">
    <template #cell-arrow>
      <span class="relation-arrow">→</span>
    </template>
  </BaseTable>
</template>

<style scoped>
.relation-arrow {
  color: var(--color-text-tertiary);
}
</style>
