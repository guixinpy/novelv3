<script setup lang="ts">
export interface BaseTableColumn {
  key: string
  label: string
  width?: string
  align?: 'left' | 'center' | 'right'
}

const props = withDefaults(
  defineProps<{
    columns: BaseTableColumn[]
    data: Record<string, unknown>[]
    rowKey?: string
    hoverable?: boolean
    clickable?: boolean
    emptyText?: string
  }>(),
  { rowKey: 'id', hoverable: true, clickable: false, emptyText: '暂无数据' },
)

const emit = defineEmits<{ 'row-click': [row: Record<string, unknown>] }>()

function getRowId(row: Record<string, unknown>, index: number): string {
  const val = row[props.rowKey]
  return val != null ? String(val) : String(index)
}

function getCellValue(row: Record<string, unknown>, key: string): unknown {
  return row[key]
}
</script>

<template>
  <div class="base-table-wrapper">
    <table class="base-table">
      <thead>
        <tr>
          <th v-for="col in columns" :key="col.key" class="base-table__th" :style="{ width: col.width, textAlign: col.align ?? 'left' }">
            {{ col.label }}
          </th>
        </tr>
      </thead>
      <tbody v-if="data.length > 0">
        <tr
          v-for="(row, idx) in data"
          :key="getRowId(row, idx)"
          class="base-table__row"
          :class="{ 'base-table__row--hoverable': hoverable, 'base-table__row--clickable': clickable }"
          @click="clickable ? emit('row-click', row) : undefined"
        >
          <td v-for="col in columns" :key="col.key" class="base-table__td" :style="{ textAlign: col.align ?? 'left' }">
            <slot :name="`cell-${col.key}`" :row="row" :value="getCellValue(row, col.key)">
              {{ getCellValue(row, col.key) ?? '' }}
            </slot>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-if="data.length === 0" class="base-table__empty">{{ emptyText }}</div>
  </div>
</template>

<style scoped>
.base-table-wrapper { width: 100%; }
.base-table { width: 100%; border-collapse: collapse; }
.base-table__th { font-size: var(--text-xs); font-weight: var(--font-semibold); text-transform: uppercase; letter-spacing: 0.05em; color: var(--color-text-tertiary); border-bottom: 1px solid var(--color-border); padding: var(--space-2) var(--space-3); }
.base-table__row { border-bottom: 1px solid var(--color-border); }
.base-table__row--hoverable:hover { background: var(--color-bg-secondary); }
.base-table__row--clickable { cursor: pointer; }
.base-table__td { padding: var(--space-3); font-size: var(--text-sm); color: var(--color-text-primary); }
.base-table__empty { padding: var(--space-12) var(--space-4); text-align: center; color: var(--color-text-tertiary); font-size: var(--text-sm); }
</style>
