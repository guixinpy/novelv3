<template>
  <section
    class="bundle-list"
    data-testid="world-proposal-bundle-list"
  >
    <header class="bundle-list__header">
      <div>
        <p class="bundle-list__eyebrow">
          提案包
        </p>
        <h3 class="bundle-list__title">
          待审变更
        </h3>
      </div>
      <span class="bundle-list__count">{{ loading ? '读取中' : `${total} 个` }}</span>
    </header>

    <div class="bundle-list__filters">
      <select :value="filters.bundle_status || ''" @change="onFilterChange('bundle_status', $event)">
        <option value="">提案包状态：全部</option>
        <option value="pending">待审</option>
        <option value="partially_approved">部分通过</option>
        <option value="approved">已通过</option>
        <option value="rejected">已驳回</option>
        <option value="uncertain">不确定</option>
        <option value="rolled_back">已回滚</option>
        <option value="split">已拆分</option>
      </select>
      <select :value="filters.item_status || ''" @change="onFilterChange('item_status', $event)">
        <option value="">条目状态：全部</option>
        <option value="pending">待审</option>
        <option value="needs_edit">需编辑</option>
        <option value="approved">已通过</option>
        <option value="approved_with_edits">编辑后通过</option>
        <option value="rejected">已驳回</option>
        <option value="uncertain">不确定</option>
        <option value="rolled_back">已回滚</option>
        <option value="split">已拆分</option>
      </select>
      <button v-if="hasActiveFilters" type="button" class="bundle-list__clear" @click="clearFilters">清除筛选</button>
    </div>

    <p
      v-if="loading && bundles.length === 0"
      class="bundle-list__empty"
    >
      正在加载提案包...
    </p>
    <ul
      v-else-if="bundles.length"
      class="bundle-list__items"
    >
      <li
        v-for="bundle in bundles"
        :key="bundle.id"
      >
        <button
          type="button"
          class="bundle-list__item"
          :class="{ 'is-active': bundle.id === selectedBundleId }"
          @click="$emit('select', bundle.id)"
        >
          <strong>{{ bundle.title }}</strong>
          <span>{{ statusLabel(bundle.bundle_status) }}</span>
        </button>
      </li>
    </ul>
    <p
      v-else
      class="bundle-list__empty"
    >
      暂无待审提案包。
    </p>

    <button
      v-if="bundles.length < total"
      type="button"
      class="bundle-list__load-more"
      :disabled="loadingMore"
      @click="$emit('loadMore')"
    >
      {{ loadingMore ? '加载中...' : `加载更多 (${bundles.length}/${total})` }}
    </button>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ProposalBundle } from '../../api/types'

const props = defineProps<{
  bundles: ProposalBundle[]
  selectedBundleId: string | null
  total: number
  filters: { bundle_status?: string; item_status?: string; profile_version?: number }
  loading?: boolean
  loadingMore?: boolean
}>()

const emit = defineEmits<{
  select: [bundleId: string]
  loadMore: []
  updateFilters: [filters: { bundle_status?: string; item_status?: string; profile_version?: number }]
}>()

const hasActiveFilters = computed(() =>
  Boolean(props.filters.bundle_status || props.filters.item_status || props.filters.profile_version),
)

function onFilterChange(key: string, event: Event) {
  const value = (event.target as HTMLSelectElement).value
  const next = { ...props.filters, [key]: value || undefined }
  emit('updateFilters', next)
}

function clearFilters() {
  emit('updateFilters', {})
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '待审',
    partially_approved: '部分通过',
    approved: '已通过',
    rejected: '已驳回',
    uncertain: '不确定',
    rolled_back: '已回滚',
    split: '已拆分',
  }
  return labels[status] || status
}
</script>

<style scoped>
.bundle-list {
  display: grid;
  gap: 0.8rem;
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 1rem;
  padding: 1rem;
  background: rgba(250, 245, 236, 0.82);
}

.bundle-list__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.bundle-list__eyebrow {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 0.72rem;
}

.bundle-list__title {
  margin: 0.12rem 0 0;
  color: var(--accent-strong);
  font-size: 0.96rem;
}

.bundle-list__count {
  color: var(--color-text-secondary);
  font-size: 0.76rem;
}

.bundle-list__filters {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  align-items: center;
}

.bundle-list__filters select {
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 0.6rem;
  padding: 0.35rem 0.55rem;
  background: rgba(255, 252, 246, 0.92);
  color: var(--color-text-primary);
  font-size: 0.74rem;
}

.bundle-list__clear {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--accent-strong);
  font-size: 0.74rem;
  cursor: pointer;
}

.bundle-list__items {
  display: grid;
  gap: 0.55rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.bundle-list__item {
  width: 100%;
  display: grid;
  gap: 0.15rem;
  text-align: left;
  border: 1px solid rgba(111, 69, 31, 0.12);
  border-radius: 0.85rem;
  padding: 0.75rem 0.85rem;
  background: rgba(255, 252, 246, 0.92);
}

.bundle-list__item strong {
  color: var(--color-text-primary);
  font-size: 0.82rem;
}

.bundle-list__item span,
.bundle-list__empty {
  color: var(--color-text-secondary);
  font-size: 0.76rem;
}

.bundle-list__item.is-active {
  border-color: rgba(118, 74, 27, 0.32);
  box-shadow: inset 0 0 0 1px rgba(118, 74, 27, 0.12);
}

.bundle-list__load-more {
  width: 100%;
  border: 1px dashed rgba(111, 69, 31, 0.18);
  border-radius: 0.85rem;
  padding: 0.55rem;
  background: none;
  color: var(--accent-strong);
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
}
</style>
