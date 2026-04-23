<script setup lang="ts">
import BaseTable from '../base/BaseTable.vue'
import type { BaseTableColumn } from '../base/BaseTable.vue'

defineProps<{
  entities: any[]
  entityType?: string
}>()

const columns: BaseTableColumn[] = [
  { key: 'name', label: '名称', width: '160px' },
  { key: 'type', label: '类型', width: '100px' },
  { key: 'description', label: '描述' },
]
</script>

<template>
  <BaseTable
    :columns="columns"
    :data="entities"
    row-key="id"
    :empty-text="`暂无${entityType || ''}数据`"
  />
</template>
