<template>
  <article class="proposal-item-card" data-testid="world-proposal-item-card">
    <header class="proposal-item-card__header">
      <div>
        <p class="proposal-item-card__claim">{{ item.subject_ref }}.{{ item.predicate }}</p>
        <h4 class="proposal-item-card__value">{{ renderValue(item.object_ref_or_value) }}</h4>
      </div>
      <div class="proposal-item-card__meta">
        <span>{{ item.item_status }}</span>
        <span>置信度 {{ item.confidence.toFixed(2) }}</span>
      </div>
    </header>

    <p class="proposal-item-card__submeta">
      {{ item.claim_id }} / {{ item.authority_type }}
    </p>

    <WorldProposalActionPanel
      :busy="busy"
      :approval-review-id="approvalReviewId"
      :can-rollback="item.item_status !== 'rolled_back'"
      @review="forwardReview"
      @split="forwardSplit"
      @rollback="forwardRollback"
    />
  </article>
</template>

<script setup lang="ts">
import WorldProposalActionPanel from './WorldProposalActionPanel.vue'
import type { ProposalItem, ProposalReviewRequest } from '../../api/types'

const props = defineProps<{
  item: ProposalItem
  busy: boolean
  approvalReviewId: string | null
}>()

const emit = defineEmits<{
  review: [itemId: string, payload: ProposalReviewRequest]
  split: [bundleId: string, itemId: string, reason: string]
  rollback: [reviewId: string, reason: string, itemId: string]
}>()

function renderValue(value: unknown) {
  return typeof value === 'string' ? value : JSON.stringify(value)
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
  color: var(--ink-muted);
  font-size: 0.76rem;
}

.proposal-item-card__value {
  margin: 0.12rem 0 0;
  color: var(--ink-strong);
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
</style>
