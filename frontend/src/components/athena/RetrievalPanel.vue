<script setup lang="ts">
import { ref } from 'vue'
import BaseButton from '../base/BaseButton.vue'
import type {
  AthenaRetrievalDiagnostics,
  AthenaRetrievalIndexResult,
  AthenaRetrievalSearchResponse,
} from '../../api/types'

const props = defineProps<{
  diagnostics: AthenaRetrievalDiagnostics | null
  search: AthenaRetrievalSearchResponse | null
  lastIndexResult: AthenaRetrievalIndexResult | null
  loading: boolean
}>()

const emit = defineEmits<{
  reindex: []
  search: [query: string]
}>()

const query = ref('')

function runSearch() {
  emit('search', query.value)
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
        <span class="retrieval-panel__metric-label">模型</span>
        <strong>{{ props.diagnostics?.embedding_model ?? '未索引' }}</strong>
      </div>
    </div>

    <div v-if="props.lastIndexResult" class="retrieval-panel__notice">
      已索引 {{ props.lastIndexResult.indexed.documents }} 个文档、
      {{ props.lastIndexResult.indexed.chunks }} 个分块。
    </div>

    <div v-if="props.search" class="retrieval-panel__results">
      <div class="retrieval-panel__summary">
        “{{ props.search.query }}” 命中 {{ props.search.total }} 条
      </div>
      <div
        v-for="item in props.search.items"
        :key="item.chunk_id"
        class="retrieval-panel__result"
      >
        <div class="retrieval-panel__result-head">
          <span class="retrieval-panel__source">{{ item.source_type === 'chapter' ? '章节' : '世界事实' }}</span>
          <span class="retrieval-panel__title">{{ item.title }}</span>
          <span class="retrieval-panel__score">{{ Math.round(item.score * 100) }}%</span>
        </div>
        <p class="retrieval-panel__snippet">{{ item.snippet }}</p>
        <div class="retrieval-panel__meta">
          {{ item.source_ref }}
          <span v-if="item.chapter_index"> · 第{{ item.chapter_index }}章</span>
        </div>
      </div>
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
