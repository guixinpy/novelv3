<script setup lang="ts">
import { computed, ref } from 'vue'
import type { AthenaTimeline } from '../../api/types'

type AthenaTimelineEvent = AthenaTimeline['events'][number] & {
  event?: string
  timestamp?: string
  chapter_ref?: string | number
}

const props = defineProps<{
  events: AthenaTimelineEvent[]
  anchors?: AthenaTimeline['anchors']
  loading?: boolean
  fallbackSummary?: {
    chapters: number
    plotlines: number
    foreshadowing: number
  }
}>()

const showCompleted = ref(false)

const completedEvents = computed(() => props.events.length > 1 ? props.events.slice(0, -1) : [])
const visibleEvents = computed(() => {
  const events = completedEvents.value.length > 0 && !showCompleted.value
    ? props.events.slice(-1)
    : props.events
  const offset = props.events.length - events.length

  return events.map((event, index) => ({
    event,
    originalIndex: offset + index,
  }))
})

function chapterLabel(event: AthenaTimelineEvent) {
  const chapter = event.chapter_ref ?? event.chapter_index
  return chapter ? `第${chapter}章` : ''
}

function eventTypeLabel(event: AthenaTimelineEvent) {
  return event.event_type === 'chapter_plan' ? '章节规划' : ''
}

function toggleCompleted() {
  showCompleted.value = !showCompleted.value
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
    <button
      v-if="completedEvents.length"
      type="button"
      class="timeline-view__completed-toggle"
      data-testid="timeline-completed-toggle"
      :aria-expanded="showCompleted"
      @click="toggleCompleted"
    >
      {{ showCompleted ? '收起已完成节点' : `已收起前 ${completedEvents.length} 个已完成节点` }}
    </button>
    <div
      v-for="{ event, originalIndex } in visibleEvents"
      :key="event.id || originalIndex"
      class="timeline-view__item"
      :class="{ 'timeline-view__item--current': originalIndex === events.length - 1 }"
    >
      <div class="timeline-view__track">
        <span
          class="timeline-view__dot"
          :class="{ 'timeline-view__dot--current': originalIndex === events.length - 1 }"
        />
        <div v-if="originalIndex < events.length - 1" class="timeline-view__line" />
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

.timeline-view__completed-toggle {
  margin: 0 0 var(--space-3) 32px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-3);
  background: var(--color-bg-white);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  cursor: pointer;
}

.timeline-view__completed-toggle:hover {
  border-color: var(--color-brand);
  color: var(--color-brand);
}

.timeline-view__item {
  display: flex;
  gap: var(--space-4);
  min-height: 48px;
}

.timeline-view__item--current .timeline-view__content {
  border-left: 3px solid var(--color-brand);
  padding-left: var(--space-3);
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
