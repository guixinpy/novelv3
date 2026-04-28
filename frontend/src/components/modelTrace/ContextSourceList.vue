<script setup lang="ts">
import type { TraceSource } from '../../api/types'

defineProps<{
  sources: TraceSource[]
}>()

function formatValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return ''
  return String(value)
}

function formatMetadata(metadata: unknown) {
  if (!metadata || typeof metadata !== 'object') return ''
  const value = metadata as Record<string, unknown>
  if (Object.keys(value).length === 0) return ''
  try {
    return JSON.stringify(value)
  } catch {
    return String(value)
  }
}
</script>

<template>
  <div class="context-sources">
    <p v-if="!sources.length" class="context-sources__empty">无来源</p>
    <ul v-else class="context-sources__list">
      <li v-for="(source, index) in sources" :key="`${source.source_type}-${source.source_id || source.source_ref || index}`" class="context-sources__item">
        <div class="context-sources__main">
          <span class="context-sources__type">{{ source.source_type }}</span>
          <span v-if="formatValue(source.label)" class="context-sources__label">{{ source.label }}</span>
          <span v-if="formatValue(source.title)" class="context-sources__title">{{ source.title }}</span>
        </div>
        <div class="context-sources__meta">
          <span v-if="formatValue(source.source_id)">ID: {{ source.source_id }}</span>
          <span v-if="source.chapter_index !== null && source.chapter_index !== undefined">第 {{ source.chapter_index }} 章</span>
          <span v-if="formatValue(source.source_ref)">Ref: {{ source.source_ref }}</span>
          <span v-if="formatMetadata(source.metadata)">Meta: {{ formatMetadata(source.metadata) }}</span>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.context-sources {
  min-width: 0;
}

.context-sources__empty {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  margin: 0;
}

.context-sources__list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  list-style: none;
  margin: 0;
  padding: 0;
}

.context-sources__item {
  border-left: 2px solid var(--color-border-strong);
  min-width: 0;
  padding-left: var(--space-2);
}

.context-sources__main,
.context-sources__meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1) var(--space-2);
  min-width: 0;
}

.context-sources__type {
  color: var(--color-brand);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.context-sources__label,
.context-sources__title {
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.context-sources__meta {
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  margin-top: var(--space-1);
}

.context-sources__meta span {
  max-width: 100%;
  overflow-wrap: anywhere;
}
</style>
