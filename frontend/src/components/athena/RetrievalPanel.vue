<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseButton from '../base/BaseButton.vue'
import type {
  AthenaRetrievalDiagnostics,
  AthenaRetrievalIndexResult,
  AthenaRetrievalSearchResponse,
  AthenaRetrievalSearchItem,
} from '../../api/types'

const props = defineProps<{
  diagnostics: AthenaRetrievalDiagnostics | null
  search: AthenaRetrievalSearchResponse | null
  lastIndexResult: AthenaRetrievalIndexResult | null
  loading: boolean
}>()

const emit = defineEmits<{
  reindex: []
  search: [query: string, params?: { source_type?: string }]
}>()

const query = ref('')
const sourceFilter = ref<'all' | 'chapter' | 'world_fact'>('all')

const sourceOptions = [
  { key: 'all', label: '全部证据' },
  { key: 'chapter', label: '章节原文' },
  { key: 'world_fact', label: '世界事实' },
] as const

const sourceCounts = computed(() => props.diagnostics?.documents_by_source_type || {})

const resultGroups = computed(() => {
  const groups: Record<string, AthenaRetrievalSearchItem[]> = {}
  for (const item of props.search?.items || []) {
    const key = item.source_type || 'other'
    groups[key] = groups[key] || []
    groups[key].push(item)
  }
  return Object.entries(groups).map(([sourceType, items]) => ({
    sourceType,
    label: sourceLabel(sourceType),
    items,
  }))
})

function runSearch() {
  const params = sourceFilter.value === 'all' ? undefined : { source_type: sourceFilter.value }
  emit('search', query.value, params)
}

function sourceLabel(sourceType: string) {
  if (sourceType === 'chapter') return '章节原文'
  if (sourceType === 'world_fact') return '世界事实'
  return '其他证据'
}

function sourceHint(item: AthenaRetrievalSearchItem) {
  const chapter = item.chapter_index ? `第${item.chapter_index}章` : '全局'
  return `${sourceLabel(item.source_type)} · ${chapter} · ${item.source_ref}`
}
</script>

<template>
  <div class="retrieval-panel">
    <div class="retrieval-panel__toolbar">
      <div class="retrieval-panel__search">
        <input
          v-model="query"
          class="retrieval-panel__input"
          type="search"
          placeholder="搜索角色、规则、伏笔、章节事实"
          @keydown.enter="runSearch"
        >
        <BaseButton size="sm" :disabled="props.loading || !query.trim()" @click="runSearch">
          搜索
        </BaseButton>
      </div>
      <BaseButton variant="ghost" size="sm" :disabled="props.loading" @click="emit('reindex')">
        重建索引
      </BaseButton>
    </div>

    <div class="retrieval-panel__filters" aria-label="检索范围">
      <button
        v-for="option in sourceOptions"
        :key="option.key"
        class="retrieval-panel__filter"
        :class="{ 'retrieval-panel__filter--active': sourceFilter === option.key }"
        type="button"
        @click="sourceFilter = option.key"
      >
        <span>{{ option.label }}</span>
        <strong v-if="option.key !== 'all'">{{ sourceCounts[option.key] ?? 0 }}</strong>
      </button>
    </div>

    <div class="retrieval-panel__metrics">
      <div class="retrieval-panel__metric">
        <span class="retrieval-panel__metric-label">文档</span>
        <strong>{{ props.diagnostics?.total_documents ?? 0 }}</strong>
      </div>
      <div class="retrieval-panel__metric">
        <span class="retrieval-panel__metric-label">分块</span>
        <strong>{{ props.diagnostics?.total_chunks ?? 0 }}</strong>
      </div>
      <div class="retrieval-panel__metric">
        <span class="retrieval-panel__metric-label">向量</span>
        <strong>{{ props.diagnostics?.total_embeddings ?? 0 }}</strong>
      </div>
      <div class="retrieval-panel__metric">
        <span class="retrieval-panel__metric-label">词项</span>
        <strong>{{ props.diagnostics?.total_terms ?? 0 }}</strong>
      </div>
      <div class="retrieval-panel__metric">
        <span class="retrieval-panel__metric-label">章节/事实</span>
        <strong>{{ sourceCounts.chapter ?? 0 }} / {{ sourceCounts.world_fact ?? 0 }}</strong>
      </div>
    </div>

    <div v-if="props.lastIndexResult" class="retrieval-panel__notice">
      已索引 {{ props.lastIndexResult.indexed.documents }} 个文档、
      {{ props.lastIndexResult.indexed.chunks }} 个分块、
      {{ props.lastIndexResult.indexed.terms ?? 0 }} 个词项。
    </div>

    <div v-if="props.search" class="retrieval-panel__results">
      <div class="retrieval-panel__summary">
        “{{ props.search.query }}” 命中 {{ props.search.total }} 条
      </div>
      <section
        v-for="group in resultGroups"
        :key="group.sourceType"
        class="retrieval-panel__group"
      >
        <h3 class="retrieval-panel__group-title">{{ group.label }}</h3>
        <div
          v-for="item in group.items"
          :key="item.chunk_id"
          class="retrieval-panel__result"
        >
          <div class="retrieval-panel__result-head">
            <span class="retrieval-panel__source">{{ sourceHint(item) }}</span>
            <span class="retrieval-panel__title">{{ item.title }}</span>
            <span class="retrieval-panel__score">相关度 {{ Math.round(item.score * 100) }}%</span>
          </div>
          <p class="retrieval-panel__snippet">{{ item.snippet }}</p>
          <div class="retrieval-panel__meta">
            可用于核对设定、补充提案证据或定位章节原文
          </div>
        </div>
      </section>
    </div>
    <div v-else class="retrieval-panel__empty">暂无检索结果</div>
  </div>
</template>

<style scoped>
.retrieval-panel {
  height: 100%;
  overflow: auto;
  padding: var(--space-4);
}

.retrieval-panel__toolbar {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-4);
}

.retrieval-panel__search {
  display: flex;
  flex: 1;
  gap: var(--space-2);
  min-width: 0;
}

.retrieval-panel__input {
  width: 100%;
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  color: var(--color-text-primary);
  background: var(--color-bg-primary);
  font-size: var(--text-sm);
}

.retrieval-panel__metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.retrieval-panel__filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
}

.retrieval-panel__filter {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-1) var(--space-2);
  color: var(--color-text-secondary);
  background: var(--color-bg-primary);
  font-size: var(--text-xs);
  cursor: pointer;
}

.retrieval-panel__filter--active {
  border-color: var(--color-brand);
  color: var(--color-brand);
  background: var(--color-brand-light);
}

.retrieval-panel__filter strong {
  font-weight: var(--font-semibold);
}

.retrieval-panel__metric {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-2);
}

.retrieval-panel__metric-label {
  display: block;
  margin-bottom: var(--space-1);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.retrieval-panel__metric strong {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.retrieval-panel__notice,
.retrieval-panel__summary,
.retrieval-panel__empty {
  margin-bottom: var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.retrieval-panel__result {
  border-bottom: 1px solid var(--color-border);
  padding: var(--space-3) 0;
}

.retrieval-panel__group {
  margin-bottom: var(--space-4);
}

.retrieval-panel__group-title {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.retrieval-panel__result-head {
  display: flex;
  gap: var(--space-2);
  align-items: center;
  margin-bottom: var(--space-2);
}

.retrieval-panel__source {
  color: var(--color-brand);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.retrieval-panel__title {
  flex: 1;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.retrieval-panel__score,
.retrieval-panel__meta {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.retrieval-panel__snippet {
  margin: 0 0 var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: 1.7;
}

@media (max-width: 720px) {
  .retrieval-panel__toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .retrieval-panel__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
