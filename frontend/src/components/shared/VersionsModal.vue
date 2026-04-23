<script setup lang="ts">
import BaseModal from '../base/BaseModal.vue'
import BaseTable from '../base/BaseTable.vue'
import BaseButton from '../base/BaseButton.vue'
import BaseBadge from '../base/BaseBadge.vue'
import type { BaseTableColumn } from '../base/BaseTable.vue'

defineProps<{
  open: boolean
  versions: any[]
  projectId: string
}>()

const emit = defineEmits<{
  close: []
  filter: [type: string]
  rollback: [versionId: string]
  'delete-version': [versionId: string]
}>()

const columns: BaseTableColumn[] = [
  { key: 'node_type', label: '类型', width: '80px' },
  { key: 'label', label: '标签' },
  { key: 'created_at', label: '创建时间', width: '160px' },
  { key: 'actions', label: '操作', width: '120px', align: 'right' },
]

const typeLabels: Record<string, string> = {
  setup: '设定',
  storyline: '故事线',
  outline: '大纲',
  chapter: '章节',
}

const filterOptions = [
  { value: '', label: '全部' },
  { value: 'setup', label: '设定' },
  { value: 'storyline', label: '故事线' },
  { value: 'outline', label: '大纲' },
  { value: 'chapter', label: '章节' },
]
</script>

<template>
  <BaseModal :open="open" title="版本历史" width="640px" @close="emit('close')">
    <div class="versions-modal__filters">
      <BaseButton
        v-for="opt in filterOptions"
        :key="opt.value"
        variant="ghost"
        size="sm"
        @click="emit('filter', opt.value)"
      >
        {{ opt.label }}
      </BaseButton>
    </div>
    <BaseTable :columns="columns" :data="versions" row-key="id" empty-text="暂无版本记录">
      <template #cell-node_type="{ value }">
        <BaseBadge variant="neutral" size="sm">
          {{ typeLabels[String(value)] || value }}
        </BaseBadge>
      </template>
      <template #cell-actions="{ row }">
        <div class="versions-modal__row-actions">
          <BaseButton variant="ghost" size="sm" @click.stop="emit('rollback', String(row.id))">
            回滚
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click.stop="emit('delete-version', String(row.id))">
            删除
          </BaseButton>
        </div>
      </template>
    </BaseTable>
  </BaseModal>
</template>

<style scoped>
.versions-modal__filters {
  display: flex;
  gap: var(--space-1);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
}

.versions-modal__row-actions {
  display: flex;
  gap: var(--space-1);
  justify-content: flex-end;
}
</style>
