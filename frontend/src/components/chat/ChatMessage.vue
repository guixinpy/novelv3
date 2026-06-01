<script setup lang="ts">
import { computed } from 'vue'
import ActionCard from './ActionCard.vue'
import ChatSummaryCard from './ChatSummaryCard.vue'
import { buildAgentRunActionResultView, getAgentRunIdFromMessage } from './agentRunProjection'

const props = defineProps<{
  msg: any
  isLatest: boolean
  loading: boolean
}>()

const emit = defineEmits<{
  decide: [decision: string, comment?: string]
  safetyAction: [action: any]
  openTrace: [traceId: string]
  openAgentRun: [runId: string]
}>()

const roleName = computed(() => {
  if (props.msg.role === 'user') return '我'
  if (props.msg.role === 'system') return '系统'
  return '墨舟'
})

const TYPE_LABELS: Record<string, string> = {
  generate_setup: '生成设定',
  generate_storyline: '生成故事线',
  generate_outline: '生成大纲',
  generate_chapter: '生成正文',
  preview_setup: '生成设定',
  preview_storyline: '生成故事线',
  preview_outline: '生成大纲',
  preview_chapter: '生成正文',
}

const GENERATING_LABELS: Record<string, string> = {
  generate_setup: '设定',
  generate_storyline: '故事线',
  generate_outline: '大纲',
  generate_chapter: '正文',
  preview_setup: '设定',
  preview_storyline: '故事线',
  preview_outline: '大纲',
  preview_chapter: '正文',
}

const projectedActionResultView = computed(() => (
  props.msg.action_result_view || buildAgentRunActionResultView(props.msg.action_result)
))

const resultText = computed(() => {
  const r = props.msg.action_result
  if (!r) return ''
  const viewLabel = projectedActionResultView.value?.label
  if (typeof viewLabel === 'string' && viewLabel.trim()) return viewLabel
  const label = TYPE_LABELS[r.type] || r.type
  if (r.status === 'success') return `✓ ${label}执行成功`
  if (r.status === 'cancelled') return `✗ 操作已取消`
  if (r.status === 'generating') return `⏳ ${GENERATING_LABELS[r.type] || label}生成中...`
  if (r.status === 'approval_required') return `⏳ ${label}等待确认`
  if (r.status === 'failed') return `✗ ${label}失败`
  return `${label}: ${r.status}`
})

const resultVariant = computed(() => {
  const viewVariant = projectedActionResultView.value?.variant
  if (viewVariant === 'success' || viewVariant === 'error' || viewVariant === 'neutral') return viewVariant
  const status = props.msg.action_result?.status
  if (status === 'success') return 'success'
  if (status === 'failed') return 'error'
  return 'neutral'
})

const resultDetailItems = computed(() => {
  const items = projectedActionResultView.value?.detail_items
  if (!Array.isArray(items)) return []
  return items.filter((item: any) => (
    typeof item?.label === 'string'
    && item.label.trim()
    && typeof item?.value === 'string'
    && item.value.trim()
  ))
})

const agentRunId = computed(() => getAgentRunIdFromMessage(props.msg))

const summaryTitle = computed(() => {
  const title = props.msg.meta?.title
  return typeof title === 'string' && title.trim() ? title : '会话摘要'
})

const summaryCompactedCount = computed(() => {
  const compactedCount = props.msg.meta?.compacted_count
  return typeof compactedCount === 'number' ? compactedCount : 0
})

const isUnavailableCommandFeedback = computed(() => (
  props.msg.message_type === 'command'
  && props.msg.meta?.command_available === false
))

const commandFeedbackLabel = computed(() => {
  const commandName = props.msg.meta?.command_name
  if (typeof commandName !== 'string' || !commandName.trim()) return '命令'
  return commandName.trim().startsWith('/') ? commandName.trim() : `/${commandName.trim()}`
})

const commandFeedbackReasons = computed(() => {
  const reasons = props.msg.meta?.unavailable_reasons
  if (!Array.isArray(reasons)) return []
  return reasons
    .map((reason: unknown) => (typeof reason === 'string' ? reason.trim() : ''))
    .filter(Boolean)
})

const agentHealthProjection = computed(() => {
  const projection = props.msg.meta?.agent_health_projection
  if (!projection || typeof projection !== 'object' || Array.isArray(projection)) return null
  return projection as Record<string, any>
})

const agentHealthStatusLabel = computed(() => {
  const status = String(agentHealthProjection.value?.status || '')
  if (status === 'ready') return '就绪'
  if (status === 'degraded') return '部分降级'
  if (status === 'needs_attention') return '需要处理'
  return status || '未知'
})

const agentHealthDiagnostics = computed(() => {
  const diagnostics = agentHealthProjection.value?.diagnostics
  if (!Array.isArray(diagnostics)) return []
  return diagnostics
    .map((diagnostic: any) => ({
      code: typeof diagnostic?.code === 'string' ? diagnostic.code.trim() : '',
      message: typeof diagnostic?.message === 'string' ? diagnostic.message.trim() : '',
    }))
    .filter((diagnostic) => diagnostic.message)
    .slice(0, 3)
})

const agentHealthRecommendedTools = computed(() => {
  const tools = agentHealthProjection.value?.recommended_next_tools
  if (!Array.isArray(tools)) return []
  return tools
    .map((tool: unknown) => (typeof tool === 'string' ? tool.trim() : ''))
    .filter(Boolean)
    .slice(0, 5)
})

const agentHealthRouteRegistryChips = computed(() => {
  const registry = agentHealthProjection.value?.agent_worker_route_registry
  if (!registry || typeof registry !== 'object' || Array.isArray(registry)) return []
  const record = registry as Record<string, unknown>
  const summary = record.summary && typeof record.summary === 'object' && !Array.isArray(record.summary)
    ? record.summary as Record<string, unknown>
    : {}
  const chips: string[] = []
  const status = typeof record.status === 'string' ? record.status.trim() : ''
  if (status) chips.push(agentWorkerRouteRegistryStatusLabel(status))
  const unroutedAllowedTools = numberValue(summary.unrouted_allowed_tools)
  if (unroutedAllowedTools !== null) chips.push(`未路由 ${unroutedAllowedTools}`)
  const issueCount = numberValue(summary.issues)
  if (issueCount !== null && issueCount > 0) chips.push(`问题 ${issueCount}`)
  return chips
})

const agentControlProjection = computed(() => {
  const projection = props.msg.meta?.agent_control
  if (!projection || typeof projection !== 'object' || Array.isArray(projection)) return null
  return projection as Record<string, any>
})

const agentControlCommandLabel = computed(() => {
  const commandName = String(agentControlProjection.value?.command_name || '').trim()
  if (!commandName) return 'Agent 命令'
  return commandName.startsWith('/') ? commandName : `/${commandName}`
})

const agentControlRouteLabel = computed(() => {
  const route = String(agentControlProjection.value?.selected_route || '')
  if (route === 'recover_blocked_run') return '恢复阻塞'
  if (route === 'recommended_followups') return '推荐后继'
  if (route === 'chapter_generation') return '生成下一章'
  return route || '未选择'
})

const agentControlReasonLabel = computed(() => {
  const reason = String(agentControlProjection.value?.reason_code || '')
  if (reason === 'recoverable_run_found') return '发现可恢复运行'
  if (reason === 'recommended_followups_found') return '存在推荐后继'
  if (reason === 'no_recovery_or_followup') return '无恢复或推荐后继'
  return reason || '暂无原因'
})

const agentControlRequiredTools = computed(() => {
  const tools = agentControlProjection.value?.required_agent_tools
  if (!Array.isArray(tools)) return []
  return tools
    .map((tool: unknown) => (typeof tool === 'string' ? tool.trim() : ''))
    .filter(Boolean)
    .slice(0, 4)
})

const canOpenTrace = computed(() => (
  props.msg.role !== 'user'
  && typeof props.msg.trace_id === 'string'
  && props.msg.trace_id.trim().length > 0
))

const messageTime = computed(() => {
  if (props.msg.role === 'user') return ''
  return formatMessageTime(props.msg.created_at)
})

function formatMessageTime(value: unknown) {
  if (typeof value !== 'string' || !value.trim()) return ''
  return value.trim().replace('T', ' ').slice(0, 16)
}

function numberValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null
}

function agentWorkerRouteRegistryStatusLabel(status: string) {
  if (status === 'passed') return '通过'
  if (status === 'needs_attention') return '需处理'
  return status || '未知'
}

function onDecide(decision: string, comment?: string) {
  emit('decide', decision, comment)
}

function onSafetyAction(action: any) {
  emit('safetyAction', action)
}

function openTrace() {
  if (!canOpenTrace.value) return
  emit('openTrace', props.msg.trace_id)
}

function openAgentRun() {
  if (!agentRunId.value) return
  emit('openAgentRun', agentRunId.value)
}
</script>

<template>
  <div
    class="chat-msg"
    :class="msg.role === 'user' ? 'chat-msg--right' : 'chat-msg--left'"
  >
    <ChatSummaryCard
      v-if="msg.message_type === 'summary'"
      :content="msg.content"
      :title="summaryTitle"
      :compacted-count="summaryCompactedCount"
    />
    <div
      v-else
      class="chat-msg__bubble"
      :class="`chat-msg__bubble--${msg.role}`"
    >
      <div class="chat-msg__header">
        <div class="chat-msg__role">{{ roleName }}</div>
        <time
          v-if="messageTime"
          class="chat-msg__time"
          :datetime="msg.created_at"
        >
          {{ messageTime }}
        </time>
        <button
          v-if="canOpenTrace"
          type="button"
          class="chat-msg__trace"
          data-testid="open-trace"
          @click="openTrace"
        >
          上下文
        </button>
      </div>
      <div class="chat-msg__content">{{ msg.content }}</div>
      <div
        v-if="isUnavailableCommandFeedback"
        class="chat-msg__command-feedback"
        data-testid="command-feedback"
      >
        <div class="chat-msg__command-feedback-head">
          <span class="chat-msg__command-feedback-name">{{ commandFeedbackLabel }}</span>
          <span class="chat-msg__command-feedback-status">暂不可用</span>
        </div>
        <ul
          v-if="commandFeedbackReasons.length"
          class="chat-msg__command-feedback-reasons"
        >
          <li
            v-for="reason in commandFeedbackReasons"
            :key="reason"
          >
            {{ reason }}
          </li>
        </ul>
      </div>
      <div
        v-if="agentHealthProjection"
        class="chat-msg__agent-health"
        data-testid="agent-health-card"
      >
        <div class="chat-msg__agent-health-head">
          <span class="chat-msg__agent-health-title">Agent 状态</span>
          <span class="chat-msg__agent-health-status">{{ agentHealthStatusLabel }}</span>
        </div>
        <ul
          v-if="agentHealthDiagnostics.length"
          class="chat-msg__agent-health-list"
        >
          <li
            v-for="diagnostic in agentHealthDiagnostics"
            :key="diagnostic.code || diagnostic.message"
          >
            {{ diagnostic.message }}
          </li>
        </ul>
        <div
          v-if="agentHealthRouteRegistryChips.length"
          class="chat-msg__agent-health-tools"
        >
          <span>Worker 路由</span>
          <code
            v-for="chip in agentHealthRouteRegistryChips"
            :key="`worker-route:${chip}`"
          >
            {{ chip }}
          </code>
        </div>
        <div
          v-if="agentHealthRecommendedTools.length"
          class="chat-msg__agent-health-tools"
        >
          <span>建议工具</span>
          <code
            v-for="tool in agentHealthRecommendedTools"
            :key="tool"
          >
            {{ tool }}
          </code>
        </div>
      </div>
      <div
        v-if="agentControlProjection"
        class="chat-msg__agent-control"
        data-testid="agent-control-card"
      >
        <div class="chat-msg__agent-control-head">
          <span class="chat-msg__agent-control-command">{{ agentControlCommandLabel }}</span>
          <span class="chat-msg__agent-control-route">{{ agentControlRouteLabel }}</span>
        </div>
        <div class="chat-msg__agent-control-reason">{{ agentControlReasonLabel }}</div>
        <div
          v-if="agentControlRequiredTools.length"
          class="chat-msg__agent-control-tools"
        >
          <span>依赖工具</span>
          <code
            v-for="tool in agentControlRequiredTools"
            :key="tool"
          >
            {{ tool }}
          </code>
        </div>
      </div>
      <ActionCard
        v-if="msg.pending_action && isLatest"
        :action="msg.pending_action"
        :disabled="loading"
        @decide="onDecide"
        @safety-action="onSafetyAction"
      />
      <div
        v-if="msg.action_result"
        class="chat-msg__result"
        :class="`chat-msg__result--${resultVariant}`"
      >
        <div class="chat-msg__result-label">{{ resultText }}</div>
        <dl
          v-if="resultDetailItems.length"
          class="chat-msg__result-details"
        >
          <div
            v-for="item in resultDetailItems"
            :key="`${item.label}:${item.value}`"
            class="chat-msg__result-detail"
          >
            <dt>{{ item.label }}</dt>
            <dd>{{ item.value }}</dd>
          </div>
        </dl>
        <button
          v-if="agentRunId"
          type="button"
          class="chat-msg__result-action"
          data-testid="open-agent-run"
          @click="openAgentRun"
        >
          查看运行
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-msg {
  display: flex;
}

.chat-msg--left {
  justify-content: flex-start;
}

.chat-msg--right {
  justify-content: flex-end;
}

.chat-msg__bubble {
  max-width: 85%;
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
}

.chat-msg__bubble--assistant {
  background: var(--color-bg-white);
  border-left: 3px solid var(--color-brand);
}

.chat-msg__bubble--system {
  background: var(--color-bg-secondary);
  border-left: 3px solid var(--color-border-strong);
}

.chat-msg__bubble--user {
  background: var(--color-brand-light);
  max-width: 80%;
}

.chat-msg__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  min-width: 0;
  margin-bottom: var(--space-1);
}

.chat-msg__role {
  min-width: 0;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.chat-msg__time {
  flex: 0 0 auto;
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  line-height: 24px;
}

.chat-msg__trace {
  flex: 0 0 auto;
  max-width: 4.5rem;
  height: 24px;
  padding: 0 var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  background: transparent;
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  line-height: 22px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-msg__trace:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}

.chat-msg__content {
  white-space: pre-wrap;
  font-size: var(--text-sm);
  line-height: var(--leading-relaxed);
  color: var(--color-text-primary);
}

.chat-msg__command-feedback {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-error-light);
  border-left: 3px solid var(--color-error);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.chat-msg__command-feedback-head {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}

.chat-msg__command-feedback-name {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.chat-msg__command-feedback-status {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-error);
}

.chat-msg__command-feedback-reasons {
  margin: var(--space-1) 0 0;
  padding-left: var(--space-4);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}

.chat-msg__agent-health {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-brand);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.chat-msg__agent-health-head {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
  justify-content: space-between;
}

.chat-msg__agent-health-title {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
}

.chat-msg__agent-health-status {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-brand);
}

.chat-msg__agent-health-list {
  margin: var(--space-2) 0 0;
  padding-left: var(--space-4);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}

.chat-msg__agent-health-tools {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  align-items: center;
  margin-top: var(--space-2);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.chat-msg__agent-health-tools code {
  padding: 1px var(--space-1);
  border-radius: var(--radius-sm);
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.chat-msg__agent-control {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-warning);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.chat-msg__agent-control-head {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}

.chat-msg__agent-control-command {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.chat-msg__agent-control-route {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-warning);
}

.chat-msg__agent-control-reason {
  margin-top: var(--space-1);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}

.chat-msg__agent-control-tools {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  align-items: center;
  margin-top: var(--space-2);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.chat-msg__agent-control-tools code {
  padding: 1px var(--space-1);
  border-radius: var(--radius-sm);
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
  font-family: var(--font-mono);
}

.chat-msg__result {
  margin-top: var(--space-2);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
}

.chat-msg__result-label {
  line-height: var(--leading-normal);
}

.chat-msg__result-details {
  display: grid;
  gap: var(--space-1);
  margin: var(--space-2) 0 0;
}

.chat-msg__result-detail {
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: var(--space-2);
  align-items: baseline;
}

.chat-msg__result-detail dt {
  color: var(--color-text-tertiary);
}

.chat-msg__result-detail dd {
  margin: 0;
  min-width: 0;
  color: inherit;
  overflow-wrap: anywhere;
}

.chat-msg__result-action {
  margin-top: var(--space-2);
  height: 26px;
  padding: 0 var(--space-2);
  border: 1px solid currentColor;
  border-radius: var(--radius-sm);
  background: transparent;
  color: inherit;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  line-height: 24px;
}

.chat-msg__result-action:hover {
  background: rgba(255, 255, 255, 0.55);
}

.chat-msg__result--success {
  background: var(--color-success-light);
  color: var(--color-success);
}

.chat-msg__result--error {
  background: var(--color-error-light);
  color: var(--color-error);
}

.chat-msg__result--neutral {
  background: var(--color-bg-tertiary);
  color: var(--color-text-secondary);
}
</style>
