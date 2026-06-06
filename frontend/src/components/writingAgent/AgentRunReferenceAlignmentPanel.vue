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
const sourceCount = computed(() => numberValue(summary.value.source_count))
const patternCount = computed(() => numberValue(summary.value.pattern_count))
const decisionCount = computed(() => numberValue(summary.value.decision_count))
const capabilityAreaCount = computed(() => numberValue(summary.value.capability_area_count))
const adapterToolCount = computed(() => numberValue(summary.value.adapter_backed_tool_count))
const patterns = computed(() => (
  recordList(props.output.patterns)
    .slice(0, 3)
    .map((pattern, index) => ({
      key: `reference-alignment-pattern:${stringValue(pattern.source) || index}`,
      source: stringValue(pattern.source),
      appliedPatterns: appliedPatternsLabel(pattern.applied_patterns),
    }))
    .filter((pattern) => pattern.source || pattern.appliedPatterns)
))
const capabilities = computed(() => (
  recordList(props.output.capability_alignment)
    .slice(0, 4)
    .map((capability, index) => ({
      key: `reference-alignment-capability:${stringValue(capability.area) || index}`,
      area: stringValue(capability.area),
      status: capabilityStatusLabel(capability.status),
    }))
    .filter((capability) => capability.area || capability.status)
))
const recommendedTools = computed(() => stringList(props.output.recommended_next_tools))

function statusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'completed' || statusValue === 'success') return '已完成'
  if (statusValue === 'running') return '进行中'
  if (statusValue === 'failed') return '失败'
  return statusValue || '未知'
}

function capabilityStatusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'implemented') return '已实现'
  if (statusValue === 'descriptor_only') return '仅描述符'
  return statusValue || '未知'
}

function appliedPatternsLabel(value: unknown) {
  return stringList(value).join(', ')
}
</script>

<template>
  <section
    class="agent-run-drawer__reference-alignment"
    aria-label="Reference alignment projection"
  >
    <h4>参考项目对齐</h4>
    <dl class="agent-run-drawer__facts">
      <div v-if="status">
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
      </div>
      <div v-if="sourceCount !== null">
        <dt>参考项目</dt>
        <dd>{{ sourceCount }}</dd>
      </div>
      <div v-if="patternCount !== null">
        <dt>模式</dt>
        <dd>{{ patternCount }}</dd>
      </div>
      <div v-if="decisionCount !== null">
        <dt>决策</dt>
        <dd>{{ decisionCount }}</dd>
      </div>
      <div v-if="capabilityAreaCount !== null">
        <dt>能力域</dt>
        <dd>{{ capabilityAreaCount }}</dd>
      </div>
      <div v-if="adapterToolCount !== null">
        <dt>适配工具</dt>
        <dd>{{ adapterToolCount }}</dd>
      </div>
    </dl>
    <ul
      v-if="patterns.length"
      class="agent-run-drawer__reference-patterns"
    >
      <li
        v-for="pattern in patterns"
        :key="pattern.key"
      >
        <div>
          <strong>{{ pattern.source || '参考项目' }}</strong>
        </div>
        <p v-if="pattern.appliedPatterns">{{ pattern.appliedPatterns }}</p>
      </li>
    </ul>
    <ul
      v-if="capabilities.length"
      class="agent-run-drawer__worker-dispatches"
    >
      <li
        v-for="capability in capabilities"
        :key="capability.key"
      >
        <strong>{{ capability.area || '能力域' }}</strong>
        <span>{{ capability.status }}</span>
      </li>
    </ul>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`reference-alignment-next:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__reference-alignment {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__reference-alignment h4 {
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

.agent-run-drawer__reference-patterns,
.agent-run-drawer__worker-dispatches,
.agent-run-drawer__tools {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
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

.agent-run-drawer__reference-patterns p {
  margin: 0;
  color: var(--color-text-secondary);
  line-height: var(--leading-normal);
}

.agent-run-drawer__worker-dispatches li,
.agent-run-drawer__tools li {
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__worker-dispatches li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.agent-run-drawer__worker-dispatches span {
  color: var(--color-text-secondary);
}
</style>
