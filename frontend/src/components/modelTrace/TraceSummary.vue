<script setup lang="ts">
import { computed } from 'vue'
import type { ModelCallTraceListItem, PromptMetadata } from '../../api/types'

const props = defineProps<{
  trace: ModelCallTraceListItem
  promptMetadata?: PromptMetadata | null
}>()

const statusMeta = computed(() => {
  const status = props.trace.status || 'unknown'
  if (status === 'running') return { label: '运行中', className: 'trace-summary__status--running' }
  if (status === 'success') return { label: '成功', className: 'trace-summary__status--success' }
  if (status === 'failed') return { label: '失败', className: 'trace-summary__status--failed' }
  return { label: status, className: 'trace-summary__status--default' }
})

const totalTokens = computed(() => {
  const promptTokens = props.trace.prompt_tokens
  const completionTokens = props.trace.completion_tokens
  if (promptTokens === null || promptTokens === undefined || completionTokens === null || completionTokens === undefined) {
    return null
  }
  return promptTokens + completionTokens
})

function formatValue(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '-'
  return String(value)
}

function formatLatency(value: number | null | undefined) {
  if (value === null || value === undefined) return '-'
  return `${value} ms`
}

function formatChapter(value: number | null | undefined) {
  if (value === null || value === undefined) return '-'
  return `第 ${value} 章`
}

function formatTime(value: string | null | undefined) {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function formatHash(value: string | null | undefined) {
  if (!value) return '-'
  if (value.length <= 22) return value
  return `${value.slice(0, 19)}...`
}
</script>

<template>
  <section class="trace-summary" aria-label="模型调用摘要">
    <div class="trace-summary__header">
      <div>
        <div class="trace-summary__eyebrow">Trace</div>
        <h4 class="trace-summary__title">{{ trace.trace_type }}</h4>
      </div>
      <span class="trace-summary__status" :class="statusMeta.className">{{ statusMeta.label }}</span>
    </div>

    <dl class="trace-summary__grid">
      <div>
        <dt>模型</dt>
        <dd>{{ formatValue(trace.model) }}</dd>
      </div>
      <div>
        <dt>Tokens</dt>
        <dd>
          <span>{{ formatValue(trace.prompt_tokens) }}</span>
          <span class="trace-summary__muted"> / </span>
          <span>{{ formatValue(trace.completion_tokens) }}</span>
          <span v-if="totalTokens !== null" class="trace-summary__muted"> = {{ totalTokens }}</span>
        </dd>
      </div>
      <div>
        <dt>延迟</dt>
        <dd>{{ formatLatency(trace.latency_ms) }}</dd>
      </div>
      <div>
        <dt>章节</dt>
        <dd>{{ formatChapter(trace.chapter_index) }}</dd>
      </div>
      <div>
        <dt>Dialog</dt>
        <dd>{{ formatValue(trace.dialog_id) }}</dd>
      </div>
      <div>
        <dt>时间</dt>
        <dd>{{ formatTime(trace.created_at) }}</dd>
      </div>
      <div v-if="promptMetadata">
        <dt>Prompt</dt>
        <dd>{{ formatValue(promptMetadata.prompt_id) }}</dd>
      </div>
      <div v-if="promptMetadata">
        <dt>版本</dt>
        <dd>{{ formatValue(promptMetadata.prompt_version) }}</dd>
      </div>
      <div v-if="promptMetadata">
        <dt>Template</dt>
        <dd>{{ formatValue(promptMetadata.template_name) }}</dd>
      </div>
      <div v-if="promptMetadata">
        <dt>Hash</dt>
        <dd :title="promptMetadata.template_hash || undefined">{{ formatHash(promptMetadata.template_hash) }}</dd>
      </div>
    </dl>

    <p v-if="trace.error_message" class="trace-summary__error">{{ trace.error_message }}</p>
  </section>
</template>

<style scoped>
.trace-summary {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.trace-summary__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.trace-summary__eyebrow {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.trace-summary__title {
  margin: var(--space-1) 0 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  line-height: var(--leading-tight);
  overflow-wrap: anywhere;
}

.trace-summary__status {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  flex-shrink: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  line-height: var(--leading-tight);
  padding: var(--space-1) var(--space-2);
}

.trace-summary__status--running {
  background: var(--color-warning-light);
  border-color: var(--color-warning);
  color: var(--color-warning);
}

.trace-summary__status--success {
  background: var(--color-success-light);
  border-color: var(--color-success);
  color: var(--color-success);
}

.trace-summary__status--failed {
  background: var(--color-error-light);
  border-color: var(--color-error);
  color: var(--color-error);
}

.trace-summary__status--default {
  background: var(--color-bg-secondary);
  color: var(--color-text-secondary);
}

.trace-summary__grid {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(2, minmax(0, 1fr));
  margin: 0;
}

.trace-summary__grid div {
  min-width: 0;
}

.trace-summary__grid dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  margin-bottom: var(--space-1);
}

.trace-summary__grid dd {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  margin: 0;
  overflow-wrap: anywhere;
}

.trace-summary__muted {
  color: var(--color-text-tertiary);
}

.trace-summary__error {
  background: var(--color-error-light);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md);
  color: var(--color-error);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  margin: 0;
  padding: var(--space-2) var(--space-3);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

@media (max-width: 640px) {
  .trace-summary__grid {
    grid-template-columns: 1fr;
  }
}
</style>
