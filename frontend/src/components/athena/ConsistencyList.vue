<script setup lang="ts">
import { computed, ref } from 'vue'
import BaseBadge from '../base/BaseBadge.vue'
import type { AthenaConsistencyIssue } from '../../api/types'

const props = defineProps<{
  issues: AthenaConsistencyIssue[]
  latestChapterIndex?: number | null
  loading?: boolean
}>()

const emit = defineEmits<{
  runCheck: [chapterIndex: number]
}>()

const expandedIdx = ref<number | null>(null)
const canRunLatestCheck = computed(() => Number.isFinite(props.latestChapterIndex))

function toggle(idx: number) {
  expandedIdx.value = expandedIdx.value === idx ? null : idx
}

function runLatestCheck() {
  if (!canRunLatestCheck.value || props.loading) return
  emit('runCheck', Number(props.latestChapterIndex))
}

const severityVariant: Record<string, 'success' | 'warning' | 'error' | 'neutral'> = {
  pass: 'success',
  warn: 'warning',
  warning: 'warning',
  fatal: 'error',
  error: 'error',
  info: 'neutral',
}

function issueSeverity(issue: AthenaConsistencyIssue) {
  return issue.severity || issue.status || 'info'
}

function issueVariant(issue: AthenaConsistencyIssue) {
  return severityVariant[issueSeverity(issue)] || 'neutral'
}
</script>

<template>
  <div class="consistency-list">
    <div class="consistency-list__toolbar">
      <button
        v-if="canRunLatestCheck"
        class="consistency-list__run-button"
        data-testid="athena-consistency-run-latest"
        type="button"
        :disabled="loading"
        @click="runLatestCheck"
      >
        检查最新章节
      </button>
    </div>
    <div v-if="issues.length === 0" class="consistency-list__empty">暂无一致性检查结果</div>
    <div
      v-for="(issue, idx) in issues"
      :key="idx"
      class="consistency-list__item"
    >
      <button class="consistency-list__header" @click="toggle(idx)">
        <BaseBadge :variant="issueVariant(issue)" size="sm">
          {{ issueSeverity(issue) }}
        </BaseBadge>
        <span class="consistency-list__type">{{ issue.checker_name || issue.check_type || issue.type || '' }}</span>
        <span class="consistency-list__desc">{{ issue.description || issue.message || '' }}</span>
        <span class="consistency-list__chevron">{{ expandedIdx === idx ? '▾' : '▸' }}</span>
      </button>
      <div v-if="expandedIdx === idx && issue.evidence" class="consistency-list__evidence">
        {{ typeof issue.evidence === 'string' ? issue.evidence : JSON.stringify(issue.evidence) }}
      </div>
    </div>
  </div>
</template>
<style scoped>
.consistency-list__toolbar {
  display: flex;
  justify-content: flex-end;
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--color-border);
}

.consistency-list__run-button {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-primary);
  background: var(--color-bg-primary);
  font-size: var(--text-sm);
  cursor: pointer;
}

.consistency-list__run-button:disabled {
  cursor: default;
  opacity: 0.6;
}

.consistency-list__item {
  border-bottom: 1px solid var(--color-border);
}

.consistency-list__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  width: 100%;
  padding: var(--space-3) 0;
  background: transparent;
  border: none;
  cursor: pointer;
  text-align: left;
}

.consistency-list__type {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  min-width: 80px;
}

.consistency-list__desc {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  flex: 1;
}

.consistency-list__chevron {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.consistency-list__evidence {
  padding: var(--space-2) var(--space-4) var(--space-3);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-2);
}

.consistency-list__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}
</style>
