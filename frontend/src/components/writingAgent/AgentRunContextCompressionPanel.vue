<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const summary = computed(() => recordValue(props.output.summary))
const strategy = computed(() => recordValue(props.output.strategy))
const compressionPlan = computed(() => recordValue(props.output.compression_plan))
const risks = computed(() => recordList(props.output.risks))
const recommendedTools = computed(() => stringList(props.output.recommended_next_tools))
const chapterLabel = computed(() => chapterIndexLabel(props.output.chapter_index))
const granularityLabel = computed(() => granularityText(strategy.value.granularity))
const protectionLabel = computed(() => (
  strategy.value.protect_current_chapter === true ? '保护当前章节' : '不保护当前章节'
))
const promptChars = computed(() => numberValue(summary.value.prompt_context_chars))
const maxChars = computed(() => numberValue(summary.value.max_chars))
const usageLabel = computed(() => {
  const ratio = numberValue(summary.value.usage_ratio)
  if (ratio === null) return ''
  return `使用率 ${Math.round(ratio * 100)}%`
})
const truncatedSectionCount = computed(() => numberValue(summary.value.truncated_section_count))
const guardFailureCount = computed(() => numberValue(summary.value.context_guard_failure_count))
const targetMaxChars = computed(() => numberValue(compressionPlan.value.target_max_chars))
const headProtectionCount = computed(() => stringList(compressionPlan.value.protected_head_sections).length)
const tailProtectionCount = computed(() => stringList(compressionPlan.value.protected_tail_sections).length)
const pretrimCount = computed(() => stringList(compressionPlan.value.pretrim_order).length)
const summaryRequiredLabel = computed(() => (
  compressionPlan.value.llm_summary_required === true ? '需要 LLM 摘要' : '无需 LLM 摘要'
))
const riskRows = computed(() => (
  risks.value
    .map((risk, index) => ({
      key: `context-compression-risk:${index}`,
      code: safeText(risk.code),
      severity: severityLabel(risk.severity),
      message: safeText(risk.message),
    }))
    .filter((risk) => Boolean(risk.code || risk.message))
))

function statusLabel(status: unknown) {
  const value = stringValue(status)
  if (value === 'ready') return '可用'
  if (value === 'warning') return '警告'
  if (value === 'blocked') return '已阻塞'
  if (value === 'completed' || value === 'success') return '已完成'
  return value || '未知'
}

function granularityText(granularity: unknown) {
  const value = stringValue(granularity)
  if (value === 'chapter_window') return '章节窗口'
  return value || '未知'
}

function severityLabel(severity: unknown) {
  const value = stringValue(severity)
  if (value === 'warning') return '警告'
  if (value === 'error') return '错误'
  if (value === 'info') return '信息'
  return value
}

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function safeText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_.:-]+/.test(value)) return ''
  if (/project-secret|memory-secret|longform-memory-secret|source-secret|critical-secret|source_refs?|source_type|source_id|source_sections?|source_section_keys|memory_provenance|LongformMemory|phase\d+\.agent_context_compression|runtime_behavior_changed|include_prompt_context|context_guard_failure_count|compressed_context|prompt context raw/i.test(value)) return ''
  return value.slice(0, 120)
}
</script>

<template>
  <section
    class="agent-run-drawer__context-compression"
    aria-label="Agent context compression projection"
  >
    <h4>上下文压缩</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(output.status) }}</dd>
      </div>
      <div v-if="chapterLabel">
        <dt>章节</dt>
        <dd>{{ chapterLabel }}</dd>
      </div>
      <div v-if="granularityLabel">
        <dt>粒度</dt>
        <dd>{{ granularityLabel }}</dd>
      </div>
      <div>
        <dt>保护</dt>
        <dd>{{ protectionLabel }}</dd>
      </div>
      <div v-if="promptChars !== null">
        <dt>上下文</dt>
        <dd>上下文字符 {{ promptChars }}</dd>
      </div>
      <div v-if="maxChars !== null">
        <dt>预算</dt>
        <dd>预算 {{ maxChars }}</dd>
      </div>
      <div v-if="usageLabel">
        <dt>使用率</dt>
        <dd>{{ usageLabel }}</dd>
      </div>
      <div v-if="truncatedSectionCount !== null">
        <dt>截断</dt>
        <dd>截断分区 {{ truncatedSectionCount }}</dd>
      </div>
      <div v-if="guardFailureCount !== null">
        <dt>Guard</dt>
        <dd>Guard 失败 {{ guardFailureCount }}</dd>
      </div>
      <div v-if="targetMaxChars !== null">
        <dt>目标</dt>
        <dd>目标 {{ targetMaxChars }}</dd>
      </div>
      <div>
        <dt>头部</dt>
        <dd>头部保护 {{ headProtectionCount }}</dd>
      </div>
      <div>
        <dt>尾部</dt>
        <dd>尾部保护 {{ tailProtectionCount }}</dd>
      </div>
      <div>
        <dt>预修剪</dt>
        <dd>预修剪 {{ pretrimCount }}</dd>
      </div>
      <div>
        <dt>摘要</dt>
        <dd>{{ summaryRequiredLabel }}</dd>
      </div>
    </dl>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`context-compression-tool:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
    <ul
      v-if="riskRows.length"
      class="agent-run-drawer__planner-signals"
    >
      <li
        v-for="risk in riskRows"
        :key="risk.key"
      >
        <strong v-if="risk.code">{{ risk.code }}</strong>
        <span v-if="risk.severity">{{ risk.severity }}</span>
        <span v-if="risk.message">{{ risk.message }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__context-compression {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__context-compression h4 {
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
.agent-run-drawer__planner-signals {
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
}
</style>
