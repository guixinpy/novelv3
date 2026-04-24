<template>
  <div class="proposal-actions">
    <textarea
      v-model="reason"
      class="proposal-actions__field"
      rows="2"
      placeholder="审阅理由，可留空走默认值"
    />
    <ProposalClaimDiffEditor
      v-if="showDiffEditor"
      :item="item"
      :anchor-options="anchorOptions"
      @submit="onDiffSubmit"
      @cancel="showDiffEditor = false"
    />
    <div class="proposal-actions__buttons">
      <button
        type="button"
        :disabled="busy"
        @click="emitReview('approve', '通过')"
      >
        通过
      </button>
      <button
        type="button"
        :disabled="busy"
        @click="emitReview('approve_with_edits', '编辑后通过')"
      >
        编辑后通过
      </button>
      <button
        type="button"
        :disabled="busy"
        @click="emitReview('reject', '驳回')"
      >
        驳回
      </button>
      <button
        type="button"
        :disabled="busy"
        @click="emitReview('mark_uncertain', '标记不确定')"
      >
        不确定
      </button>
      <button
        type="button"
        :disabled="busy"
        @click="$emit('split', buildReason('拆分审阅'))"
      >
        拆分
      </button>
      <button
        v-if="canRollback && approvalReviewId"
        type="button"
        :disabled="busy"
        @click="$emit('rollback', approvalReviewId, buildReason('回滚审批'))"
      >
        回滚
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ProposalClaimDiffEditor from './ProposalClaimDiffEditor.vue'
import type { ProposalItem, ProposalReviewRequest } from '../../api/types'

const props = defineProps<{
  busy: boolean
  approvalReviewId: string | null
  canRollback: boolean
  item: ProposalItem
  reviewerRef: string
  anchorOptions: string[]
}>()

const emit = defineEmits<{
  review: [payload: ProposalReviewRequest]
  split: [reason: string]
  rollback: [reviewId: string, reason: string]
}>()

const reason = ref('')
const showDiffEditor = ref(false)
const pendingEditedFields = ref<Record<string, unknown>>({})

function buildReason(fallback: string) {
  return reason.value.trim() || fallback
}

function emitReview(action: ProposalReviewRequest['action'], fallbackReason: string) {
  if (action === 'approve_with_edits' && !showDiffEditor.value) {
    showDiffEditor.value = true
    return
  }
  emit('review', {
    reviewer_ref: props.reviewerRef,
    action,
    reason: buildReason(fallbackReason),
    evidence_refs: [],
    edited_fields: action === 'approve_with_edits' ? pendingEditedFields.value : {},
  })
  showDiffEditor.value = false
}

function onDiffSubmit(editedFields: Record<string, unknown>) {
  pendingEditedFields.value = editedFields
  emitReview('approve_with_edits', '编辑后通过')
}
</script>

<style scoped>
.proposal-actions {
  display: grid;
  gap: 0.6rem;
}

.proposal-actions__field {
  width: 100%;
  border: 1px solid rgba(111, 69, 31, 0.14);
  border-radius: 0.8rem;
  padding: 0.65rem 0.75rem;
  background: rgba(255, 252, 246, 0.92);
  color: var(--color-text-primary);
  font-size: 0.78rem;
  resize: vertical;
}

.proposal-actions__buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.proposal-actions__buttons button {
  border: 1px solid rgba(111, 69, 31, 0.18);
  border-radius: 999px;
  padding: 0.38rem 0.72rem;
  background: rgba(255, 252, 246, 0.92);
  color: var(--accent-strong);
  font-size: 0.76rem;
  font-weight: 700;
}

.proposal-actions__buttons button:disabled {
  opacity: 0.5;
}
</style>
