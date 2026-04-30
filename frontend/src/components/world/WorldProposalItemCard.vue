<template>
  <article
    class="proposal-item-card"
    :class="conflictClass"
    data-testid="world-proposal-item-card"
    :data-item-status="item.item_status"
  >
    <header class="proposal-item-card__header">
      <div>
        <p class="proposal-item-card__claim">
          {{ item.subject_ref }}.{{ item.predicate }}
        </p>
        <h4 class="proposal-item-card__value">
          {{ renderItemSummary(item) }}
        </h4>
      </div>
      <div class="proposal-item-card__meta">
        <span>{{ statusLabel(item.item_status) }}</span>
        <span>置信度 {{ item.confidence.toFixed(2) }}</span>
      </div>
    </header>

    <div v-if="itemConflicts.length" class="proposal-item-card__conflicts">
      <div
        v-for="conflict in itemConflicts"
        :key="conflict.conflict_type"
        class="proposal-item-card__conflict"
        :class="`is-${conflict.conflict_type}`"
      >
        <span v-if="conflict.conflict_type === 'truth_conflict'">⚠</span>
        <span v-else>⚡</span>
        {{ conflict.detail }}
      </div>
    </div>

    <p class="proposal-item-card__submeta">
      {{ item.claim_id }} / {{ item.authority_type }}
    </p>

    <div v-if="evidenceSpan || quality" class="proposal-item-card__evidence">
      <div v-if="evidenceSpan" class="proposal-item-card__evidence-block">
        <span class="proposal-item-card__evidence-label">证据</span>
        <strong v-if="evidenceSpan.ref">{{ evidenceSpan.ref }}</strong>
        <p v-if="evidenceSpan.text">{{ evidenceSpan.text }}</p>
        <p v-else-if="evidenceSpan.matched_names?.length">{{ evidenceSpan.matched_names.join(' / ') }}</p>
      </div>
      <div v-if="quality" class="proposal-item-card__evidence-block">
        <span class="proposal-item-card__evidence-label">质量</span>
        <strong>{{ quality.signal || 'unknown' }} / {{ quality.confidence_band || 'unknown' }}</strong>
        <p>{{ priorityText }}</p>
      </div>
    </div>

    <WorldProposalActionPanel
      :busy="busy"
      :approval-review-id="approvalReviewId"
      :can-rollback="item.item_status !== 'rolled_back'"
      :item="item"
      :reviewer-ref="reviewerRef"
      :anchor-options="anchorOptions"
      @review="forwardReview"
      @split="forwardSplit"
      @rollback="forwardRollback"
    />
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import WorldProposalActionPanel from './WorldProposalActionPanel.vue'
import type {
  ProposalEvidenceSpan,
  ProposalItem,
  ProposalItemConflict,
  ProposalObjectValue,
  ProposalQuality,
  ProposalReviewRequest,
} from '../../api/types'

const props = defineProps<{
  item: ProposalItem
  busy: boolean
  approvalReviewId: string | null
  reviewerRef: string
  anchorOptions: string[]
  conflicts: ProposalItemConflict[]
}>()

const itemConflicts = computed(() =>
  props.conflicts.filter((c) => c.item_id === props.item.id),
)

const conflictClass = computed(() => {
  if (itemConflicts.value.some((c) => c.conflict_type === 'truth_conflict')) return 'has-conflict'
  if (itemConflicts.value.some((c) => c.conflict_type === 'high_impact')) return 'has-risk'
  return ''
})

const objectPayload = computed<ProposalObjectValue | null>(() => {
  const value = props.item.object_ref_or_value
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as ProposalObjectValue
})

const evidenceSpan = computed<ProposalEvidenceSpan | null>(() => {
  const span = objectPayload.value?.evidence_span
  return span && typeof span === 'object' ? span : null
})

const quality = computed<ProposalQuality | null>(() => {
  const itemQuality = objectPayload.value?.quality
  return itemQuality && typeof itemQuality === 'object' ? itemQuality : null
})

const priorityText = computed(() => {
  const priority = quality.value?.review_priority || 'normal'
  if (priority === 'high') return '优先人工复核'
  if (priority === 'low') return '可低优先级处理'
  return '常规复核'
})

const emit = defineEmits<{
  review: [itemId: string, payload: ProposalReviewRequest]
  split: [bundleId: string, itemId: string, reason: string]
  rollback: [reviewId: string, reason: string, itemId: string]
}>()

function renderValue(value: unknown) {
  return typeof value === 'string' ? value : JSON.stringify(value)
}

function renderItemSummary(item: ProposalItem) {
  if (item.notes) return item.notes
  const value = item.object_ref_or_value
  if (item.predicate === 'presence_count' && value && typeof value === 'object' && 'count' in value) {
    const data = value as { count?: unknown; chapter_index?: unknown }
    const count = typeof data.count === 'number' ? data.count : String(data.count || '')
    const chapter = typeof data.chapter_index === 'number' ? `第${data.chapter_index}章` : '本章'
    return `${item.subject_ref} 在${chapter}出现 ${count} 次`
  }
  return renderValue(value)
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '待审',
    needs_edit: '需编辑',
    approved: '已通过',
    approved_with_edits: '编辑后通过',
    rejected: '已驳回',
    uncertain: '不确定',
    split: '已拆分',
    rolled_back: '已回滚',
  }
  return labels[status] || status
}

function forwardReview(payload: ProposalReviewRequest) {
  emit('review', props.item.id, payload)
}

function forwardSplit(reason: string) {
  emit('split', props.item.bundle_id, props.item.id, reason)
}

function forwardRollback(reviewId: string, reason: string) {
  emit('rollback', reviewId, reason, props.item.id)
}
</script>

<style scoped>
.proposal-item-card {
  display: grid;
  gap: 0.75rem;
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 1rem;
  padding: 1rem;
  background:
    linear-gradient(180deg, rgba(252, 249, 241, 0.96) 0%, rgba(244, 236, 223, 0.92) 100%);
}

.proposal-item-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.9rem;
}

.proposal-item-card__claim,
.proposal-item-card__submeta {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 0.76rem;
}

.proposal-item-card__value {
  margin: 0.12rem 0 0;
  color: var(--color-text-primary);
  font-size: 0.92rem;
}

.proposal-item-card__meta {
  display: grid;
  gap: 0.2rem;
  justify-items: end;
  color: var(--accent-strong);
  font-size: 0.75rem;
  font-weight: 700;
}

.proposal-item-card__evidence {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
}

.proposal-item-card__evidence-block {
  min-width: 0;
  border: 1px solid rgba(111, 69, 31, 0.12);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  background: rgba(255, 252, 244, 0.72);
}

.proposal-item-card__evidence-label {
  display: block;
  color: var(--color-text-tertiary);
  font-size: 0.68rem;
  font-weight: 700;
}

.proposal-item-card__evidence-block strong {
  display: block;
  color: var(--color-text-primary);
  font-size: 0.76rem;
  overflow-wrap: anywhere;
}

.proposal-item-card__evidence-block p {
  margin: 0.18rem 0 0;
  color: var(--color-text-secondary);
  font-size: 0.74rem;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.proposal-item-card.has-conflict { border-left: 3px solid #dc2626; }
.proposal-item-card.has-risk { border-left: 3px solid #d97706; }
.proposal-item-card__conflicts { display: grid; gap: 0.3rem; }
.proposal-item-card__conflict { font-size: 0.72rem; line-height: 1.4; }
.proposal-item-card__conflict.is-truth_conflict { color: #dc2626; }
.proposal-item-card__conflict.is-high_impact { color: #d97706; }

@media (max-width: 720px) {
  .proposal-item-card__evidence {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
