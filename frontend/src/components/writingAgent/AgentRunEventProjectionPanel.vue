<script setup lang="ts">
import { computed } from 'vue'
import {
  numberValue,
  recordList,
  recordValue,
  stringList,
  stringValue,
} from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const summary = computed(() => recordValue(props.output.summary))
const status = computed(() => stringValue(props.output.status))
const totalEventCount = computed(() => numberValue(summary.value.total))
const eventTypeSummary = computed(() => recordValue(summary.value.by_event_type))
const sourceTypeSummary = computed(() => recordValue(summary.value.by_source_type))
const backgroundTaskEventCount = computed(() => numberValue(sourceTypeSummary.value.background_task))
const runEventCount = computed(() => numberValue(sourceTypeSummary.value.writing_agent_run))
const stepEventCount = computed(() => numberValue(sourceTypeSummary.value.writing_agent_step))
const toolErrorCount = computed(() => numberValue(eventTypeSummary.value.tool_error))
const rows = computed(() => (
  recordList(props.output.events)
    .slice(0, 6)
    .map((event, index) => {
      const chapterIndex = numberValue(event.chapter_index)
      return {
        key: `agent-event-projection:${index}`,
        eventType: eventTypeLabel(event.event_type),
        sourceType: sourceTypeLabel(event.source_type),
        toolName: stringValue(event.tool_name),
        chapterLabel: chapterIndex !== null ? `第${chapterIndex}章` : '',
        status: statusLabel(event.status),
        errorPreview: stringValue(event.error_preview),
      }
    })
    .filter((event) => (
      event.eventType ||
      event.sourceType ||
      event.toolName ||
      event.chapterLabel ||
      event.status ||
      event.errorPreview
    ))
))
const recommendedTools = computed(() => uniqueStrings(stringList(props.output.recommended_tools)))

function uniqueStrings(values: string[]): string[] {
  return Array.from(new Set(values))
}

function statusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'completed' || statusValue === 'success') return '已完成'
  if (statusValue === 'running') return '进行中'
  if (statusValue === 'failed') return '失败'
  if (statusValue === 'blocked') return '已阻塞'
  return statusValue || '未知'
}

function eventTypeLabel(value: unknown) {
  const eventValue = stringValue(value)
  if (eventValue === 'task_created') return '任务创建'
  if (eventValue === 'task_started') return '任务开始'
  if (eventValue === 'task_completed') return '任务完成'
  if (eventValue === 'task_error') return '任务错误'
  if (eventValue === 'task_cancelled') return '任务取消'
  if (eventValue === 'run_created') return '运行创建'
  if (eventValue === 'run_started') return '运行开始'
  if (eventValue === 'run_completed') return '运行完成'
  if (eventValue === 'run_error') return '运行错误'
  if (eventValue === 'run_blocked') return '运行阻塞'
  if (eventValue === 'run_cancelled') return '运行取消'
  if (eventValue === 'tool_started') return '工具开始'
  if (eventValue === 'tool_completed') return '工具完成'
  if (eventValue === 'tool_error') return '工具错误'
  return eventValue || '未知事件'
}

function sourceTypeLabel(value: unknown) {
  const sourceValue = stringValue(value)
  if (sourceValue === 'background_task') return '后台任务'
  if (sourceValue === 'writing_agent_run') return 'Agent 运行'
  if (sourceValue === 'writing_agent_step') return '工具步骤'
  return sourceValue || '未知来源'
}
</script>

<template>
  <section
    class="agent-run-drawer__event-projection"
    aria-label="Agent event projection"
  >
    <h4>Agent 事件投影</h4>
    <dl class="agent-run-drawer__facts">
      <div v-if="status">
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
      </div>
      <div v-if="totalEventCount !== null">
        <dt>事件总数</dt>
        <dd>{{ totalEventCount }}</dd>
      </div>
      <div v-if="backgroundTaskEventCount !== null">
        <dt>后台任务事件</dt>
        <dd>{{ backgroundTaskEventCount }}</dd>
      </div>
      <div v-if="runEventCount !== null">
        <dt>运行事件</dt>
        <dd>{{ runEventCount }}</dd>
      </div>
      <div v-if="stepEventCount !== null">
        <dt>工具事件</dt>
        <dd>{{ stepEventCount }}</dd>
      </div>
      <div v-if="toolErrorCount !== null">
        <dt>工具错误</dt>
        <dd>{{ toolErrorCount }}</dd>
      </div>
    </dl>
    <ul
      v-if="rows.length"
      class="agent-run-drawer__event-rows"
    >
      <li
        v-for="event in rows"
        :key="event.key"
      >
        <div>
          <strong>{{ event.eventType }}</strong>
          <span>{{ event.sourceType }}</span>
        </div>
        <p>
          <span v-if="event.toolName">{{ event.toolName }}</span>
          <span v-if="event.chapterLabel">{{ event.chapterLabel }}</span>
          <span v-if="event.status">{{ event.status }}</span>
        </p>
        <p v-if="event.errorPreview">{{ event.errorPreview }}</p>
      </li>
    </ul>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`event-projection-next:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__event-projection {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__event-projection h4 {
  margin: 0;
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.agent-run-drawer__facts {
  display: grid;
  gap: var(--space-2);
  margin: 0;
}

.agent-run-drawer__facts div {
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr);
  gap: var(--space-3);
}

.agent-run-drawer__facts dt {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.agent-run-drawer__facts dd {
  margin: 0;
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__event-rows,
.agent-run-drawer__tools {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__event-rows li {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__event-rows div,
.agent-run-drawer__event-rows p {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
  margin: 0;
}

.agent-run-drawer__event-rows strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__event-rows span,
.agent-run-drawer__event-rows p {
  color: var(--color-text-secondary);
}

.agent-run-drawer__tools li {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}
</style>
