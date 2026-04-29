<script setup lang="ts">
import { computed } from 'vue'
import BaseButton from '../base/BaseButton.vue'
import type { WorldModelDashboard } from '../../api/types'
import type { AthenaSection } from '../../stores/ui'

const props = defineProps<{
  dashboard: WorldModelDashboard | null
  loading?: boolean
}>()

const emit = defineEmits<{
  navigate: [section: AthenaSection]
}>()

const metrics = computed(() => props.dashboard?.metrics ?? {
  entity_count: 0,
  fact_count: 0,
  presence_count: 0,
  event_count: 0,
  pending_bundle_count: 0,
  pending_item_count: 0,
})

const metricItems = computed(() => [
  { label: '实体', value: metrics.value.entity_count },
  { label: '事实', value: metrics.value.fact_count },
  { label: '在场', value: metrics.value.presence_count },
  { label: '事件', value: metrics.value.event_count },
  { label: '待审包', value: metrics.value.pending_bundle_count },
  { label: '待审条目', value: metrics.value.pending_item_count },
])

const profileLabel = computed(() => {
  if (!props.dashboard?.project_profile) return '未导入 world-model'
  return `Profile v${props.dashboard.project_profile.version}`
})

const nextActionLabel = computed(() => props.dashboard?.next_action.label ?? '等待世界模型初始化')

const nextActionSection = computed<AthenaSection>(() => {
  const action = props.dashboard?.next_action.action
  if (action === 'review_proposals') return 'proposals'
  if (action === 'inspect_projection') return 'projection'
  return 'characters'
})

function goNext() {
  emit('navigate', nextActionSection.value)
}
</script>

<template>
  <section class="athena-overview">
    <header class="athena-overview__header">
      <div>
        <p class="athena-overview__eyebrow">{{ profileLabel }}</p>
        <h2 class="athena-overview__title">世界模型总览</h2>
      </div>
      <BaseButton
        data-testid="athena-overview-next-action"
        size="sm"
        :loading="loading"
        @click="goNext"
      >
        {{ nextActionLabel }}
      </BaseButton>
    </header>

    <div class="athena-overview__metrics">
      <div v-for="item in metricItems" :key="item.label" class="athena-overview__metric">
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </div>
    </div>

    <div class="athena-overview__status">
      <span>下一步</span>
      <strong>{{ nextActionLabel }}</strong>
    </div>
  </section>
</template>

<style scoped>
.athena-overview {
  height: 100%;
  overflow: auto;
  padding: var(--space-4);
}

.athena-overview__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.athena-overview__eyebrow {
  margin-bottom: var(--space-1);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.athena-overview__title {
  color: var(--color-text-primary);
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
}

.athena-overview__metrics {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: var(--space-3);
  padding: var(--space-4) 0;
}

.athena-overview__metric {
  min-width: 0;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.athena-overview__metric span,
.athena-overview__status span {
  display: block;
  margin-bottom: var(--space-1);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.athena-overview__metric strong {
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.athena-overview__status {
  padding-top: var(--space-2);
}

.athena-overview__status strong {
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

@media (max-width: 980px) {
  .athena-overview__header {
    display: grid;
  }

  .athena-overview__metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
