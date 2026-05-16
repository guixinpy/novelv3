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
const reviewQueueClusters = computed(() => worldModel.proposalReviewQueue?.clusters ?? [])
const reviewQueueLoadedItems = computed(() =>
  worldModel.proposalReviewQueue?.returned_items
  ?? reviewQueueClusters.value.reduce((total, cluster) => total + Math.max(0, cluster.candidate_count), 0),
)
const canLoadMoreReviewQueue = computed(() => Boolean(worldModel.proposalReviewQueue?.has_more))
const selectedBundleDetail = computed(() => worldModel.selectedBundleDetail)
const detailItemTotal = computed(() =>
  selectedBundleDetail.value?.items_total ?? selectedBundleDetail.value?.items.length ?? 0,
)
const visibleProposalItems = computed(() => selectedBundleDetail.value?.items ?? [])
const canShowMoreProposalItems = computed(() => visibleProposalItems.value.length < detailItemTotal.value)

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

async function showMoreProposalItems() {
  await worldModel.loadMoreBundleDetailItems(props.projectId)
}

async function loadMoreReviewQueue() {
  await worldModel.loadMoreProposalReviewQueue(props.projectId)
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

function riskLabel(level: string) {
  const labels: Record<string, string> = {
    high: '高风险',
    medium: '中风险',
    low: '低风险',
  }
  return labels[level] || level
}

function reviewModeLabel(mode: string) {
  const labels: Record<string, string> = {
    individual: '单独审阅',
    batch: '批量审阅',
  }
  return labels[mode] || mode
}

function chapterRangeLabel(range: { start: number | null; end: number | null }) {
  if (range.start === null && range.end === null) return '全书范围'
  if (range.start === range.end) return `第${range.start}章`
  return `第${range.start ?? '?'}-${range.end ?? '?'}章`
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
      <section v-if="worldModel.proposalReviewQueue" class="proposal-workbench__queue" aria-label="提案审阅队列">
        <header class="proposal-workbench__queue-header">
          <div>
            <span>审阅队列</span>
            <strong>{{ worldModel.proposalReviewQueue.total_items }} 个待处理条目</strong>
            <small v-if="worldModel.proposalReviewQueue.total_items > reviewQueueLoadedItems">
              已显示 {{ reviewQueueLoadedItems }}/{{ worldModel.proposalReviewQueue.total_items }} 项
            </small>
          </div>
          <div class="proposal-workbench__queue-actions">
            <em>{{ reviewQueueClusters.length }} 组</em>
            <button
              v-if="canLoadMoreReviewQueue"
              type="button"
              data-testid="load-more-proposal-review-queue"
              :disabled="worldModel.loadingMoreProposalReviewQueue"
              @click="loadMoreReviewQueue"
            >
              {{ worldModel.loadingMoreProposalReviewQueue ? '加载中...' : '加载更多' }}
            </button>
          </div>
        </header>
        <ol v-if="reviewQueueClusters.length" class="proposal-workbench__queue-list">
          <li v-for="cluster in reviewQueueClusters" :key="cluster.cluster_id" class="proposal-workbench__queue-item">
            <span>{{ riskLabel(cluster.risk_level) }}</span>
            <strong>{{ reviewModeLabel(cluster.review_mode) }} · {{ cluster.candidate_count }} 项</strong>
            <small>{{ cluster.predicate }} · {{ chapterRangeLabel(cluster.chapter_range) }}</small>
          </li>
        </ol>
        <p v-else class="proposal-workbench__queue-empty">当前没有待审候选事实。</p>
      </section>

      <div v-if="worldModel.error" class="proposal-workbench__error">{{ worldModel.error }}</div>
      <div v-if="proposalLoading" class="proposal-workbench__empty">加载提案...</div>
      <template v-else-if="selectedBundleDetail">
        <header class="proposal-workbench__header">
          <div>
            <h3 class="proposal-workbench__title">{{ selectedBundleDetail.bundle.title }}</h3>
            <p class="proposal-workbench__summary">{{ selectedBundleDetail.bundle.summary || '无摘要' }}</p>
          </div>
          <span class="proposal-workbench__status">{{ bundleStatusLabel(selectedBundleDetail.bundle.bundle_status) }}</span>
        </header>

        <WorldProposalImpactList :snapshots="selectedBundleDetail.impact_snapshots" />
        <div v-if="detailItemTotal > visibleProposalItems.length || detailItemTotal > 100" class="proposal-workbench__item-window">
          <span>已显示 {{ visibleProposalItems.length }}/{{ detailItemTotal }} 项</span>
          <button
            v-if="canShowMoreProposalItems"
            type="button"
            data-testid="show-more-proposal-items"
            :disabled="worldModel.loadingMoreBundleItems"
            @click="showMoreProposalItems"
          >
            {{ worldModel.loadingMoreBundleItems ? '加载中...' : '显示更多' }}
          </button>
        </div>
        <WorldProposalItemCard
          v-for="item in visibleProposalItems"
          :key="item.id"
          :item="item"
          :busy="worldModel.isActionPending(item.id)"
          :approval-review-id="approvalReviewId(item)"
          :reviewer-ref="worldModel.reviewerName"
          :anchor-options="[]"
          :conflicts="selectedBundleDetail.conflicts"
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

.proposal-workbench__item-window {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.proposal-workbench__item-window button {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-3);
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  cursor: pointer;
}

.proposal-workbench__error {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-sm);
  color: var(--color-error);
  background: var(--color-error-light);
  font-size: var(--text-sm);
}

.proposal-workbench__queue {
  display: grid;
  gap: var(--space-3);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.proposal-workbench__queue-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
}

.proposal-workbench__queue-header span,
.proposal-workbench__queue-header small,
.proposal-workbench__queue-header em,
.proposal-workbench__queue-item span,
.proposal-workbench__queue-item small,
.proposal-workbench__queue-empty {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  font-style: normal;
}

.proposal-workbench__queue-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  justify-content: flex-end;
}

.proposal-workbench__queue-actions button {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-3);
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  cursor: pointer;
}

.proposal-workbench__queue-actions button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.proposal-workbench__queue-header strong,
.proposal-workbench__queue-item strong {
  display: block;
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.proposal-workbench__queue-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.proposal-workbench__queue-item {
  display: grid;
  gap: 2px;
  min-width: 0;
  padding: var(--space-2) 0;
  border-bottom: 1px solid var(--color-border);
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
