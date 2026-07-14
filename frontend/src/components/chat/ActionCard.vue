<template>
  <div class="action-card" data-testid="pending-action-card">
    <p class="action-card__copy">
      {{ actionCopy }}
    </p>
    <div
      v-if="chapterTargetConflict"
      class="action-card__warning"
      data-testid="chapter-target-conflict"
    >
      <strong>章节目标冲突</strong>
      <span>
        第{{ chapterTargetConflict.chapterIndex }}章已有{{ chapterTargetConflict.sourceLabel }}，确认前请检查是否要继续覆盖同一章节。
      </span>
    </div>
    <dl
      v-if="dialogRouteRows.length"
      class="action-card__route"
      data-testid="dialog-route-decision"
    >
      <template
        v-for="row in dialogRouteRows"
        :key="row.label"
      >
        <dt>{{ row.label }}</dt>
        <dd>{{ row.value }}</dd>
      </template>
    </dl>
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
    <section
      v-if="safetyRecommendations.length"
      class="action-card__safety"
      aria-label="Agent 安全建议"
    >
      <div
        v-for="recommendation in safetyRecommendations"
        :key="recommendation.key"
        class="action-card__safety-item"
        :class="`action-card__safety-item--${recommendation.severity}`"
      >
        <div class="action-card__safety-title">{{ recommendation.title }}</div>
        <p class="action-card__safety-message">{{ recommendation.message }}</p>
        <button
          v-if="recommendation.action"
          :disabled="disabled"
          type="button"
          class="action-card__safety-action"
          data-testid="pending-action-safety-prepare"
          @click="$emit('safetyAction', recommendation.action)"
        >
          {{ recommendation.action.label }}
        </button>
      </div>
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
const emit = defineEmits<{
  decide: [decision: string, comment?: string]
  safetyAction: [action: {
    kind: string
    label: string
    pending_action_id: string
    auto_execute: boolean
    guarded_apply: boolean
  }]
}>()

const showRevise = ref(false)
const reviseComment = ref('')
const executionPreview = computed(() => props.action?.execution_preview || null)
const chapterTargetConflict = computed(() => {
  const conflict = props.action?.params?.chapter_target_conflict
  if (!conflict || typeof conflict !== 'object') return null
  if (conflict.status !== 'reserved') return null
  const chapterIndex = Number(conflict.chapter_index || props.action?.params?.chapter_index)
  if (!Number.isInteger(chapterIndex) || chapterIndex <= 0) return null
  const sourceLabel = typeof conflict.source_label === 'string' && conflict.source_label.trim()
    ? conflict.source_label.trim()
    : '待确认或运行中的生成任务'
  return { chapterIndex, sourceLabel }
})
const actionCopy = computed(() => {
  const copy = String(props.action?.description || '')
  if (!chapterTargetConflict.value) return copy
  return copy.replace(/\s*注意：第\d+章已有.+?，请确认是否仍要继续。\s*$/, '').trim()
})
const dialogRouteRows = computed(() => {
  const decision = props.action?.params?.dialog_route_decision
  if (!decision || typeof decision !== 'object') return []
  const rows: Array<{ label: string; value: string }> = []
  const selectedRoute = stringValue(decision.selected_route)
  if (selectedRoute) {
    rows.push({ label: '继续路由', value: dialogRouteLabel(selectedRoute) })
  }
  const reasonCode = stringValue(decision.reason_code)
  if (reasonCode) {
    rows.push({ label: '路由原因', value: dialogRouteReasonLabel(reasonCode) })
  }
  return rows
})
const previewSteps = computed(() => Array.isArray(executionPreview.value?.steps) ? executionPreview.value.steps : [])
const safetyRecommendations = computed(() => {
  const recommendations = props.action?.safety_view?.recommendations
  if (!Array.isArray(recommendations)) return []
  return recommendations
    .map((item: any, index: number) => {
      const title = typeof item?.title === 'string' ? item.title.trim() : ''
      const message = typeof item?.message === 'string' ? item.message.trim() : ''
      const severity = typeof item?.severity === 'string' && item.severity.trim()
        ? item.severity.trim()
        : 'info'
      if (!title && !message) return null
      return {
        key: `${item?.kind || 'recommendation'}-${index}`,
        title,
        message,
        severity,
        action: safetyActionFromRecommendation(item),
      }
    })
    .filter((item): item is {
      key: string
      title: string
      message: string
      severity: string
      action: ReturnType<typeof safetyActionFromRecommendation>
    } => Boolean(item))
})
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

function safetyActionFromRecommendation(item: any) {
  const action = item?.action
  if (!action || typeof action !== 'object') return null
  if (action.kind !== 'prepare_route_upgrade_contract') return null
  if (action.auto_execute === true || action.guarded_apply === true) return null
  const pendingActionId = typeof action.pending_action_id === 'string' ? action.pending_action_id.trim() : ''
  if (!pendingActionId || pendingActionId !== String(props.action?.id || '').trim()) return null
  const label = typeof action.label === 'string' && action.label.trim()
    ? action.label.trim()
    : '生成审批契约'
  return {
    kind: 'prepare_route_upgrade_contract',
    label,
    pending_action_id: pendingActionId,
    auto_execute: false,
    guarded_apply: false,
  }
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
}

function dialogRouteLabel(route: string) {
  if (route === 'recover_blocked_run') return '恢复阻塞运行'
  if (route === 'recommended_followups') return '推荐后继'
  if (route === 'chapter_generation') return '继续章节生成'
  return route
}

function dialogRouteReasonLabel(reasonCode: string) {
  if (reasonCode === 'recoverable_run_found') return '发现可恢复运行'
  if (reasonCode === 'recommended_followups_found') return '发现上一轮推荐后继'
  if (reasonCode === 'no_recovery_or_followup') return '无恢复或后继，继续章节生成'
  return reasonCode
}
</script>

<style scoped>
.action-card {
  margin-top: 0.85rem;
  border: 1px solid var(--color-warm-border);
  background:
    linear-gradient(180deg, rgba(248, 239, 221, 0.96) 0%, var(--color-chat-card-bg) 100%);
  border-radius: 1rem;
  padding: 1rem;
}

.action-card__copy {
  margin-bottom: 0.8rem;
  color: var(--color-text-primary);
  font-size: 0.92rem;
  line-height: 1.55;
}

.action-card__warning {
  display: grid;
  gap: 0.2rem;
  margin-bottom: 0.8rem;
  border-left: 3px solid var(--color-warning, #b7791f);
  background: rgba(255, 247, 214, 0.78);
  color: var(--color-text-primary);
  padding: 0.65rem 0.75rem;
  border-radius: 0.55rem;
  font-size: 0.82rem;
  line-height: 1.45;
}

.action-card__warning strong {
  font-size: 0.78rem;
}

.action-card__route {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.35rem 0.65rem;
  margin: 0 0 0.85rem;
  border: 1px solid rgba(79, 70, 229, 0.14);
  background: rgba(238, 242, 255, 0.62);
  border-radius: 0.75rem;
  padding: 0.65rem 0.75rem;
  font-size: 0.82rem;
}

.action-card__route dt {
  color: var(--color-text-secondary);
  font-weight: 700;
}

.action-card__route dd {
  margin: 0;
  color: var(--color-text-primary);
}

.action-card__preview {
  margin-bottom: 0.85rem;
  border: 1px solid var(--color-warm-subtle);
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
  border-left: 2px solid var(--color-chat-card-border);
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

.action-card__safety {
  display: grid;
  gap: 0.55rem;
  margin-bottom: 0.85rem;
}

.action-card__safety-item {
  border: 1px solid var(--color-success-light);
  background: var(--color-safety-bg);
  color: var(--color-text-primary);
  border-radius: 0.75rem;
  padding: 0.7rem 0.8rem;
}

.action-card__safety-title {
  font-size: 0.84rem;
  font-weight: 800;
  line-height: 1.35;
}

.action-card__safety-message {
  margin: 0.24rem 0 0;
  color: var(--color-text-secondary);
  font-size: 0.8rem;
  line-height: 1.45;
}

.action-card__safety-action {
  margin-top: 0.55rem;
  border: 1px solid var(--color-safety-border);
  background: rgba(255, 255, 255, 0.72);
  color: var(--color-success);
  border-radius: 0.65rem;
  padding: 0.44rem 0.7rem;
  font-size: 0.78rem;
  font-weight: 800;
  line-height: 1.2;
}

.action-card__safety-action:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.94);
}

.action-card__safety-action:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.action-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.action-card__button {
  border: 1px solid var(--color-warm-border);
  background: rgba(255, 251, 242, 0.92);
  color: var(--color-text-secondary);
  border-radius: 0.85rem;
  padding: 0.55rem 0.9rem;
  font-size: 0.86rem;
  font-weight: 700;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.action-card__button--primary {
  background: linear-gradient(180deg, var(--color-warm-amber) 0%, var(--color-warm-brown) 100%);
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
  border: 1px solid var(--color-warm-border);
  background: rgba(255, 251, 242, 0.96);
  color: var(--color-text-primary);
  border-radius: 0.85rem;
  padding: 0.65rem 0.85rem;
  font-size: 0.88rem;
  outline: none;
}

.action-card__input:focus {
  border-color: var(--color-warm-border);
  box-shadow: 0 0 0 3px rgba(141, 93, 49, 0.12);
}
</style>
