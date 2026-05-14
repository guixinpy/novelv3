<script setup lang="ts">
import { computed } from 'vue'
import type { ProposalBundle, ProposalBundleDetail } from '../../api/types'

type ReviewInsightView = 'impact' | 'history'

const props = defineProps<{
  detail: ProposalBundleDetail | null
  bundles: ProposalBundle[]
  view: ReviewInsightView
}>()

const latestImpact = computed(() => props.detail?.impact_snapshots?.[0] ?? null)
const reviewRows = computed(() => props.detail?.reviews || [])
const bundleRows = computed(() => props.bundles.slice(0, 20))

const metrics = computed(() => [
  { label: '候选项', value: props.detail?.items_total ?? props.detail?.items.length ?? 0 },
  { label: '影响主体', value: latestImpact.value?.affected_subject_refs.length ?? 0 },
  { label: '审阅记录', value: reviewRows.value.length },
])

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return '无'
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  try {
    return JSON.stringify(value, (_key, entry) => typeof entry === 'bigint' ? String(entry) : entry)
  } catch (_error) {
    return String(value)
  }
}

function statusLabel(status: string) {
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
  <section class="review-insight">
    <div class="review-insight__metrics">
      <div v-for="metric in metrics" :key="metric.label" class="review-insight__metric">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
      </div>
    </div>

    <template v-if="view === 'impact'">
      <article v-if="latestImpact" class="review-insight__card">
        <header>
          <span>影响快照</span>
          <strong>{{ latestImpact.created_at || '未记录时间' }}</strong>
        </header>
        <dl>
          <dt>候选项</dt>
          <dd>{{ latestImpact.candidate_item_ids.length }}</dd>
          <dt>影响主体</dt>
          <dd>{{ latestImpact.affected_subject_refs.join(' / ') || '无' }}</dd>
          <dt>影响谓词</dt>
          <dd>{{ latestImpact.affected_predicates.join(' / ') || '无' }}</dd>
          <dt>既有真相</dt>
          <dd>{{ latestImpact.affected_truth_claim_ids.join(' / ') || '无' }}</dd>
          <dt>摘要</dt>
          <dd>{{ formatValue(latestImpact.summary) }}</dd>
        </dl>
      </article>
      <div v-else class="review-insight__empty">尚未生成影响快照</div>
    </template>

    <template v-else>
      <section class="review-insight__history">
        <h3>提案批次</h3>
        <article v-for="bundle in bundleRows" :key="bundle.id" class="review-insight__line">
          <span>{{ statusLabel(bundle.bundle_status) }}</span>
          <strong>{{ bundle.title }}</strong>
          <p>{{ bundle.summary || bundle.created_at }}</p>
        </article>
        <div v-if="bundleRows.length === 0" class="review-insight__empty">暂无提案批次</div>
      </section>

      <section class="review-insight__history">
        <h3>当前批次审阅</h3>
        <article v-for="review in reviewRows" :key="review.id" class="review-insight__line">
          <span>{{ review.review_action }}</span>
          <strong>{{ review.reviewer_ref }}</strong>
          <p>{{ review.reason || review.created_at }}</p>
        </article>
        <div v-if="reviewRows.length === 0" class="review-insight__empty">当前批次暂无审阅记录</div>
      </section>
    </template>
  </section>
</template>

<style scoped>
.review-insight {
  height: 100%;
  overflow: auto;
  padding: var(--space-4);
}

.review-insight__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.review-insight__metric {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-2);
}

.review-insight__metric span,
.review-insight__card header span,
.review-insight__card dt,
.review-insight__line span {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.review-insight__metric strong {
  color: var(--color-text-primary);
  font-size: var(--text-lg);
}

.review-insight__card,
.review-insight__history {
  display: grid;
  gap: var(--space-3);
}

.review-insight__card header {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
}

.review-insight__card header strong,
.review-insight__history h3,
.review-insight__line strong {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
}

.review-insight__card dl {
  display: grid;
  grid-template-columns: minmax(80px, auto) minmax(0, 1fr);
  gap: var(--space-2);
}

.review-insight__card dd,
.review-insight__line p {
  overflow-wrap: anywhere;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.review-insight__history {
  margin-bottom: var(--space-5);
}

.review-insight__line {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-3);
}

.review-insight__line strong {
  display: block;
  margin: var(--space-1) 0;
}

.review-insight__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

@media (max-width: 760px) {
  .review-insight__metrics {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
