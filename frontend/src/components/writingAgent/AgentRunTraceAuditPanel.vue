<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const audit = computed(() => recordValue(props.output.audit))
const run = computed(() => recordValue(props.output.run))
const failure = computed(() => recordValue(props.output.failure))
const context = computed(() => recordValue(props.output.context))
const intentChain = computed(() => recordValue(props.output.intent_chain))
const endToEndChain = computed(() => recordValue(props.output.end_to_end_chain))
const anomalySummary = computed(() => recordValue(props.output.anomaly_summary))
const steps = computed(() => recordList(props.output.steps))
const traces = computed(() => recordList(props.output.traces))
const eventChain = computed(() => recordList(props.output.event_chain))
const recommendedActions = computed(() => recordList(props.output.recommended_actions))
const runGoal = computed(() => safeText(run.value.goal))
const stepCount = computed(() => numberValue(audit.value.step_count))
const traceCount = computed(() => numberValue(audit.value.trace_count))
const eventCount = computed(() => numberValue(audit.value.event_chain_count))
const contextBlockCount = computed(() => numberValue(audit.value.context_block_count))
const controlPlaneGapCount = computed(() => numberValue(audit.value.control_plane_gap_count))
const intentChainStatus = computed(() => stringValue(intentChain.value.status))
const intentChainRuleId = computed(() => safeText(intentChain.value.rule_id))
const intentChainClass = computed(() => safeText(intentChain.value.intent_class))
const intentChainChapterLabel = computed(() => chapterIndexLabel(intentChain.value.chapter_index))
const intentChainPlannedCount = computed(() => numberValue(intentChain.value.planned_tool_count))
const intentChainExecutedCount = computed(() => numberValue(intentChain.value.executed_tool_count))
const intentChainMatchedCount = computed(() => numberValue(intentChain.value.matched_tool_count))
const endToEndStatus = computed(() => stringValue(endToEndChain.value.status))
const endToEndPlannedCount = computed(() => numberValue(endToEndChain.value.planned_tool_count))
const endToEndToolStepCount = computed(() => numberValue(endToEndChain.value.tool_step_count))
const endToEndModelTraceCount = computed(() => numberValue(endToEndChain.value.model_trace_count))
const endToEndResultMessage = computed(() => recordValue(endToEndChain.value.result_message))
const endToEndResultActionType = computed(() => safeText(endToEndResultMessage.value.action_type))
const endToEndResultStatusLabel = computed(() => actionStatusLabel(endToEndResultMessage.value.action_status))
const anomalyStatus = computed(() => stringValue(anomalySummary.value.status))
const anomalyIssueCount = computed(() => numberValue(anomalySummary.value.issue_count))
const anomalySeverityCounts = computed(() => recordValue(anomalySummary.value.severity_counts))
const anomalyCriticalCount = computed(() => numberValue(anomalySeverityCounts.value.critical))
const anomalyWarningCount = computed(() => numberValue(anomalySeverityCounts.value.warning))
const anomalyInfoCount = computed(() => numberValue(anomalySeverityCounts.value.info))
const anomalyFailedStepCount = computed(() => numberValue(anomalySummary.value.failed_step_count))
const anomalyFailedTraceCount = computed(() => numberValue(anomalySummary.value.failed_trace_count))
const anomalyMissingTraceCount = computed(() => numberValue(anomalySummary.value.missing_trace_binding_count))
const anomalyUnmatchedPlanCount = computed(() => numberValue(anomalySummary.value.unmatched_planned_tool_count))
const anomalyMissingResultMessage = computed(() => anomalySummary.value.missing_result_message === true)
const anomalyTruncatedContextCount = computed(() => numberValue(anomalySummary.value.truncated_context_block_count))
const failureTool = computed(() => safeText(failure.value.tool_name))
const failureReason = computed(() => safeText(failure.value.reason_code))
const failureMessage = computed(() => safeText(failure.value.message))
const intentChainRows = computed(() => (
  recordList(intentChain.value.planned_tools)
    .map((tool, index) => {
      const stepIndex = numberValue(tool.step_index)
      return {
        key: `trace-audit-intent-tool:${index}`,
        toolName: safeText(tool.tool_name) || '计划工具',
        statusLabel: statusLabel(tool.status),
        stepLabel: stepIndex !== null ? `#${stepIndex}` : '',
      }
    })
    .filter((row) => Boolean(row.toolName || row.statusLabel || row.stepLabel))
))
const endToEndSegmentRows = computed(() => (
  recordList(endToEndChain.value.segments)
    .map((segment, index) => {
      const count = numberValue(segment.count)
      const chapterLabel = chapterIndexLabel(segment.chapter_index)
      const status = stringValue(segment.status)
      const actionStatus = stringValue(segment.action_status)
      return {
        key: `trace-audit-e2e:${index}`,
        stageLabel: endToEndStageLabel(segment.stage),
        statusLabel: availabilityLabel(status),
        meta: [
          count !== null ? `${count}` : '',
          chapterLabel,
          safeText(segment.intent_class),
          safeText(segment.action_type),
          actionStatus ? actionStatusLabel(actionStatus) : '',
        ].filter(Boolean).join(' · '),
      }
    })
    .filter((row) => Boolean(row.stageLabel || row.statusLabel || row.meta))
))
const anomalyIssueRows = computed(() => (
  recordList(anomalySummary.value.issues)
    .slice(0, 8)
    .map((issue, index) => {
      const stepIndex = numberValue(issue.step_index)
      const charCount = numberValue(issue.char_count)
      const sourceCount = numberValue(issue.source_count)
      return {
        key: `trace-audit-anomaly:${index}`,
        label: anomalyCodeLabel(issue.code),
        severityLabel: anomalySeverityLabel(issue.severity),
        meta: [
          safeText(issue.tool_name),
          safeText(issue.trace_type),
          endToEndStageLabel(issue.stage),
          safeText(issue.kind),
          statusLabel(issue.status),
          stepIndex !== null ? `#${stepIndex}` : '',
          chapterIndexLabel(issue.chapter_index),
          issue.error_recorded === true ? '已记录错误' : '',
          charCount !== null ? `${charCount} 字` : '',
          sourceCount !== null ? `来源 ${sourceCount}` : '',
        ].filter(Boolean).join(' · '),
        title: safeText(issue.title),
      }
    })
    .filter((row) => Boolean(row.label || row.severityLabel || row.meta || row.title))
))
const stepRows = computed(() => (
  steps.value
    .map((step, index) => {
      const stepIndex = numberValue(step.step_index)
      const toolName = safeText(step.tool_name)
      return {
        key: `trace-audit-step:${stepIndex ?? index}`,
        label: [stepIndex !== null ? `#${stepIndex}` : '', toolName].filter(Boolean).join(' '),
        statusLabel: statusLabel(step.status),
        chapterLabel: chapterIndexLabel(step.chapter_index),
      }
    })
    .filter((row) => Boolean(row.label || row.statusLabel || row.chapterLabel))
))
const traceRows = computed(() => (
  traces.value
    .map((trace, index) => {
      const promptTokens = numberValue(trace.prompt_tokens)
      const completionTokens = numberValue(trace.completion_tokens)
      const latencyMs = numberValue(trace.latency_ms)
      const contextBlockCount = numberValue(trace.context_block_count)
      const contextCharCount = numberValue(trace.context_char_count)
      const meta = [
        safeText(trace.model),
        promptTokens !== null ? `prompt ${promptTokens}` : '',
        completionTokens !== null ? `completion ${completionTokens}` : '',
        latencyMs !== null ? `${latencyMs}ms` : '',
        contextBlockCount !== null ? `上下文块 ${contextBlockCount}` : '',
        contextCharCount !== null ? `${contextCharCount} 字` : '',
      ].filter(Boolean).join(' · ')
      return {
        key: `trace-audit-trace:${index}`,
        label: safeText(trace.trace_type) || '模型 Trace',
        statusLabel: statusLabel(trace.status),
        meta,
        error: safeText(trace.error_message),
      }
    })
    .filter((row) => Boolean(row.label || row.statusLabel || row.meta || row.error))
))
const eventRows = computed(() => (
  eventChain.value
    .slice(0, 6)
    .map((event, index) => ({
      key: `trace-audit-event:${index}`,
      label: eventLabel(event),
      detail: eventDetail(event),
    }))
    .filter((row) => Boolean(row.label || row.detail))
))
const contextRows = computed(() => (
  recordList(context.value.blocks)
    .map((block, index) => {
      const charCount = numberValue(block.char_count)
      const sourceCount = numberValue(block.source_count)
      return {
        key: `trace-audit-context:${index}`,
        title: safeText(block.title) || '上下文块',
        kind: safeText(block.kind),
        meta: [
          charCount !== null ? `${charCount} 字` : '',
          sourceCount !== null ? `来源 ${sourceCount}` : '',
          block.truncated === true ? '已截断' : '',
        ].filter(Boolean).join(' · '),
      }
    })
    .filter((row) => Boolean(row.title || row.meta))
))
const recommendedActionRows = computed(() => (
  recommendedActions.value
    .map((action, index) => {
      const sourceStepIndex = numberValue(action.source_step_index)
      return {
        key: `trace-audit-action:${index}`,
        toolName: safeText(action.tool_name) || '建议工具',
        reason: safeText(action.reason_code),
        sourceStepLabel: sourceStepIndex !== null ? `步骤 ${sourceStepIndex}` : '',
      }
    })
    .filter((row) => Boolean(row.toolName || row.reason || row.sourceStepLabel))
))
const hasIntentChain = computed(() => Boolean(
  intentChainStatus.value === 'available' ||
  intentChainRuleId.value ||
  intentChainClass.value ||
  intentChainChapterLabel.value ||
  intentChainRows.value.length
))
const hasEndToEndChain = computed(() => Boolean(
  endToEndStatus.value ||
  endToEndPlannedCount.value !== null ||
  endToEndToolStepCount.value !== null ||
  endToEndModelTraceCount.value !== null ||
  endToEndResultActionType.value ||
  endToEndSegmentRows.value.length
))
const hasAnomalySummary = computed(() => Boolean(
  anomalyStatus.value ||
  anomalyIssueCount.value !== null ||
  anomalyIssueRows.value.length
))

function safeText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_-]+/.test(value)) return ''
  if (/(run|step|trace|message|task|target|chapter-content|longform)-secret|source_refs?|source_id|approval_contract|approval:/i.test(value)) return ''
  return value.slice(0, 96)
}

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function statusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'completed' || value === 'success' || value === 'ready' || value === 'passed') return '已完成'
  if (value === 'blocked') return '阻塞'
  if (value === 'failed') return '失败'
  if (value === 'running') return '运行中'
  if (value === 'executed') return '已执行'
  if (value === 'pending') return '等待中'
  if (value === 'cancelled') return '已取消'
  if (value === 'needs_attention') return '需处理'
  return value || '未知'
}

function anomalyStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'clear') return '正常'
  if (value === 'failed') return '失败'
  if (value === 'warning') return '警告'
  return statusLabel(value)
}

function anomalySeverityLabel(severity: unknown) {
  const value = stringValue(severity)
  if (value === 'critical') return '严重'
  if (value === 'warning') return '警告'
  if (value === 'info') return '提示'
  return safeText(value)
}

function endToEndStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'complete') return '完整'
  if (value === 'partial') return '部分'
  if (value === 'missing') return '缺失'
  return statusLabel(value)
}

function availabilityLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'available') return '可用'
  if (value === 'missing') return '缺失'
  return statusLabel(value)
}

function actionStatusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'success' || value === 'completed') return '成功'
  if (value === 'ready') return '可用'
  if (value === 'failed') return '失败'
  if (value === 'blocked') return '阻塞'
  if (value === 'running') return '运行中'
  return value
}

function endToEndStageLabel(stage: unknown) {
  const value = stringValue(stage)
  if (!value) return ''
  if (value === 'intent') return '意图'
  if (value === 'planned_tools') return '计划工具'
  if (value === 'executed_tools') return '执行工具'
  if (value === 'model_traces') return '模型 Trace'
  if (value === 'result_message') return '结果消息'
  return safeText(value)
}

function anomalyCodeLabel(code: unknown) {
  const value = stringValue(code)
  if (value === 'failed_tool_step') return '工具步骤失败'
  if (value === 'failed_model_trace') return '模型 Trace 失败'
  if (value === 'missing_trace_binding') return '缺少 Trace 绑定'
  if (value === 'planned_tool_not_executed') return '计划工具未执行'
  if (value === 'missing_result_message') return '结果消息缺失'
  if (value === 'truncated_context_block') return '上下文块已截断'
  return safeText(value)
}

function eventLabel(event: Record<string, unknown>) {
  const eventType = stringValue(event.event_type)
  if (eventType === 'dialog_route_decision') {
    return safeText(event.selected_route_label) || '对话路由'
  }
  if (eventType === 'approval_decision') {
    return ['审批', safeText(event.decision_label)].filter(Boolean).join('：')
  }
  if (eventType === 'run_dispatched') {
    return ['运行派发', statusLabel(event.status)].filter(Boolean).join('：')
  }
  if (eventType === 'tool_step') {
    const stepIndex = numberValue(event.step_index)
    const toolName = safeText(event.tool_name)
    return ['工具步骤', stepIndex !== null ? `#${stepIndex}` : '', toolName].filter(Boolean).join(' ')
  }
  if (eventType === 'trace_attached') {
    return ['Trace', safeText(event.trace_type)].filter(Boolean).join(' ')
  }
  return safeText(eventType)
}

function eventDetail(event: Record<string, unknown>) {
  const eventType = stringValue(event.event_type)
  if (eventType === 'dialog_route_decision') {
    return safeText(event.reason_label)
  }
  if (eventType === 'approval_decision') {
    return safeText(event.action_type)
  }
  if (eventType === 'run_dispatched') {
    return safeText(event.entrypoint)
  }
  if (eventType === 'tool_step' || eventType === 'trace_attached') {
    return statusLabel(event.status)
  }
  return ''
}
</script>

<template>
  <section
    class="agent-run-drawer__trace-audit"
    aria-label="Agent trace audit projection"
  >
    <h4>Trace 审计</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(audit.status) }}</dd>
      </div>
      <div v-if="runGoal">
        <dt>目标</dt>
        <dd>{{ runGoal }}</dd>
      </div>
      <div v-if="stepCount !== null">
        <dt>步骤</dt>
        <dd>步骤 {{ stepCount }}</dd>
      </div>
      <div v-if="traceCount !== null">
        <dt>Trace</dt>
        <dd>Trace {{ traceCount }}</dd>
      </div>
      <div v-if="eventCount !== null">
        <dt>事件</dt>
        <dd>事件 {{ eventCount }}</dd>
      </div>
      <div v-if="contextBlockCount !== null">
        <dt>上下文</dt>
        <dd>上下文块 {{ contextBlockCount }}</dd>
      </div>
      <div v-if="controlPlaneGapCount !== null">
        <dt>控制面</dt>
        <dd>控制面缺口 {{ controlPlaneGapCount }}</dd>
      </div>
    </dl>
    <div
      v-if="failureTool || failureReason || failureMessage"
      class="agent-run-drawer__trace-audit-failure"
    >
      <strong>{{ failureTool || '失败摘要' }}</strong>
      <span v-if="failureReason">{{ failureReason }}</span>
      <p v-if="failureMessage">{{ failureMessage }}</p>
    </div>
    <div
      v-if="hasAnomalySummary"
      class="agent-run-drawer__trace-audit-anomaly"
    >
      <strong>异常摘要</strong>
      <dl class="agent-run-drawer__facts">
        <div v-if="anomalyStatus">
          <dt>状态</dt>
          <dd>{{ anomalyStatusLabel(anomalyStatus) }}</dd>
        </div>
        <div v-if="anomalyIssueCount !== null">
          <dt>问题</dt>
          <dd>问题 {{ anomalyIssueCount }}</dd>
        </div>
        <div v-if="anomalyCriticalCount !== null">
          <dt>严重</dt>
          <dd>严重 {{ anomalyCriticalCount }}</dd>
        </div>
        <div v-if="anomalyWarningCount !== null">
          <dt>警告</dt>
          <dd>警告 {{ anomalyWarningCount }}</dd>
        </div>
        <div v-if="anomalyInfoCount !== null">
          <dt>提示</dt>
          <dd>提示 {{ anomalyInfoCount }}</dd>
        </div>
        <div v-if="anomalyFailedStepCount !== null">
          <dt>失败步骤</dt>
          <dd>失败步骤 {{ anomalyFailedStepCount }}</dd>
        </div>
        <div v-if="anomalyFailedTraceCount !== null">
          <dt>失败 Trace</dt>
          <dd>失败 Trace {{ anomalyFailedTraceCount }}</dd>
        </div>
        <div v-if="anomalyMissingTraceCount !== null">
          <dt>缺 Trace</dt>
          <dd>缺 Trace {{ anomalyMissingTraceCount }}</dd>
        </div>
        <div v-if="anomalyUnmatchedPlanCount !== null">
          <dt>未执行计划</dt>
          <dd>未执行计划 {{ anomalyUnmatchedPlanCount }}</dd>
        </div>
        <div v-if="anomalyMissingResultMessage">
          <dt>结果消息</dt>
          <dd>缺结果消息</dd>
        </div>
        <div v-if="anomalyTruncatedContextCount !== null">
          <dt>截断上下文</dt>
          <dd>截断上下文 {{ anomalyTruncatedContextCount }}</dd>
        </div>
      </dl>
      <ul
        v-if="anomalyIssueRows.length"
        class="agent-run-drawer__planner-signals"
      >
        <li
          v-for="row in anomalyIssueRows"
          :key="row.key"
        >
          <strong>{{ row.label }}</strong>
          <span v-if="row.severityLabel">{{ row.severityLabel }}</span>
          <span v-if="row.meta">{{ row.meta }}</span>
          <span v-if="row.title">{{ row.title }}</span>
        </li>
      </ul>
    </div>
    <div
      v-if="hasIntentChain"
      class="agent-run-drawer__trace-audit-intent"
    >
      <strong>意图链路</strong>
      <dl class="agent-run-drawer__facts">
        <div v-if="intentChainRuleId">
          <dt>规则</dt>
          <dd>{{ intentChainRuleId }}</dd>
        </div>
        <div v-if="intentChainClass">
          <dt>意图</dt>
          <dd>{{ intentChainClass }}</dd>
        </div>
        <div v-if="intentChainChapterLabel">
          <dt>章节</dt>
          <dd>{{ intentChainChapterLabel }}</dd>
        </div>
        <div v-if="intentChainPlannedCount !== null">
          <dt>计划工具</dt>
          <dd>计划工具 {{ intentChainPlannedCount }}</dd>
        </div>
        <div v-if="intentChainExecutedCount !== null">
          <dt>已执行</dt>
          <dd>已执行 {{ intentChainExecutedCount }}</dd>
        </div>
        <div v-if="intentChainMatchedCount !== null">
          <dt>已匹配</dt>
          <dd>已匹配 {{ intentChainMatchedCount }}</dd>
        </div>
      </dl>
      <ul
        v-if="intentChainRows.length"
        class="agent-run-drawer__execution-tools"
      >
        <li
          v-for="row in intentChainRows"
          :key="row.key"
        >
          <span>{{ row.toolName }}</span>
          <strong>{{ [row.stepLabel, row.statusLabel].filter(Boolean).join(' · ') }}</strong>
        </li>
      </ul>
    </div>
    <div
      v-if="hasEndToEndChain"
      class="agent-run-drawer__trace-audit-end-to-end"
    >
      <strong>端到端链路</strong>
      <dl class="agent-run-drawer__facts">
        <div v-if="endToEndStatus">
          <dt>状态</dt>
          <dd>{{ endToEndStatusLabel(endToEndStatus) }}</dd>
        </div>
        <div v-if="endToEndPlannedCount !== null">
          <dt>计划工具</dt>
          <dd>计划工具 {{ endToEndPlannedCount }}</dd>
        </div>
        <div v-if="endToEndToolStepCount !== null">
          <dt>执行步骤</dt>
          <dd>执行步骤 {{ endToEndToolStepCount }}</dd>
        </div>
        <div v-if="endToEndModelTraceCount !== null">
          <dt>模型 Trace</dt>
          <dd>模型 Trace {{ endToEndModelTraceCount }}</dd>
        </div>
        <div v-if="endToEndResultActionType || endToEndResultStatusLabel">
          <dt>结果消息</dt>
          <dd>
            {{ [endToEndResultActionType, endToEndResultStatusLabel].filter(Boolean).join(' · ') }}
          </dd>
        </div>
      </dl>
      <ul
        v-if="endToEndSegmentRows.length"
        class="agent-run-drawer__execution-tools"
      >
        <li
          v-for="row in endToEndSegmentRows"
          :key="row.key"
        >
          <span>{{ row.stageLabel }}</span>
          <strong>{{ [row.statusLabel, row.meta].filter(Boolean).join(' · ') }}</strong>
        </li>
      </ul>
    </div>
    <ul
      v-if="recommendedActionRows.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="row in recommendedActionRows"
        :key="row.key"
      >
        {{ row.toolName }}
        <span v-if="row.reason"> · {{ row.reason }}</span>
        <span v-if="row.sourceStepLabel"> · {{ row.sourceStepLabel }}</span>
      </li>
    </ul>
    <ul
      v-if="eventRows.length"
      class="agent-run-drawer__planner-signals"
    >
      <li
        v-for="row in eventRows"
        :key="row.key"
      >
        <strong>{{ row.label }}</strong>
        <span v-if="row.detail">{{ row.detail }}</span>
      </li>
    </ul>
    <ul
      v-if="contextRows.length"
      class="agent-run-drawer__reference-patterns"
    >
      <li
        v-for="row in contextRows"
        :key="row.key"
      >
        <div>
          <strong>{{ row.title }}</strong>
          <span v-if="row.kind">{{ row.kind }}</span>
        </div>
        <p v-if="row.meta">{{ row.meta }}</p>
      </li>
    </ul>
    <ul
      v-if="stepRows.length"
      class="agent-run-drawer__execution-tools"
    >
      <li
        v-for="row in stepRows"
        :key="row.key"
      >
        <span>{{ row.label || '工具步骤' }}</span>
        <strong>{{ [row.chapterLabel, row.statusLabel].filter(Boolean).join(' · ') }}</strong>
      </li>
    </ul>
    <ul
      v-if="traceRows.length"
      class="agent-run-drawer__reference-patterns"
    >
      <li
        v-for="row in traceRows"
        :key="row.key"
      >
        <div>
          <strong>{{ row.label }}</strong>
          <span>{{ row.statusLabel }}</span>
        </div>
        <p v-if="row.meta">{{ row.meta }}</p>
        <p v-if="row.error">{{ row.error }}</p>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__trace-audit {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__trace-audit h4 {
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

.agent-run-drawer__tools,
.agent-run-drawer__execution-tools,
.agent-run-drawer__planner-signals,
.agent-run-drawer__reference-patterns {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__tools li,
.agent-run-drawer__planner-signals li {
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__planner-signals li {
  display: grid;
  gap: var(--space-1);
}

.agent-run-drawer__planner-signals strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__planner-signals span {
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
}

.agent-run-drawer__execution-tools li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__execution-tools span {
  min-width: 0;
  overflow-wrap: anywhere;
}

.agent-run-drawer__execution-tools strong {
  flex: 0 0 auto;
  color: var(--color-text-secondary);
  font-weight: var(--font-semibold);
}

.agent-run-drawer__reference-patterns li {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__reference-patterns div {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: baseline;
}

.agent-run-drawer__reference-patterns strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__reference-patterns span,
.agent-run-drawer__reference-patterns p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
}

.agent-run-drawer__trace-audit-failure {
  display: grid;
  gap: 2px;
  padding: var(--space-2);
  border-left: 3px solid var(--color-warning);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
}

.agent-run-drawer__trace-audit-failure strong {
  color: var(--color-text-primary);
}

.agent-run-drawer__trace-audit-failure span,
.agent-run-drawer__trace-audit-failure p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
  overflow-wrap: anywhere;
}

.agent-run-drawer__trace-audit-intent,
.agent-run-drawer__trace-audit-anomaly,
.agent-run-drawer__trace-audit-end-to-end {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  font-size: var(--text-xs);
}

.agent-run-drawer__trace-audit-intent > strong,
.agent-run-drawer__trace-audit-anomaly > strong,
.agent-run-drawer__trace-audit-end-to-end > strong {
  color: var(--color-text-primary);
}
</style>
