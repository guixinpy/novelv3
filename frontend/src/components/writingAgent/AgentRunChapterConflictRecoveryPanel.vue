<script setup lang="ts">
import { computed } from 'vue'
import {
  numberValue,
  recordList,
  recordValue,
  stringValue,
} from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const status = computed(() => stringValue(props.output.status))
const conflict = computed(() => recordValue(props.output.conflict))
const recovery = computed(() => recordValue(props.output.recovery))
const chapterIndex = computed(() => (
  numberValue(props.output.chapter_index) ??
  numberValue(conflict.value.chapter_index)
))
const conflictStatus = computed(() => stringValue(conflict.value.status))
const activeTaskCount = computed(() => numberValue(conflict.value.active_task_count))
const recoveryState = computed(() => stringValue(recovery.value.status))
const recoveryNextTool = computed(() => stringValue(recovery.value.next_tool))
const planToolCount = computed(() => recordList(props.output.tools).length)
const recoveryOptionCount = computed(() => recordList(props.output.recovery_options).length)
const taskRows = computed(() => (
  recordList(conflict.value.tasks)
    .slice(0, 5)
    .map((task, index) => ({
      key: `chapter-conflict-task:${index}`,
      sourceLabel: stringValue(task.source_label) || '占用任务',
      status: taskStatusLabel(task.status),
      chapterLabel: taskChapterLabel(task),
    }))
    .filter((task) => task.sourceLabel || task.status || task.chapterLabel)
))
const recoveryOptionRows = computed(() => (
  recordList(props.output.recovery_options)
    .slice(0, 5)
    .map((option, index) => ({
      key: `chapter-conflict-option:${index}`,
      action: recoveryOptionLabel(option.action),
      toolName: stringValue(option.tool_name),
      safeAutoExecute: typeof option.safe_auto_execute === 'boolean' ? option.safe_auto_execute : null,
    }))
    .filter((option) => option.action || option.toolName)
))

function statusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'completed' || statusValue === 'success') return '已完成'
  if (statusValue === 'running') return '进行中'
  if (statusValue === 'failed') return '失败'
  if (statusValue === 'blocked') return '已阻塞'
  return statusValue || '未知'
}

function conflictStatusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'reserved') return '已占用'
  if (statusValue === 'available') return '可用'
  return statusValue || '未知'
}

function recoveryStatusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'recommended') return '建议处理'
  if (statusValue === 'none') return '无需恢复'
  if (statusValue === 'completed' || statusValue === 'success') return '已完成'
  if (statusValue === 'failed') return '失败'
  return statusValue || '未知'
}

function taskStatusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'pending') return '待执行'
  if (statusValue === 'running') return '运行中'
  if (statusValue === 'completed' || statusValue === 'success') return '已完成'
  if (statusValue === 'failed') return '失败'
  if (statusValue === 'cancelled') return '已取消'
  return statusValue || ''
}

function taskChapterLabel(task: Record<string, unknown>) {
  const taskChapterIndex = numberValue(task.chapter_index)
  if (taskChapterIndex !== null) return `第${taskChapterIndex}章`

  return chapterRangeLabel(recordValue(task.chapter_range))
}

function chapterRangeLabel(range: Record<string, unknown>) {
  const start = numberValue(range.start)
  const end = numberValue(range.end)
  if (start !== null && end !== null) return `第${start}-${end}章`
  return ''
}

function recoveryOptionLabel(value: unknown) {
  const actionValue = stringValue(value)
  if (actionValue === 'inspect_occupying_task') return '检查占用任务'
  if (actionValue === 'wait_for_occupying_task') return '等待占用任务'
  return actionValue || '恢复选项'
}
</script>

<template>
  <section
    class="agent-run-drawer__chapter-conflict"
    aria-label="Chapter conflict recovery projection"
  >
    <h4>章节冲突恢复</h4>
    <dl class="agent-run-drawer__facts">
      <div v-if="status">
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
      </div>
      <div v-if="chapterIndex !== null">
        <dt>目标章节</dt>
        <dd>第{{ chapterIndex }}章</dd>
      </div>
      <div v-if="conflictStatus">
        <dt>占用状态</dt>
        <dd>{{ conflictStatusLabel(conflictStatus) }}</dd>
      </div>
      <div v-if="activeTaskCount !== null">
        <dt>占用任务</dt>
        <dd>{{ activeTaskCount }}</dd>
      </div>
      <div v-if="recoveryState">
        <dt>恢复状态</dt>
        <dd>{{ recoveryStatusLabel(recoveryState) }}</dd>
      </div>
      <div v-if="recoveryNextTool">
        <dt>下一工具</dt>
        <dd>{{ recoveryNextTool }}</dd>
      </div>
      <div v-if="planToolCount > 0">
        <dt>计划工具</dt>
        <dd>{{ planToolCount }}</dd>
      </div>
      <div v-if="recoveryOptionCount > 0">
        <dt>恢复选项</dt>
        <dd>{{ recoveryOptionCount }}</dd>
      </div>
    </dl>
    <ul
      v-if="taskRows.length"
      class="agent-run-drawer__event-rows"
    >
      <li
        v-for="task in taskRows"
        :key="task.key"
      >
        <div>
          <strong>{{ task.sourceLabel }}</strong>
          <span v-if="task.chapterLabel">{{ task.chapterLabel }}</span>
        </div>
        <p v-if="task.status">{{ task.status }}</p>
      </li>
    </ul>
    <ul
      v-if="recoveryOptionRows.length"
      class="agent-run-drawer__worker-dispatches"
    >
      <li
        v-for="option in recoveryOptionRows"
        :key="option.key"
      >
        <strong>{{ option.action }}</strong>
        <span v-if="option.toolName">{{ option.toolName }}</span>
        <span v-if="option.safeAutoExecute !== null">{{ option.safeAutoExecute ? '可自动检查' : '需等待' }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__chapter-conflict {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__chapter-conflict h4 {
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
.agent-run-drawer__worker-dispatches {
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

.agent-run-drawer__worker-dispatches li {
  display: grid;
  gap: 2px;
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__worker-dispatches span {
  color: var(--color-text-secondary);
}
</style>
