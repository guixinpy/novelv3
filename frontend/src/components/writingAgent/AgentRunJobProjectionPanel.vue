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
const queue = computed(() => recordValue(props.output.queue))
const status = computed(() => stringValue(props.output.status))
const totalTaskCount = computed(() => numberValue(summary.value.total))
const returnedTaskCount = computed(() => numberValue(summary.value.returned))
const queueDepth = computed(() => numberValue(queue.value.depth))
const activeTaskCount = computed(() => numberValue(queue.value.active))
const terminalTaskCount = computed(() => numberValue(queue.value.terminal))
const selectedTask = computed(() => recordValue(props.output.selected_task))
const selectedTaskStatus = computed(() => stringValue(selectedTask.value.status))
const selectedTaskChapterIndex = computed(() => numberValue(selectedTask.value.chapter_index))
const selectedTaskChapterRange = computed(() => chapterRangeLabel(recordValue(selectedTask.value.chapter_range)))
const selectedTaskProgress = computed(() => recordValue(selectedTask.value.progress))
const selectedTaskResume = computed(() => recordValue(selectedTask.value.resume))
const nextChapterIndex = computed(() => (
  numberValue(selectedTaskResume.value.next_chapter_index) ??
  numberValue(selectedTaskProgress.value.next_chapter_index)
))
const completedChapterCount = computed(() => (
  numberValue(selectedTaskResume.value.completed_count) ??
  numberValue(selectedTaskProgress.value.completed_count)
))
const canResume = computed(() => (
  typeof selectedTaskResume.value.can_resume === 'boolean'
    ? selectedTaskResume.value.can_resume
    : selectedTaskProgress.value.can_resume
))
const selectedTaskRecovery = computed(() => recordValue(selectedTask.value.recovery))
const canRetry = computed(() => (
  typeof selectedTaskRecovery.value.can_retry === 'boolean'
    ? selectedTaskRecovery.value.can_retry
    : null
))
const recoveryCapability = computed(() => {
  if (canResume.value === true) return '可恢复'
  if (canRetry.value === true) return '可重试'
  if (canResume.value === false || canRetry.value === false) return '不可恢复'
  return ''
})
const errorPreview = computed(() => stringValue(selectedTask.value.error_preview))
const controlPlaneReadiness = computed(() => recordValue(selectedTask.value.control_plane_readiness))
const controlPlaneSummary = computed(() => recordValue(controlPlaneReadiness.value.summary))
const controlPlaneStatus = computed(() => stringValue(controlPlaneReadiness.value.status))
const controlPlaneGapCount = computed(() => numberValue(controlPlaneSummary.value.total_gap_count))
const commandContracts = computed(() => recordValue(selectedTask.value.command_contracts))
const commandContractSummary = computed(() => recordValue(commandContracts.value.summary))
const commandContractStatus = computed(() => stringValue(commandContracts.value.status))
const controlCommandCount = computed(() => numberValue(commandContractSummary.value.agent_control_commands))
const commandContractGapCount = computed(() => numberValue(commandContractSummary.value.gap_count))
const reservation = computed(() => recordValue(props.output.chapter_reservation))
const reservationStatus = computed(() => stringValue(reservation.value.status))
const reservationChapterIndex = computed(() => numberValue(reservation.value.chapter_index))
const reservationActiveTaskCount = computed(() => numberValue(reservation.value.active_task_count))
const reservationRows = computed(() => (
  recordList(reservation.value.tasks)
    .slice(0, 5)
    .map((task, index) => ({
      key: `job-projection-reservation:${index}`,
      sourceLabel: stringValue(task.source_label) || '占用任务',
      status: taskStatusLabel(task.status),
      chapterLabel: taskChapterLabel(task),
    }))
    .filter((task) => task.sourceLabel || task.status || task.chapterLabel)
))
const eventProjection = computed(() => recordValue(selectedTask.value.event_projection))
const eventProjectionSummary = computed(() => recordValue(eventProjection.value.summary))
const eventProjectionStatus = computed(() => stringValue(eventProjection.value.status))
const eventCount = computed(() => numberValue(eventProjectionSummary.value.total))
const eventTypeSummary = computed(() => recordValue(eventProjectionSummary.value.by_event_type))
const toolErrorCount = computed(() => numberValue(eventTypeSummary.value.tool_error))
const recommendedTools = computed(() => uniqueStrings([
  ...stringList(props.output.recommended_tools),
  ...stringList(selectedTaskRecovery.value.recommended_tools),
  ...stringList(reservation.value.recommended_tools),
]).slice(0, 6))

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

function controlPlaneStatusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'ready') return '可继续编排'
  if (statusValue === 'degraded') return '需检查'
  if (statusValue === 'needs_attention') return '需处理'
  return statusValue || '未知'
}

function reservationStatusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'reserved') return '已占用'
  if (statusValue === 'available') return '可用'
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
  const chapterIndex = numberValue(task.chapter_index)
  if (chapterIndex !== null) return `第${chapterIndex}章`

  return chapterRangeLabel(recordValue(task.chapter_range))
}

function chapterRangeLabel(range: Record<string, unknown>) {
  const start = numberValue(range.start)
  const end = numberValue(range.end)
  if (start !== null && end !== null) return `第${start}-${end}章`
  return ''
}
</script>

<template>
  <section
    class="agent-run-drawer__job-projection"
    aria-label="Agent job projection"
  >
    <h4>任务队列投影</h4>
    <dl class="agent-run-drawer__facts">
      <div v-if="status">
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
      </div>
      <div v-if="queueDepth !== null">
        <dt>队列深度</dt>
        <dd>{{ queueDepth }}</dd>
      </div>
      <div v-if="activeTaskCount !== null">
        <dt>活跃任务</dt>
        <dd>{{ activeTaskCount }}</dd>
      </div>
      <div v-if="terminalTaskCount !== null">
        <dt>终止任务</dt>
        <dd>{{ terminalTaskCount }}</dd>
      </div>
      <div v-if="returnedTaskCount !== null && totalTaskCount !== null">
        <dt>返回任务</dt>
        <dd>{{ returnedTaskCount }} / {{ totalTaskCount }}</dd>
      </div>
      <div v-if="selectedTaskStatus">
        <dt>任务状态</dt>
        <dd>{{ taskStatusLabel(selectedTaskStatus) }}</dd>
      </div>
      <div v-if="selectedTaskChapterIndex !== null">
        <dt>目标章节</dt>
        <dd>第{{ selectedTaskChapterIndex }}章</dd>
      </div>
      <div v-if="selectedTaskChapterRange">
        <dt>章节范围</dt>
        <dd>{{ selectedTaskChapterRange }}</dd>
      </div>
      <div v-if="nextChapterIndex !== null">
        <dt>下一章</dt>
        <dd>第{{ nextChapterIndex }}章</dd>
      </div>
      <div v-if="completedChapterCount !== null">
        <dt>已完成章节</dt>
        <dd>{{ completedChapterCount }}</dd>
      </div>
      <div v-if="recoveryCapability">
        <dt>恢复能力</dt>
        <dd>{{ recoveryCapability }}</dd>
      </div>
      <div v-if="errorPreview">
        <dt>错误摘要</dt>
        <dd>{{ errorPreview }}</dd>
      </div>
      <div v-if="controlPlaneStatus">
        <dt>控制平面</dt>
        <dd>{{ controlPlaneStatusLabel(controlPlaneStatus) }}</dd>
      </div>
      <div v-if="controlPlaneGapCount !== null">
        <dt>控制面缺口</dt>
        <dd>{{ controlPlaneGapCount }}</dd>
      </div>
      <div v-if="commandContractStatus">
        <dt>命令契约</dt>
        <dd>{{ statusLabel(commandContractStatus) }}</dd>
      </div>
      <div v-if="controlCommandCount !== null">
        <dt>控制命令</dt>
        <dd>{{ controlCommandCount }}</dd>
      </div>
      <div v-if="commandContractGapCount !== null">
        <dt>契约缺口</dt>
        <dd>{{ commandContractGapCount }}</dd>
      </div>
      <div v-if="reservationStatus">
        <dt>章节占用</dt>
        <dd>{{ reservationStatusLabel(reservationStatus) }}</dd>
      </div>
      <div v-if="reservationChapterIndex !== null">
        <dt>占用章节</dt>
        <dd>第{{ reservationChapterIndex }}章</dd>
      </div>
      <div v-if="reservationActiveTaskCount !== null">
        <dt>占用任务</dt>
        <dd>{{ reservationActiveTaskCount }}</dd>
      </div>
      <div v-if="eventProjectionStatus">
        <dt>事件投影</dt>
        <dd>{{ statusLabel(eventProjectionStatus) }}</dd>
      </div>
      <div v-if="eventCount !== null">
        <dt>事件</dt>
        <dd>{{ eventCount }}</dd>
      </div>
      <div v-if="toolErrorCount !== null">
        <dt>工具错误</dt>
        <dd>{{ toolErrorCount }}</dd>
      </div>
    </dl>
    <ul
      v-if="reservationRows.length"
      class="agent-run-drawer__event-rows"
    >
      <li
        v-for="task in reservationRows"
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
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`job-projection-next:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__job-projection {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__job-projection h4 {
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
