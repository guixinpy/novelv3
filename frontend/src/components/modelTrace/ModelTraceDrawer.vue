<script setup lang="ts">
import { computed, watch } from 'vue'
import BaseModal from '../base/BaseModal.vue'
import { useModelTraceStore } from '../../stores/modelTraces'
import type { ModelCallTraceDetail, PromptBudget, PromptMetadata } from '../../api/types'
import TraceSummary from './TraceSummary.vue'
import ContextBlockList from './ContextBlockList.vue'
import RawMessagesViewer from './RawMessagesViewer.vue'

const props = defineProps<{
  projectId: string
  traceId?: string | null
  open: boolean
}>()

const emit = defineEmits<{ close: [] }>()
const store = useModelTraceStore()

const detail = computed(() => store.selectedTrace)
const promptMetadata = computed(() => detail.value ? resolvePromptMetadata(detail.value) : null)
const promptBudget = computed(() => detail.value ? resolvePromptBudget(detail.value) : null)
const hasMetadata = computed(() => {
  const metadata = detail.value?.trace_metadata
  return Boolean(metadata && Object.keys(metadata).length > 0)
})
const metadataText = computed(() => {
  if (!detail.value?.trace_metadata) return ''
  try {
    return JSON.stringify(detail.value.trace_metadata, null, 2)
  } catch {
    return String(detail.value.trace_metadata)
  }
})

watch(
  () => [props.open, props.projectId, props.traceId] as const,
  ([open, projectId, traceId]) => {
    if (!open || !projectId || !traceId) {
      store.closeTrace()
      return
    }
    void store.selectTrace(projectId, traceId)
  },
  { immediate: true },
)

function handleClose() {
  store.closeTrace()
  emit('close')
}

function resolvePromptMetadata(trace: ModelCallTraceDetail): PromptMetadata | null {
  if (trace.prompt_metadata) return trace.prompt_metadata

  const metadata = trace.trace_metadata || {}
  const promptMetadata: PromptMetadata = {
    prompt_id: stringFromUnknown(metadata.prompt_id),
    prompt_version: stringFromUnknown(metadata.prompt_version),
    template_name: stringFromUnknown(metadata.template_name),
    template_hash: stringFromUnknown(metadata.template_hash),
  }

  return Object.values(promptMetadata).some(Boolean) ? promptMetadata : null
}

function resolvePromptBudget(trace: ModelCallTraceDetail): PromptBudget | null {
  if (trace.prompt_budget) return trace.prompt_budget

  const budget = trace.trace_metadata?.budget
  if (!isRecord(budget)) return null

  const omittedBlockKeys = stringListFromUnknown(budget.omitted_block_keys)
  const truncatedBlocks = stringListFromUnknown(budget.truncated_blocks)
  const omittedBlocks = numberFromUnknown(budget.omitted_blocks) || 0

  return {
    max_context_chars: numberFromUnknown(budget.max_context_chars),
    included_blocks: numberFromUnknown(budget.included_blocks) || 0,
    omitted_blocks: omittedBlocks,
    omitted_block_keys: omittedBlockKeys,
    truncated_blocks: truncatedBlocks,
    has_omitted_blocks: omittedBlocks > 0 || omittedBlockKeys.length > 0,
    has_truncated_blocks: truncatedBlocks.length > 0,
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function stringFromUnknown(value: unknown) {
  if (value === null || value === undefined) return null
  const text = String(value)
  return text || null
}

function numberFromUnknown(value: unknown) {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  if (typeof value === 'string' && value.trim()) {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) return parsed
  }
  return null
}

function stringListFromUnknown(value: unknown) {
  if (!Array.isArray(value)) return []
  return value
    .map((item) => stringFromUnknown(item))
    .filter((item): item is string => Boolean(item))
}
</script>

<template>
  <BaseModal :open="open" title="模型调用详情" width="760px" @close="handleClose">
    <div class="model-trace-drawer">
      <p v-if="store.loadingDetail" class="model-trace-drawer__state">加载模型调用详情...</p>
      <p v-if="store.detailError" class="model-trace-drawer__error">{{ store.detailError }}</p>

      <template v-if="detail">
        <TraceSummary :trace="detail" :prompt-metadata="promptMetadata" />

        <section class="model-trace-drawer__section" aria-label="上下文块">
          <h4>上下文块</h4>
          <ContextBlockList :blocks="detail.context_blocks || []" :budget="promptBudget" />
        </section>

        <section class="model-trace-drawer__section" aria-label="Raw messages">
          <h4>Raw Messages</h4>
          <RawMessagesViewer :messages="detail.messages || []" />
        </section>

        <section v-if="hasMetadata" class="model-trace-drawer__section" aria-label="Trace metadata">
          <h4>Trace Metadata</h4>
          <pre class="model-trace-drawer__metadata">{{ metadataText }}</pre>
        </section>
      </template>

      <p v-else-if="!store.loadingDetail && !store.detailError" class="model-trace-drawer__state">
        未选择模型调用记录
      </p>
    </div>
  </BaseModal>
</template>

<style scoped>
.model-trace-drawer {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  min-width: 0;
}

.model-trace-drawer__section {
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  min-width: 0;
  padding-top: var(--space-4);
}

.model-trace-drawer__section h4 {
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  line-height: var(--leading-tight);
  margin: 0;
}

.model-trace-drawer__state {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  margin: 0;
}

.model-trace-drawer__error {
  background: var(--color-error-light);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md);
  color: var(--color-error);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  margin: 0;
  padding: var(--space-3);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.model-trace-drawer__metadata {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--leading-relaxed);
  margin: 0;
  max-height: 240px;
  overflow: auto;
  padding: var(--space-3);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
