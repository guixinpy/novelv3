<script setup lang="ts">
defineProps<{
  events: any[]
  anchors?: any[]
}>()
</script>

<template>
  <div class="timeline-view">
    <div v-if="events.length === 0" class="timeline-view__empty">暂无时间线数据</div>
    <div
      v-for="(event, index) in events"
      :key="index"
      class="timeline-view__item"
    >
      <div class="timeline-view__track">
        <span
          class="timeline-view__dot"
          :class="{ 'timeline-view__dot--current': index === events.length - 1 }"
        />
        <div v-if="index < events.length - 1" class="timeline-view__line" />
      </div>
      <div class="timeline-view__content">
        <div class="timeline-view__desc">{{ event.description || event.event || '' }}</div>
        <div v-if="event.chapter_ref || event.timestamp" class="timeline-view__meta">
          <span v-if="event.chapter_ref">第{{ event.chapter_ref }}章</span>
          <span v-if="event.timestamp">{{ event.timestamp }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.timeline-view {
  padding: var(--space-2) 0;
}
.timeline-view__item {
  display: flex;
  gap: var(--space-4);
  min-height: 48px;
}

.timeline-view__track {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 16px;
  flex-shrink: 0;
}

.timeline-view__dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-border);
  flex-shrink: 0;
  margin-top: 6px;
}

.timeline-view__dot--current {
  background: var(--color-brand);
}

.timeline-view__line {
  width: 2px;
  flex: 1;
  background: var(--color-border);
  margin-top: 4px;
}

.timeline-view__content {
  padding-bottom: var(--space-4);
}

.timeline-view__desc {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  line-height: var(--leading-normal);
}

.timeline-view__meta {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-1);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.timeline-view__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
