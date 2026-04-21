<template>
  <p
    v-if="worldModelError"
    class="setup-tab__error"
    data-testid="world-model-error"
  >
    {{ worldModelError }}
  </p>
  <div v-else-if="showWorldModel" class="setup-tab setup-tab--world" data-testid="world-model-view">
    <WorldProfileBanner v-if="worldModel.projectProfile" :profile="worldModel.projectProfile" />
    <WorldProjectionViewer v-if="worldModel.projection" :projection="worldModel.projection" />

    <div class="setup-tab__world-grid">
      <WorldProposalBundleList
        :bundles="worldModel.proposalBundles"
        :selected-bundle-id="worldModel.selectedBundleId"
        @select="selectBundle"
      />

      <section class="setup-tab__world-detail">
        <WorldProposalImpactList
          :snapshots="worldModel.selectedBundleDetail?.impact_snapshots ?? []"
        />

        <article
          v-if="worldModel.selectedBundleDetail"
          class="setup-tab__proposal-items"
        >
          <header class="setup-tab__proposal-header">
            <div>
              <p class="setup-tab__proposal-eyebrow">Proposal Review</p>
              <h3 class="setup-tab__proposal-title">
                {{ worldModel.selectedBundleDetail.bundle.title }}
              </h3>
            </div>
            <span class="setup-tab__proposal-status">
              {{ worldModel.selectedBundleDetail.bundle.bundle_status }}
            </span>
          </header>

          <WorldProposalItemCard
            v-for="item in worldModel.selectedBundleDetail.items"
            :key="item.id"
            :item="item"
            :busy="worldModel.isActionPending(item.id)"
            :approval-review-id="approvalReviewIdMap[item.id] ?? null"
            @review="reviewItem"
            @split="splitItem"
            @rollback="rollbackReview"
          />
        </article>
        <p v-else class="setup-tab__world-empty">当前没有待审条目。</p>
      </section>
    </div>
  </div>
  <div v-else-if="shouldShowFallback && setup" class="setup-tab">
    <SetupSummaryCard
      title="角色"
      :description="characterDescription"
      test-id="setup-summary-card-characters"
      body-test-id="setup-summary-card-characters-body"
      @open="openDetail('characters')"
    >
      <ul v-if="characterSummary.entries.length > 0" class="setup-summary-list" aria-label="角色概览">
        <li
          v-for="(entry, index) in characterSummary.entries"
          :key="`${entry.name}-${index}`"
          class="setup-summary-list__item"
        >
          <div class="setup-summary-list__headline">
            <span class="setup-summary-list__label">{{ entry.name }}</span>
            <span v-if="entry.meta?.length" class="setup-summary-list__meta">{{ entry.meta.join(' / ') }}</span>
          </div>
          <p class="setup-summary-list__value">{{ entry.summary }}</p>
        </li>
      </ul>
      <p
        v-else
        class="setup-summary-empty"
        data-testid="setup-summary-card-characters-empty"
      >
        暂无角色概览
      </p>
    </SetupSummaryCard>

    <SetupSummaryCard
      title="世界观"
      test-id="setup-summary-card-world"
      body-test-id="setup-summary-card-world-body"
      @open="openDetail('world')"
    >
      <ul v-if="worldSummary.length > 0" class="setup-summary-list" aria-label="世界观概览">
        <li
          v-for="(item, index) in worldSummary"
          :key="`${item.label}-${index}`"
          class="setup-summary-list__item"
        >
          <div class="setup-summary-list__headline">
            <span class="setup-summary-list__label">{{ item.label }}</span>
          </div>
          <p class="setup-summary-list__value">{{ item.value }}</p>
        </li>
      </ul>
      <p
        v-else
        class="setup-summary-empty"
        data-testid="setup-summary-card-world-empty"
      >
        世界观待补充
      </p>
    </SetupSummaryCard>

    <SetupSummaryCard
      title="核心概念"
      test-id="setup-summary-card-concept"
      body-test-id="setup-summary-card-concept-body"
      @open="openDetail('concept')"
    >
      <ul v-if="conceptSummary.length > 0" class="setup-summary-list" aria-label="核心概念概览">
        <li
          v-for="(item, index) in conceptSummary"
          :key="`${item.label}-${index}`"
          class="setup-summary-list__item"
        >
          <div class="setup-summary-list__headline">
            <span class="setup-summary-list__label">{{ item.label }}</span>
          </div>
          <p class="setup-summary-list__value">{{ item.value }}</p>
        </li>
      </ul>
      <p
        v-else
        class="setup-summary-empty"
        data-testid="setup-summary-card-concept-empty"
      >
        核心概念待补充
      </p>
    </SetupSummaryCard>

    <SetupDetailModal
      :show="isDetailModalOpen"
      :setup="setup"
      :initial-section="detailModalSection"
      @close="isDetailModalOpen = false"
    />
  </div>
  <p v-else-if="isWaitingForWorldModel" class="setup-tab__empty">加载世界模型视图...</p>
  <p v-else class="setup-tab__empty">暂无设定数据。</p>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { ProposalReviewRequest, SetupData } from '../../api/types'
import { useWorldModelStore } from '../../stores/worldModel'
import WorldProfileBanner from '../world/WorldProfileBanner.vue'
import WorldProjectionViewer from '../world/WorldProjectionViewer.vue'
import WorldProposalBundleList from '../world/WorldProposalBundleList.vue'
import WorldProposalImpactList from '../world/WorldProposalImpactList.vue'
import WorldProposalItemCard from '../world/WorldProposalItemCard.vue'
import SetupDetailModal from './SetupDetailModal.vue'
import SetupSummaryCard from './SetupSummaryCard.vue'
import {
  buildCharacterSummaryItems,
  buildConceptSummaryItems,
  buildWorldSummaryItems,
} from './setupSummaryPresentation'

type SetupSection = 'characters' | 'world' | 'concept'

const props = defineProps<{
  projectId?: string
  setup: SetupData | null
}>()

const worldModel = useWorldModelStore()
const isDetailModalOpen = ref(false)
const detailModalSection = ref<SetupSection>('characters')

const characterSummary = computed(() => buildCharacterSummaryItems(props.setup?.characters ?? []))
const worldSummary = computed(() => {
  if (!props.setup) {
    return []
  }

  return buildWorldSummaryItems(props.setup.world_building)
})
const conceptSummary = computed(() => {
  if (!props.setup) {
    return []
  }

  return buildConceptSummaryItems(props.setup.core_concept)
})
const characterDescription = computed(() => {
  const count = characterSummary.value.count

  if (count <= 0) {
    return '暂无角色概览'
  }

  return `共 ${count} 名角色`
})

const worldModelError = computed(() => worldModel.error.trim())
const showWorldModel = computed(() => worldModel.hasWorldData && !worldModelError.value)
const isWaitingForWorldModel = computed(() =>
  Boolean(props.projectId)
    && !worldModelError.value
    && !worldModel.loaded
    && worldModel.loading
    && !showWorldModel.value,
)
const shouldShowFallback = computed(() =>
  !showWorldModel.value && (!props.projectId || worldModel.loaded || !worldModel.loading),
)
const approvalReviewIdMap = computed<Record<string, string>>(() => {
  const reviews = worldModel.selectedBundleDetail?.reviews ?? []
  return reviews.reduce<Record<string, string>>((acc, review) => {
    if (
      review.proposal_item_id &&
      (review.review_action === 'approve' || review.review_action === 'approve_with_edits')
    ) {
      acc[review.proposal_item_id] = review.id
    }
    return acc
  }, {})
})

watch(() => props.setup?.id, () => {
  isDetailModalOpen.value = false
  detailModalSection.value = 'characters'
})

watch(
  () => props.projectId,
  (projectId, previousProjectId) => {
    if (!projectId) return
    if (projectId !== previousProjectId) {
      worldModel.resetProjectScopedState(projectId)
    }
    void worldModel.loadSetupPanelData(projectId)
  },
  { immediate: true },
)

watch(
  () => props.setup,
  (setup, previousSetup) => {
    if (!props.projectId || !setup || setup === previousSetup) return
    void worldModel.loadSetupPanelData(props.projectId)
  },
)

function openDetail(section: SetupSection): void {
  detailModalSection.value = section
  isDetailModalOpen.value = true
}

function selectBundle(bundleId: string) {
  if (!props.projectId) return
  void worldModel.selectBundle(props.projectId, bundleId)
}

function reviewItem(itemId: string, payload: ProposalReviewRequest) {
  if (!props.projectId) return
  void worldModel.reviewProposalItem(props.projectId, itemId, payload)
}

function splitItem(bundleId: string, itemId: string, reason: string) {
  if (!props.projectId) return
  void worldModel.splitProposalBundle(props.projectId, bundleId, {
    reviewer_ref: 'frontend.reviewer',
    reason,
    evidence_refs: [],
    item_ids: [itemId],
  })
}

function rollbackReview(reviewId: string, reason: string, itemId: string) {
  if (!props.projectId) return
  void worldModel.rollbackProposalReview(props.projectId, reviewId, {
    reviewer_ref: 'frontend.reviewer',
    reason,
    evidence_refs: [],
  }, itemId)
}
</script>

<style scoped>
.setup-tab {
  display: grid;
  gap: 0.85rem;
}

.setup-tab--world {
  gap: 1rem;
}

.setup-tab__world-grid {
  display: grid;
  gap: 1rem;
}

.setup-tab__world-detail,
.setup-tab__proposal-items {
  display: grid;
  gap: 0.85rem;
}

.setup-tab__proposal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
}

.setup-tab__proposal-eyebrow {
  margin: 0;
  color: var(--ink-muted);
  font-size: 0.72rem;
}

.setup-tab__proposal-title {
  margin: 0.12rem 0 0;
  color: var(--accent-strong);
  font-size: 0.96rem;
}

.setup-tab__proposal-status {
  border-radius: 999px;
  padding: 0.3rem 0.72rem;
  background: rgba(118, 74, 27, 0.08);
  color: var(--accent-strong);
  font-size: 0.74rem;
  font-weight: 700;
}

.setup-tab__world-empty {
  color: var(--ink-muted);
  font-size: 0.84rem;
}

.setup-tab__error {
  margin: 0;
  border: 1px solid rgba(163, 62, 38, 0.22);
  border-radius: 0.9rem;
  padding: 0.9rem 1rem;
  background: rgba(170, 78, 51, 0.08);
  color: #8a311c;
  font-size: 0.84rem;
  line-height: 1.5;
}

.setup-summary-list {
  display: grid;
  gap: 0.7rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.setup-summary-list__item {
  display: grid;
  gap: 0.2rem;
}

.setup-summary-list__headline {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  min-width: 0;
}

.setup-summary-list__label {
  color: var(--ink-strong);
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1.35;
}

.setup-summary-list__meta {
  color: var(--ink-muted);
  font-size: 0.74rem;
  line-height: 1.35;
}

.setup-summary-list__value {
  color: var(--ink-muted);
  font-size: 0.84rem;
  line-height: 1.55;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
}

.setup-summary-empty {
  color: var(--ink-muted);
  font-size: 0.84rem;
  line-height: 1.55;
}

.setup-tab__empty {
  padding: 1rem;
  color: var(--ink-muted);
  font-size: 0.875rem;
}

@media (min-width: 960px) {
  .setup-tab__world-grid {
    grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
    align-items: start;
  }
}
</style>
