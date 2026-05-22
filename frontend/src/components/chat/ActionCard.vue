<template>
  <div class="action-card" data-testid="pending-action-card">
    <p class="action-card__copy">
      {{ action.description }}
    </p>
    <section
      v-if="executionPreview"
      class="action-card__preview"
      aria-label="执行预览"
    >
      <div class="action-card__preview-title">{{ executionPreview.title }}</div>
      <p class="action-card__preview-summary">{{ executionPreview.summary }}</p>
      <ul class="action-card__preview-list">
        <li
          v-for="(step, index) in previewSteps"
          :key="step.step_id || `${step.tool_name}-${index}`"
          class="action-card__preview-step"
        >
          <span class="action-card__preview-step-label">{{ step.label }}</span>
          <span
            v-if="step.reason"
            class="action-card__preview-step-reason"
          >
            {{ step.reason }}
          </span>
        </li>
      </ul>
      <dl
        v-if="auditRows.length"
        class="action-card__audit"
      >
        <dt class="action-card__audit-title">审批依据</dt>
        <template
          v-for="row in auditRows"
          :key="row.label"
        >
          <dt>{{ row.label }}</dt>
          <dd>{{ row.value }}</dd>
        </template>
      </dl>
    </section>
    <div class="action-card__actions">
      <button
        :disabled="disabled"
        class="action-card__button action-card__button--primary"
        data-testid="pending-action-confirm"
        @click="$emit('decide', 'confirm')"
      >
        同意执行
      </button>
      <button
        :disabled="disabled"
        class="action-card__button"
        @click="$emit('decide', 'cancel')"
      >
        取消
      </button>
      <button
        :disabled="disabled"
        class="action-card__button"
        @click="showRevise = !showRevise"
      >
        修改后再执行
      </button>
    </div>
    <div
      v-if="showRevise"
      class="action-card__revise"
    >
      <input
        v-model="reviseComment"
        class="action-card__input"
        placeholder="补充修改说明..."
        @keyup.enter="submitRevise"
      >
      <button
        :disabled="disabled || !reviseComment.trim()"
        class="action-card__button action-card__button--primary"
        @click="submitRevise"
      >
        提交
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const props = defineProps<{ action: any; disabled: boolean }>()
const emit = defineEmits<{ decide: [decision: string, comment?: string] }>()

const showRevise = ref(false)
const reviseComment = ref('')
const executionPreview = computed(() => props.action?.execution_preview || null)
const previewSteps = computed(() => Array.isArray(executionPreview.value?.steps) ? executionPreview.value.steps : [])
const auditRows = computed(() => {
  const audit = executionPreview.value?.audit
  if (!audit || typeof audit !== 'object') return []
  return [
    { label: '意图', value: audit.intent_class },
    { label: '来源投影', value: audit.source_projection_id },
    { label: '规划器', value: audit.planner_version },
    { label: '计划', value: audit.plan_id },
  ].filter((row) => typeof row.value === 'string' && row.value.trim())
})

function submitRevise() {
  if (!reviseComment.value.trim()) return
  emit('decide', 'revise', reviseComment.value)
  reviseComment.value = ''
  showRevise.value = false
}
</script>

<style scoped>
.action-card {
  margin-top: 0.85rem;
  border: 1px solid rgba(111, 69, 31, 0.16);
  background:
    linear-gradient(180deg, rgba(248, 239, 221, 0.96) 0%, rgba(241, 230, 209, 0.94) 100%);
  border-radius: 1rem;
  padding: 1rem;
}

.action-card__copy {
  margin-bottom: 0.8rem;
  color: var(--color-text-primary);
  font-size: 0.92rem;
  line-height: 1.55;
}

.action-card__preview {
  margin-bottom: 0.85rem;
  border: 1px solid rgba(111, 69, 31, 0.12);
  border-radius: 0.85rem;
  background: rgba(255, 251, 242, 0.72);
  padding: 0.8rem;
}

.action-card__preview-title {
  color: var(--color-text-primary);
  font-size: 0.88rem;
  font-weight: 800;
  line-height: 1.35;
}

.action-card__preview-summary {
  margin: 0.3rem 0 0;
  color: var(--color-text-secondary);
  font-size: 0.82rem;
  line-height: 1.45;
}

.action-card__preview-list {
  display: grid;
  gap: 0.35rem;
  margin: 0.55rem 0 0;
  padding: 0;
  list-style: none;
}

.action-card__preview-step {
  display: grid;
  gap: 0.15rem;
  padding-left: 0.55rem;
  border-left: 2px solid rgba(111, 69, 31, 0.22);
}

.action-card__preview-step-label {
  color: var(--color-text-primary);
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1.35;
}

.action-card__preview-step-reason {
  color: var(--color-text-secondary);
  font-size: 0.8rem;
  line-height: 1.4;
}

.action-card__audit {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: 0.28rem 0.55rem;
  margin: 0.7rem 0 0;
  color: var(--color-text-tertiary);
  font-size: 0.76rem;
  line-height: 1.35;
}

.action-card__audit-title {
  grid-column: 1 / -1;
  color: var(--color-text-secondary);
  font-weight: 800;
}

.action-card__audit dt,
.action-card__audit dd {
  margin: 0;
}

.action-card__audit dd {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.action-card__button {
  border: 1px solid rgba(111, 69, 31, 0.16);
  background: rgba(255, 251, 242, 0.92);
  color: var(--color-text-secondary);
  border-radius: 0.85rem;
  padding: 0.55rem 0.9rem;
  font-size: 0.86rem;
  font-weight: 700;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.action-card__button--primary {
  background: linear-gradient(180deg, #8d5d31 0%, #6f451f 100%);
  color: #fff8ef;
}

.action-card__button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 18px rgba(79, 55, 27, 0.12);
}

.action-card__button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.action-card__revise {
  display: flex;
  gap: 0.65rem;
  margin-top: 0.8rem;
}

.action-card__input {
  flex: 1;
  min-width: 0;
  border: 1px solid rgba(111, 69, 31, 0.16);
  background: rgba(255, 251, 242, 0.96);
  color: var(--color-text-primary);
  border-radius: 0.85rem;
  padding: 0.65rem 0.85rem;
  font-size: 0.88rem;
  outline: none;
}

.action-card__input:focus {
  border-color: rgba(111, 69, 31, 0.34);
  box-shadow: 0 0 0 3px rgba(141, 93, 49, 0.12);
}
</style>
