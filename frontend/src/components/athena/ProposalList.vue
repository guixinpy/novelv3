<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseBadge from '../base/BaseBadge.vue'
import WorldProposalImpactList from '../world/WorldProposalImpactList.vue'
import WorldProposalItemCard from '../world/WorldProposalItemCard.vue'
import { useAthenaStore } from '../../stores/athena'
import type { ProposalItem, ProposalReviewRequest } from '../../api/types'

const props = defineProps<{
  proposals: any
  projectId?: string
}>()

const athena = useAthenaStore()
const expandedId = ref<string | null>(null)

async function toggle(id: string) {
  expandedId.value = expandedId.value === id ? null : id
  if (expandedId.value && props.projectId && !athena.proposalDetails[id]) {
    await athena.loadProposalDetail(props.projectId, id)
  }
}

function bundleStatus(bundle: any) {
  return bundle.bundle_status || bundle.status || 'unknown'
}

function bundleItemCount(bundle: any) {
  const detail = athena.proposalDetails[bundle.id]
  if (detail) return `${detail.items.length} 项`
  return Array.isArray(bundle.items) ? `${bundle.items.length} 项` : ''
}

const activeDetail = computed(() => {
  if (!expandedId.value) return null
  return athena.proposalDetails[expandedId.value] || null
})

function approvalReviewId(item: ProposalItem) {
  const review = activeDetail.value?.reviews.find((entry) =>
    entry.proposal_item_id === item.id && Boolean(entry.created_truth_claim_id),
  )
  return review?.id || null
}

function itemBusy(itemId: string) {
  return Boolean(athena.proposalBusy[itemId])
}

async function reviewItem(itemId: string, payload: ProposalReviewRequest) {
  if (!props.projectId || !activeDetail.value) return
  await athena.reviewProposalItem(props.projectId, activeDetail.value.bundle.id, itemId, payload)
}

async function splitItem(bundleId: string, itemId: string, reason: string) {
  if (!props.projectId) return
  await athena.splitProposalItem(props.projectId, bundleId, itemId, reason)
}

async function rollbackItem(reviewId: string, reason: string, itemId: string) {
  if (!props.projectId || !activeDetail.value) return
  await athena.rollbackProposalReview(props.projectId, activeDetail.value.bundle.id, itemId, reviewId, reason)
}

async function batchApprove(bundleId: string) {
  if (!props.projectId) return
  await athena.batchApproveLowRiskItems(props.projectId, bundleId)
}

const statusVariant: Record<string, 'success' | 'warning' | 'error' | 'neutral'> = {
  draft: 'neutral',
  pending: 'warning',
  approved: 'success',
  rejected: 'error',
}
</script>

<template>
  <div class="proposal-list">
    <div v-if="!proposals?.items?.length" class="proposal-list__empty">暂无提案</div>
    <div
      v-for="bundle in (proposals?.items || [])"
      :key="bundle.id"
      class="proposal-list__item"
    >
      <button class="proposal-list__header" @click="toggle(bundle.id)">
        <span class="proposal-list__title">{{ bundle.title || bundle.id }}</span>
        <BaseBadge :variant="statusVariant[bundleStatus(bundle)] || 'neutral'" size="sm">
          {{ bundleStatus(bundle) }}
        </BaseBadge>
        <span v-if="bundleItemCount(bundle)" class="proposal-list__meta">{{ bundleItemCount(bundle) }}</span>
        <span class="proposal-list__chevron">{{ expandedId === bundle.id ? '▾' : '▸' }}</span>
      </button>
      <div v-if="expandedId === bundle.id" class="proposal-list__detail">
        <template v-if="athena.proposalDetails[bundle.id]">
          <div class="proposal-list__detail-toolbar">
            <button
              type="button"
              class="proposal-list__batch"
              data-testid="batch-approve-low-risk"
              @click="batchApprove(bundle.id)"
            >
              批量通过低风险项
            </button>
          </div>
          <WorldProposalImpactList :snapshots="athena.proposalDetails[bundle.id].impact_snapshots" />
          <WorldProposalItemCard
            v-for="item in athena.proposalDetails[bundle.id].items"
            :key="item.id"
            :item="item"
            :busy="itemBusy(item.id)"
            :approval-review-id="approvalReviewId(item)"
            reviewer-ref="athena.user"
            :anchor-options="[]"
            :conflicts="athena.proposalDetails[bundle.id].conflicts"
            @review="reviewItem"
            @split="splitItem"
            @rollback="rollbackItem"
          />
        </template>
        <div v-else class="proposal-list__detail-item">加载提案详情...</div>
      </div>
    </div>
  </div>
</template>
<style scoped>
.proposal-list__item {
  border-bottom: 1px solid var(--color-border);
}

.proposal-list__header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  width: 100%;
  padding: var(--space-3) 0;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.proposal-list__title {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
  flex: 1;
}

.proposal-list__meta {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.proposal-list__chevron {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.proposal-list__detail {
  display: grid;
  gap: var(--space-3);
  padding: 0 0 var(--space-3) var(--space-4);
}

.proposal-list__detail-toolbar {
  display: flex;
  justify-content: flex-end;
}

.proposal-list__batch {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-3);
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  cursor: pointer;
}

.proposal-list__detail-item {
  padding: var(--space-2) 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  border-bottom: 1px solid var(--color-border);
}

.proposal-list__detail-item:last-child {
  border-bottom: none;
}

.proposal-list__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
