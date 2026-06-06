<script setup lang="ts">
import { computed } from 'vue'
import {
  contextCompressionChapterLabel,
  contextCompressionSeverityLabel,
  contextCompressionStatusLabel,
  safeContextCompressionText,
} from './agentRunProjection/contextCompressionProjection'
import { numberValue, recordList, recordValue, stringList } from './agentRunProjection/safeProjection'

const props = defineProps<{
  step: unknown
}>()

const step = computed(() => recordValue(props.step))
const output = computed(() => recordValue(step.value.output))
const input = computed(() => recordValue(step.value.input))
const checks = computed(() => recordValue(output.value.checks))
const compression = computed(() => recordValue(checks.value.context_compression))
const summary = computed(() => recordValue(compression.value.summary))
const compressionPlan = computed(() => recordValue(compression.value.compression_plan))
const preview = computed(() => recordValue(output.value.context_compression_payload_preview))
const previewPayload = computed(() => recordValue(preview.value.compression_payload))
const issues = computed(() => recordList(output.value.issues))
const hasProjection = computed(() => Boolean(Object.keys(compression.value).length))
const chapterLabel = computed(() => (
  contextCompressionChapterLabel(compression.value.chapter_index) ||
  contextCompressionChapterLabel(output.value.chapter_index) ||
  contextCompressionChapterLabel(input.value.chapter_index)
))
const promptChars = computed(() => numberValue(summary.value.prompt_context_chars))
const maxChars = computed(() => numberValue(summary.value.max_chars))
const usageLabel = computed(() => {
  const ratio = numberValue(summary.value.usage_ratio)
  if (ratio === null) return ''
  return `使用率 ${Math.round(ratio * 100)}%`
})
const targetMaxChars = computed(() => (
  numberValue(compressionPlan.value.target_max_chars) ??
  numberValue(previewPayload.value.target_max_chars)
))
const previewLabel = computed(() => (
  Object.keys(preview.value).length ? contextCompressionStatusLabel(preview.value.status) : ''
))
const compressedChars = computed(() => numberValue(previewPayload.value.compressed_context_chars))
const recommendedTools = computed(() => {
  const seen = new Set<string>()
  return [
    ...stringList(output.value.recommended_next_tools),
    ...stringList(preview.value.recommended_next_tools),
  ].filter((tool) => {
    if (seen.has(tool)) return false
    seen.add(tool)
    return true
  })
})
const issueRows = computed(() => (
  issues.value
    .filter((issue) => safeContextCompressionText(issue.code).startsWith('context_compression'))
    .slice(0, 4)
    .map((issue, index) => ({
      key: `preflight-budget-issue:${index}`,
      code: safeContextCompressionText(issue.code),
      severity: contextCompressionSeverityLabel(issue.severity),
      message: safeContextCompressionText(issue.message),
    }))
    .filter((issue) => Boolean(issue.code || issue.message))
))
</script>

<template>
  <section
    v-if="hasProjection"
    class="agent-run-drawer__context-budget"
    aria-label="Agent preflight context budget"
  >
    <h4>上下文预算</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ contextCompressionStatusLabel(compression.status) }}</dd>
      </div>
      <div v-if="chapterLabel">
        <dt>章节</dt>
        <dd>{{ chapterLabel }}</dd>
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
      <div v-if="targetMaxChars !== null">
        <dt>目标</dt>
        <dd>目标 {{ targetMaxChars }}</dd>
      </div>
      <div v-if="previewLabel">
        <dt>预览</dt>
        <dd>压缩预览 {{ previewLabel }}</dd>
      </div>
      <div v-if="compressedChars !== null">
        <dt>压缩</dt>
        <dd>压缩字符 {{ compressedChars }}</dd>
      </div>
    </dl>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`preflight-budget-tool:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
    <ul
      v-if="issueRows.length"
      class="agent-run-drawer__planner-signals"
    >
      <li
        v-for="issue in issueRows"
        :key="issue.key"
      >
        <strong v-if="issue.code">{{ issue.code }}</strong>
        <span v-if="issue.severity">{{ issue.severity }}</span>
        <span v-if="issue.message">{{ issue.message }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__context-budget {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__context-budget h4 {
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
