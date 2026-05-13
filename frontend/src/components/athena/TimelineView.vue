<script setup lang="ts">
import type { AthenaTimeline } from '../../api/types'

type AthenaTimelineEvent = AthenaTimeline['events'][number] & {
  event?: string
  timestamp?: string
  chapter_ref?: string | number
}

defineProps<{
  events: AthenaTimelineEvent[]
  anchors?: AthenaTimeline['anchors']
  loading?: boolean
  fallbackSummary?: {
    chapters: number
    plotlines: number
    foreshadowing: number
  }
}>()

function chapterLabel(event: AthenaTimelineEvent) {
  const chapter = event.chapter_ref ?? event.chapter_index
  return chapter ? `第${chapter}章` : ''
}

function eventTypeLabel(event: AthenaTimelineEvent) {
  return event.event_type === 'chapter_plan' ? '章节规划' : ''
}
</script>

<template>
  <div class="timeline-view">
    <div v-if="loading && events.length === 0" class="timeline-view__empty">
      <strong>正在读取叙事时间线...</strong>
    </div>
    <div v-else-if="events.length === 0" class="timeline-view__empty">
      <strong>暂无时间线数据</strong>
      <span v-if="fallbackSummary && (fallbackSummary.chapters || fallbackSummary.plotlines || fallbackSummary.foreshadowing)">
        已生成 {{ fallbackSummary.chapters }} 章规划、{{ fallbackSummary.plotlines }} 条故事线、{{ fallbackSummary.foreshadowing }} 条伏笔，可切换到对应标签查看。
      </span>
    </div>
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
        <div v-if="chapterLabel(event) || event.timestamp || eventTypeLabel(event)" class="timeline-view__meta">
          <span v-if="chapterLabel(event)">{{ chapterLabel(event) }}</span>
          <span v-if="eventTypeLabel(event)">{{ eventTypeLabel(event) }}</span>
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
  display: grid;
  gap: var(--space-2);
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.timeline-view__empty strong {
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
}
</style>
