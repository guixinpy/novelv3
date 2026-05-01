<script setup lang="ts">
import { computed } from 'vue'
import WorldProposalBundleList from '../world/WorldProposalBundleList.vue'
import WorldProposalImpactList from '../world/WorldProposalImpactList.vue'
import WorldProposalItemCard from '../world/WorldProposalItemCard.vue'
import { useWorldModelStore } from '../../stores/worldModel'
import type { ProposalItem, ProposalReviewRequest } from '../../api/types'

const props = defineProps<{
  projectId: string
}>()

const worldModel = useWorldModelStore()

const proposalLoading = computed(() =>
  worldModel.isLaneLoading('bundles') || worldModel.isLaneLoading('detail'),
)

function approvalReviewId(item: ProposalItem) {
  const review = worldModel.selectedBundleDetail?.reviews.find((entry) =>
    entry.proposal_item_id === item.id && Boolean(entry.created_truth_claim_id),
  )
  return review?.id || null
}

async function selectBundle(bundleId: string) {
  await worldModel.selectBundle(props.projectId, bundleId)
}

async function loadMore() {
  await worldModel.loadMoreBundles(props.projectId)
}

async function updateFilters(filters: typeof worldModel.bundleFilters) {
  await worldModel.applyBundleFilters(props.projectId, filters)
}

async function reviewItem(itemId: string, payload: ProposalReviewRequest) {
  await worldModel.reviewProposalItem(props.projectId, itemId, payload)
}

async function splitItem(bundleId: string, itemId: string, reason: string) {
  await worldModel.splitProposalBundle(props.projectId, bundleId, {
    reviewer_ref: worldModel.reviewerName,
    reason,
    evidence_refs: [],
    item_ids: [itemId],
  })
}

async function rollbackItem(reviewId: string, reason: string, itemId: string) {
  await worldModel.rollbackProposalReview(props.projectId, reviewId, {
    reviewer_ref: worldModel.reviewerName,
    reason,
    evidence_refs: [],
  }, itemId)
}

function bundleStatusLabel(status: string) {
  const labels: Record<string, string> = {
    pending: '待审',
    partially_approved: '部分通过',
    approved: '已通过',
    rejected: '已驳回',
    uncertain: '不确定',
    rolled_back: '已回滚',
    split: '已拆分',
  }
  return labels[status] || status
}
</script>

<template>
  <div class="proposal-workbench">
    <WorldProposalBundleList
      :bundles="worldModel.proposalBundles"
      :selected-bundle-id="worldModel.selectedBundleId"
      :total="worldModel.bundlesTotal"
      :filters="worldModel.bundleFilters"
      :loading="proposalLoading && worldModel.proposalBundles.length === 0"
      :loading-more="worldModel.loadingMoreBundles"
      @select="selectBundle"
      @load-more="loadMore"
      @update-filters="updateFilters"
    />

    <section class="proposal-workbench__detail">
      <div v-if="worldModel.error" class="proposal-workbench__error">{{ worldModel.error }}</div>
      <div v-if="proposalLoading" class="proposal-workbench__empty">加载提案...</div>
      <template v-else-if="worldModel.selectedBundleDetail">
        <header class="proposal-workbench__header">
          <div>
            <h3 class="proposal-workbench__title">{{ worldModel.selectedBundleDetail.bundle.title }}</h3>
            <p class="proposal-workbench__summary">{{ worldModel.selectedBundleDetail.bundle.summary || '无摘要' }}</p>
          </div>
          <span class="proposal-workbench__status">{{ bundleStatusLabel(worldModel.selectedBundleDetail.bundle.bundle_status) }}</span>
        </header>

        <WorldProposalImpactList :snapshots="worldModel.selectedBundleDetail.impact_snapshots" />
        <WorldProposalItemCard
          v-for="item in worldModel.selectedBundleDetail.items"
          :key="item.id"
          :item="item"
          :busy="worldModel.isActionPending(item.id)"
          :approval-review-id="approvalReviewId(item)"
          :reviewer-ref="worldModel.reviewerName"
          :anchor-options="[]"
          :conflicts="worldModel.selectedBundleDetail.conflicts"
          @review="reviewItem"
          @split="splitItem"
          @rollback="rollbackItem"
        />
      </template>
      <div v-else class="proposal-workbench__empty">暂无选中的提案。</div>
    </section>
  </div>
</template>

<style scoped>
.proposal-workbench {
  display: grid;
  grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
  gap: var(--space-4);
  height: 100%;
  overflow: hidden;
  padding: var(--space-4);
}

.proposal-workbench__detail {
  min-width: 0;
  overflow: auto;
  display: grid;
  align-content: start;
  gap: var(--space-3);
}

.proposal-workbench__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.proposal-workbench__title {
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.proposal-workbench__summary {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.proposal-workbench__status {
  color: var(--color-brand);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.proposal-workbench__error {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-sm);
  color: var(--color-error);
  background: var(--color-error-light);
  font-size: var(--text-sm);
}

.proposal-workbench__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

@media (max-width: 980px) {
  .proposal-workbench {
    grid-template-columns: minmax(0, 1fr);
    overflow: auto;
  }
}
</style>
