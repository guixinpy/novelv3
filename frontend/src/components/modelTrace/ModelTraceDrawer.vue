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
const longformDiagnostics = computed(() => detail.value ? resolveLongformDiagnostics(detail.value.trace_metadata) : null)
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
    requested_context_chars: numberFromUnknown(budget.requested_context_chars) || 0,
    used_context_chars: numberFromUnknown(budget.used_context_chars) || 0,
    remaining_context_chars: numberFromUnknown(budget.remaining_context_chars) || 0,
    included_blocks: numberFromUnknown(budget.included_blocks) || 0,
    omitted_blocks: omittedBlocks,
    omitted_block_keys: omittedBlockKeys,
    truncated_blocks: truncatedBlocks,
    has_omitted_blocks: omittedBlocks > 0 || omittedBlockKeys.length > 0,
    has_truncated_blocks: truncatedBlocks.length > 0,
  }
}

function resolveLongformDiagnostics(metadata: Record<string, unknown>) {
  const wordTarget = resolveChapterWordTarget(metadata.chapter_word_target)
  const warnings = resolvePostGenerationWarnings(metadata.post_generation_warnings)
  if (!wordTarget && warnings.length === 0) return null
  return { wordTarget, warnings }
}

function resolveChapterWordTarget(value: unknown) {
  if (!isRecord(value)) return null
  const actual = numberFromUnknown(value.actual_word_count)
  if (actual === null) return null
  const average = numberFromUnknown(value.target_average_word_count)
  const targetMin = numberFromUnknown(value.target_min_word_count)
  const targetMax = numberFromUnknown(value.target_max_word_count)
  const deviation = numberFromUnknown(value.deviation_word_count)
  const status = stringFromUnknown(value.status) || 'untracked'
  return {
    actual,
    average,
    deviation,
    range: targetMin !== null && targetMax !== null ? `${formatNumber(targetMin)}-${formatNumber(targetMax)}字` : '',
    statusClass: `model-trace-diagnostic__status--${status}`,
    statusLabel: chapterWordTargetStatusLabel(status),
    summary: average !== null
      ? `${formatNumber(actual)}字 / 目标${formatNumber(average)}字`
      : `${formatNumber(actual)}字`,
  }
}

function resolvePostGenerationWarnings(value: unknown) {
  if (!Array.isArray(value)) return []
  return value
    .filter(isRecord)
    .map((item) => ({
      stage: postGenerationStageLabel(stringFromUnknown(item.stage) || 'unknown'),
      errorType: stringFromUnknown(item.error_type) || 'Error',
      message: stringFromUnknown(item.message) || '未提供错误信息',
    }))
}

function chapterWordTargetStatusLabel(status: string) {
  if (status === 'under') return '偏短'
  if (status === 'within') return '达标'
  if (status === 'over') return '偏长'
  return '未跟踪'
}

function postGenerationStageLabel(stage: string) {
  const labels: Record<string, string> = {
    consistency_check: '一致性检查',
    athena_analysis: '雅典娜分析',
    chapter_retrieval_index: '章节检索索引',
    longform_memory_refresh: '长篇记忆刷新',
    longform_memory_retrieval_sync: '长篇记忆检索同步',
    chapter_generated_event: '章节生成事件',
  }
  return labels[stage] || stage
}

function formatNumber(value: number) {
  return value.toLocaleString('zh-CN')
}

function formatSignedNumber(value: number | null) {
  if (value === null) return ''
  if (value > 0) return `+${formatNumber(value)}`
  return formatNumber(value)
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

        <section v-if="longformDiagnostics" class="model-trace-drawer__section" aria-label="长篇生成诊断">
          <h4>长篇生成诊断</h4>
          <div class="model-trace-diagnostics">
            <article v-if="longformDiagnostics.wordTarget" class="model-trace-diagnostic">
              <div class="model-trace-diagnostic__header">
                <span>章节字数目标</span>
                <span
                  class="model-trace-diagnostic__status"
                  :class="longformDiagnostics.wordTarget.statusClass"
                >
                  {{ longformDiagnostics.wordTarget.statusLabel }}
                </span>
              </div>
              <strong>{{ longformDiagnostics.wordTarget.summary }}</strong>
              <p v-if="longformDiagnostics.wordTarget.range">
                目标范围 {{ longformDiagnostics.wordTarget.range }}
                <template v-if="longformDiagnostics.wordTarget.deviation !== null">
                  · 偏离 {{ formatSignedNumber(longformDiagnostics.wordTarget.deviation) }}字
                </template>
              </p>
            </article>

            <article v-if="longformDiagnostics.warnings.length" class="model-trace-diagnostic">
              <div class="model-trace-diagnostic__header">
                <span>生成后维护警告</span>
                <span class="model-trace-diagnostic__status model-trace-diagnostic__status--warning">
                  {{ longformDiagnostics.warnings.length }}
                </span>
              </div>
              <ul class="model-trace-diagnostic__warnings">
                <li v-for="(warning, index) in longformDiagnostics.warnings" :key="`${warning.stage}-${index}`">
                  <div>
                    <strong>{{ warning.stage }}</strong>
                    <span>{{ warning.errorType }}</span>
                  </div>
                  <p>{{ warning.message }}</p>
                </li>
              </ul>
            </article>
          </div>
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

.model-trace-diagnostics {
  display: grid;
  gap: var(--space-3);
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
}

.model-trace-diagnostic {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
  padding: var(--space-3);
}

.model-trace-diagnostic__header {
  align-items: center;
  color: var(--color-text-secondary);
  display: flex;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  gap: var(--space-2);
  justify-content: space-between;
  line-height: var(--leading-tight);
}

.model-trace-diagnostic strong {
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  line-height: var(--leading-tight);
}

.model-trace-diagnostic p {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  margin: 0;
  overflow-wrap: anywhere;
}

.model-trace-diagnostic__status {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  flex: 0 0 auto;
  font-size: var(--text-xs);
  line-height: var(--leading-tight);
  padding: 2px var(--space-2);
}

.model-trace-diagnostic__status--within {
  background: var(--color-success-light);
  border-color: var(--color-success);
  color: var(--color-success);
}

.model-trace-diagnostic__status--under,
.model-trace-diagnostic__status--over,
.model-trace-diagnostic__status--warning {
  background: var(--color-warning-light);
  border-color: var(--color-warning);
  color: var(--color-warning);
}

.model-trace-diagnostic__warnings {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  list-style: none;
  margin: 0;
  padding: 0;
}

.model-trace-diagnostic__warnings li {
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding-top: var(--space-2);
}

.model-trace-diagnostic__warnings li:first-child {
  border-top: 0;
  padding-top: 0;
}

.model-trace-diagnostic__warnings div {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.model-trace-diagnostic__warnings strong {
  font-size: var(--text-sm);
}

.model-trace-diagnostic__warnings span {
  color: var(--color-text-tertiary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
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
