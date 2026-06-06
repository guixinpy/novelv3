<script setup lang="ts">
import { computed } from 'vue'
import { numberValue, recordList, recordValue, stringList, stringValue } from './agentRunProjection/safeProjection'

const props = defineProps<{
  output: Record<string, unknown>
}>()

const summary = computed(() => recordValue(props.output.context_summary))
const activeState = computed(() => recordValue(summary.value.active_state))
const targetOutline = computed(() => recordValue(activeState.value.target_outline))
const decision = computed(() => recordValue(props.output.decision))
const progress = computed(() => recordValue(props.output.progress))
const limits = computed(() => recordValue(props.output.limits))
const provenance = computed(() => recordValue(props.output.memory_provenance))
const promptWindow = computed(() => recordValue(provenance.value.prompt_context))
const diagnostics = computed(() => recordList(props.output.diagnostics))
const status = computed(() => stringValue(props.output.status))
const chapterLabel = computed(() => chapterIndexLabel(props.output.chapter_index))
const goal = computed(() => safeText(summary.value.goal))
const outlineTitle = computed(() => safeText(targetOutline.value.title))
const outlineSummary = computed(() => safeText(targetOutline.value.summary))
const generatedChapterCount = computed(() => numberValue(progress.value.generated_chapter_count))
const latestChapterLabel = computed(() => chapterIndexLabel(progress.value.latest_generated_chapter_index))
const generatedWordCount = computed(() => numberValue(progress.value.generated_word_count))
const promptChars = computed(() => (
  numberValue(props.output.prompt_context_chars) ?? numberValue(promptWindow.value.chars)
))
const budgetChars = computed(() => (
  numberValue(limits.value.max_chars) ?? numberValue(promptWindow.value.max_chars)
))
const provenanceStatus = computed(() => stringValue(provenance.value.status))
const generationLabel = computed(() => {
  if (props.output.should_generate_next_chapter === true) return '可用于生成'
  if (props.output.should_generate_next_chapter === false) return '暂不生成'
  const decisionStatus = stringValue(decision.value.status)
  if (decisionStatus === 'ready') return '可用于生成'
  if (decisionStatus === 'blocked') return '已阻塞'
  return safeText(decision.value.message) || decisionStatus
})
const recommendedActions = computed(() => stringList(props.output.recommended_actions))
const sectionRows = computed(() => (
  recordList(props.output.sections)
    .slice(0, 4)
    .map((section, sectionIndex) => {
      const title = safeText(section.title) || '上下文分区'
      const itemCount = numberValue(section.item_count)
      const items = recordList(section.items)
        .slice(0, 2)
        .map((item, itemIndex) => ({
          key: `longform-context-section:${sectionIndex}:item:${itemIndex}`,
          title: safeText(item.title),
          summary: safeText(item.summary),
        }))
        .filter((item) => Boolean(item.title || item.summary))
      return {
        key: `longform-context-section:${sectionIndex}`,
        title,
        itemCount,
        items,
      }
    })
    .filter((section) => Boolean(section.title || section.items.length))
))
const diagnosticRows = computed(() => (
  diagnostics.value
    .slice(0, 4)
    .map((item, index) => ({
      key: `longform-context-diagnostic:${index}`,
      code: safeText(item.code),
      message: safeText(item.message),
    }))
    .filter((item) => Boolean(item.code || item.message))
))

function statusLabel(value: unknown) {
  const statusValue = stringValue(value)
  if (statusValue === 'success' || statusValue === 'completed') return '已完成'
  if (statusValue === 'running') return '进行中'
  if (statusValue === 'failed') return '失败'
  if (statusValue === 'blocked') return '已阻止'
  if (statusValue === 'pending') return '待执行'
  return statusValue || '待执行'
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

function chapterIndexLabel(value: unknown) {
  const index = numberValue(value)
  return index !== null ? `第${index}章` : ''
}

function safeText(label: unknown) {
  const value = stringValue(label).replace(/\s+/g, ' ')
  if (!value) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_.:-]+/.test(value)) return ''
  if (/project-secret|memory-secret|memory-overflow|chapter-content-\d+|source_refs?|source_type|source_id|memory_id|source_sections?|source_section_keys|longform_context_package|phase\d+\.longform_memory_provenance|phase\d+\.longform_context_summary|build_longform_context_package|Athena\/world_model|retrieved_memory_rollups_and_generation_context|raw prompt context/i.test(value)) return ''
  return value.slice(0, 120)
}
</script>

<template>
  <section
    class="agent-run-drawer__longform-context"
    aria-label="Agent longform context summary projection"
  >
    <h4>长篇上下文摘要</h4>
    <dl class="agent-run-drawer__facts">
      <div>
        <dt>状态</dt>
        <dd>{{ statusLabel(status) }}</dd>
      </div>
      <div v-if="chapterLabel">
        <dt>章节</dt>
        <dd>{{ chapterLabel }}</dd>
      </div>
      <div v-if="goal">
        <dt>目标</dt>
        <dd>{{ goal }}</dd>
      </div>
      <div v-if="generationLabel">
        <dt>生成判断</dt>
        <dd>{{ generationLabel }}</dd>
      </div>
      <div v-if="generatedChapterCount !== null">
        <dt>已生成</dt>
        <dd>已生成 {{ generatedChapterCount }}</dd>
      </div>
      <div v-if="latestChapterLabel">
        <dt>最新章节</dt>
        <dd>最新章节 {{ latestChapterLabel }}</dd>
      </div>
      <div v-if="generatedWordCount !== null">
        <dt>字数</dt>
        <dd>字数 {{ generatedWordCount }}</dd>
      </div>
      <div v-if="promptChars !== null">
        <dt>上下文字符</dt>
        <dd>上下文字符 {{ promptChars }}</dd>
      </div>
      <div v-if="budgetChars !== null">
        <dt>预算</dt>
        <dd>预算 {{ budgetChars }}</dd>
      </div>
      <div v-if="provenanceStatus">
        <dt>来源覆盖</dt>
        <dd>{{ provenanceStatusLabel(provenanceStatus) }}</dd>
      </div>
      <div v-if="outlineTitle">
        <dt>目标大纲</dt>
        <dd>{{ outlineTitle }}</dd>
      </div>
      <div v-if="outlineSummary">
        <dt>大纲摘要</dt>
        <dd>{{ outlineSummary }}</dd>
      </div>
    </dl>
    <ul
      v-if="recommendedActions.length"
      class="agent-run-drawer__tools"
    >
      <li
        v-for="action in recommendedActions"
        :key="`longform-context-action:${action}`"
      >
        {{ action }}
      </li>
    </ul>
    <ul
      v-if="sectionRows.length"
      class="agent-run-drawer__reference-patterns"
    >
      <li
        v-for="section in sectionRows"
        :key="section.key"
      >
        <div>
          <strong>
            {{ section.itemCount !== null ? `${section.title} ${section.itemCount}` : section.title }}
          </strong>
        </div>
        <template
          v-for="item in section.items"
          :key="item.key"
        >
          <p v-if="item.title"><strong>{{ item.title }}</strong></p>
          <p v-if="item.summary && item.summary !== item.title">{{ item.summary }}</p>
        </template>
      </li>
    </ul>
    <ul
      v-if="diagnosticRows.length"
      class="agent-run-drawer__planner-signals"
    >
      <li
        v-for="diagnostic in diagnosticRows"
        :key="diagnostic.key"
      >
        <strong v-if="diagnostic.code">{{ diagnostic.code }}</strong>
        <span v-if="diagnostic.message">{{ diagnostic.message }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.agent-run-drawer__longform-context {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.agent-run-drawer__longform-context h4 {
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

.agent-run-drawer__tools {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
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

.agent-run-drawer__reference-patterns,
.agent-run-drawer__planner-signals {
  display: grid;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}

.agent-run-drawer__reference-patterns li,
.agent-run-drawer__planner-signals li {
  display: grid;
  gap: var(--space-1);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
}

.agent-run-drawer__reference-patterns div {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}

.agent-run-drawer__reference-patterns strong,
.agent-run-drawer__planner-signals strong {
  color: var(--color-text-primary);
  font-size: var(--text-xs);
}

.agent-run-drawer__planner-signals span {
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.agent-run-drawer__reference-patterns p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: 1.5;
  overflow-wrap: anywhere;
}
</style>
