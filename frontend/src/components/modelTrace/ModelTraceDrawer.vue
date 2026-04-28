<script setup lang="ts">
import { computed, watch } from 'vue'
import BaseModal from '../base/BaseModal.vue'
import { useModelTraceStore } from '../../stores/modelTraces'
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
</script>

<template>
  <BaseModal :open="open" title="模型调用详情" width="760px" @close="handleClose">
    <div class="model-trace-drawer">
      <p v-if="store.loadingDetail" class="model-trace-drawer__state">加载模型调用详情...</p>
      <p v-if="store.detailError" class="model-trace-drawer__error">{{ store.detailError }}</p>

      <template v-if="detail">
        <TraceSummary :trace="detail" />

        <section class="model-trace-drawer__section" aria-label="上下文块">
          <h4>上下文块</h4>
          <ContextBlockList :blocks="detail.context_blocks || []" />
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
