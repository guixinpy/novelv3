<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const summary = computed(() => recordValue(props.output.summary))
const provenance = computed(() => recordValue(props.output.memory_provenance))
const status = computed(() => stringValue(props.output.status))
const chapterLabel = computed(() => chapterIndexLabel(props.output.chapter_index))
const captureStatus = computed(() => stringValue(props.output.capture_status))
const chapterAvailabilityLabel = computed(() => (
  summary.value.chapter_available === true ? '章节可用' : '章节缺失'
))
const candidateCount = computed(() => numberValue(summary.value.candidate_count))
const reviewStepCount = computed(() => numberValue(summary.value.review_step_count))
const recommendedTools = computed(() => stringList(props.output.recommended_next_tools))
const candidates = computed(() => recordList(props.output.candidates))
const provenanceStatus = computed(() => stringValue(provenance.value.status))
const candidateRows = computed(() => (
  candidates.value
    .slice(0, 5)
    .map((candidate, index) => {
      const confidence = numberValue(candidate.confidence)
      const evidence = recordValue(candidate.evidence)
      return {
        key: `post-memory-candidate:${index}`,
        title: safeText(candidate.title) || '写后记忆候选',
        type: candidateTypeLabel(candidate.memory_type),
        summary: safeText(candidate.summary),
        chapterLabel: chapterIndexLabel(evidence.chapter_index),
        confidenceLabel: confidence !== null ? `置信 ${confidence}` : '',
      }
    })
    .filter((candidate) => Boolean(candidate.title || candidate.summary))
))

function statusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'completed' || statusValue === 'success') return '已完成'
  if (statusValue === 'running') return '进行中'
  if (statusValue === 'failed') return '失败'
  if (statusValue === 'blocked') return '已阻塞'
  return statusValue || '未知'
}

function captureStatusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'ready') return '可写入候选'
  if (statusValue === 'needs_review') return '需要审稿'
  if (statusValue === 'missing_chapter') return '缺少章节'
  return statusValue || '未知'
}

function provenanceStatusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'available') return '可用'
  if (statusValue === 'degraded') return '降级'
  if (statusValue === 'truncated') return '截断'
  if (statusValue === 'sparse') return '稀疏'
  if (statusValue === 'blocked') return '已阻塞'
  return statusValue || '未知'
}

function candidateTypeLabel(memoryType: unknown) {
  const value = stringValue(memoryType)
  if (value === 'writing_pattern') return '写法模式'
  if (value === 'self_optimization_lesson') return '自优化经验'
  if (value === 'author_preference') return '作者偏好'
  if (value === 'project_policy') return '项目策略'
  if (value === 'learned_rule') return '学习规则'
  return value || '知识库候选'
}

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function safeText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_-]+/.test(value)) return ''
  if (/project-secret|chapter-content-\d+|review-step-secret|source_refs?|source_type|source_id|chapter_content_id|review_step_ids|memory_provenance|next_tool_call|target_type|agent_post_chapter_memory_capture_plan|phase\d+\.post_chapter_memory_capture|approval_contract|approval:/i.test(value)) return ''
  return value.slice(0, 120)
}
</script>

<template>
  <section
    class="agent-run-drawer__post-memory"
    aria-label="Agent post-chapter memory capture projection"
  >
    <h4>写后记忆沉淀规划</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
      </div>
      <div v-if="chapterLabel">
        <dt>章节</dt>
        <dd>{{ chapterLabel }}</dd>
      </div>
      <div>
        <dt>沉淀状态</dt>
        <dd>{{ captureStatusLabel(captureStatus) }}</dd>
      </div>
      <div>
        <dt>章节证据</dt>
        <dd>{{ chapterAvailabilityLabel }}</dd>
      </div>
      <div v-if="candidateCount !== null">
        <dt>候选</dt>
        <dd>候选 {{ candidateCount }}</dd>
      </div>
      <div v-if="reviewStepCount !== null">
        <dt>审稿</dt>
        <dd>审稿证据 {{ reviewStepCount }}</dd>
      </div>
      <div v-if="provenanceStatus">
        <dt>来源覆盖</dt>
        <dd>{{ provenanceStatusLabel(provenanceStatus) }}</dd>
      </div>
    </dl>
    <ul
      v-if="recommendedTools.length"
      class="agent-run-drawer__write-tools"
    >
      <li
        v-for="tool in recommendedTools"
        :key="`post-memory-projection-next:${tool}`"
      >
        {{ tool }}
      </li>
    </ul>
    <ul
      v-if="candidateRows.length"
      class="agent-run-drawer__reference-patterns"
    >
      <li
        v-for="candidate in candidateRows"
        :key="candidate.key"
      >
        <div>
          <strong>{{ candidate.title }}</strong>
          <span v-if="candidate.type">{{ candidate.type }}</span>
          <span v-if="candidate.chapterLabel">{{ candidate.chapterLabel }}</span>
          <span v-if="candidate.confidenceLabel">{{ candidate.confidenceLabel }}</span>
        </div>
        <p v-if="candidate.summary">{{ candidate.summary }}</p>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__post-memory {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__post-memory h4 {
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

.agent-run-drawer__write-tools,
.agent-run-drawer__reference-patterns {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__write-tools li,
.agent-run-drawer__reference-patterns li {
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__reference-patterns li {
  display: grid;
  gap: var(--space-1);
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
</style>
