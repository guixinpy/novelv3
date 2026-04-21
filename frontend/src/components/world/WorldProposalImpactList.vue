<template>
  <section class="impact-list" data-testid="world-proposal-impact-list">
    <header class="impact-list__header">
      <div>
        <p class="impact-list__eyebrow">Impact Snapshot</p>
        <h3 class="impact-list__title">影响范围</h3>
      </div>
      <span v-if="isHighRisk" class="impact-list__risk">高风险变更</span>
    </header>

    <div v-if="latestSnapshot" class="impact-list__body">
      <p>候选数：{{ candidateCount }}</p>
      <p>覆盖现有 truth：{{ existingTruthCount }}</p>
      <p>主体：{{ latestSnapshot.affected_subject_refs.join(' / ') || '无' }}</p>
      <p>谓词：{{ latestSnapshot.affected_predicates.join(' / ') || '无' }}</p>
    </div>
    <p v-else class="impact-list__empty">尚未生成 impact snapshot。</p>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ProposalImpactSnapshot } from '../../api/types'

const props = defineProps<{
  snapshots: ProposalImpactSnapshot[]
}>()

const latestSnapshot = computed(() => props.snapshots[0] ?? null)
const candidateCount = computed(() => Number(latestSnapshot.value?.summary.candidate_count ?? 0))
const existingTruthCount = computed(() => Number(latestSnapshot.value?.summary.existing_truth_count ?? 0))
const isHighRisk = computed(() => candidateCount.value > 1 || existingTruthCount.value > 0)
</script>

<style scoped>
.impact-list {
  display: grid;
  gap: 0.7rem;
  border: 1px solid rgba(164, 84, 48, 0.18);
  border-radius: 1rem;
  padding: 1rem;
  background: rgba(248, 239, 229, 0.84);
}

.impact-list__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.8rem;
}

.impact-list__eyebrow {
  margin: 0;
  color: var(--ink-muted);
  font-size: 0.72rem;
}

.impact-list__title {
  margin: 0.12rem 0 0;
  color: var(--accent-strong);
  font-size: 0.96rem;
}

.impact-list__risk {
  border-radius: 999px;
  padding: 0.3rem 0.72rem;
  background: rgba(156, 61, 36, 0.12);
  color: #8d341f;
  font-size: 0.74rem;
  font-weight: 700;
}

.impact-list__body,
.impact-list__empty {
  color: var(--ink-muted);
  font-size: 0.8rem;
  line-height: 1.55;
}

.impact-list__body p {
  margin: 0;
}
</style>
