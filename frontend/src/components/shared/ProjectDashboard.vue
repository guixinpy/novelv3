<script setup lang="ts">
import { computed } from 'vue'
import type { PendingAction } from '../../api/types'

const props = defineProps<{
  setup: any
  storyline: any
  outline: any
  chapters: any[]
  totalWords: number
  pendingAction?: PendingAction | null
  aiLoading?: boolean
  latestActionLabel?: string
  latestActionStatus?: string | null
  suggestedNextStep?: string | null
}>()

const emit = defineEmits<{
  tool: [tool: 'manuscript' | 'versions' | 'export']
}>()

type StageCard = {
  key: 'setup' | 'storyline' | 'outline'
  title: string
  status: string
  statusTone: 'done' | 'warning' | 'empty'
  summary: string
  progress: number | null
}

function asArray(value: unknown): any[] {
  return Array.isArray(value) ? value : []
}

function countFilledFields(source: Record<string, unknown> | null | undefined, fields: string[]) {
  if (!source) return 0
  return fields.filter((field) => {
    const value = source[field]
    return typeof value === 'string' ? value.trim().length > 0 : Boolean(value)
  }).length
}

const setupCard = computed<StageCard>(() => {
  const characters = asArray(props.setup?.characters)
  const worldFields = ['background', 'geography', 'society', 'rules', 'atmosphere']
  const coreFields = ['theme', 'premise', 'hook', 'unique_selling_point']
  const worldCount = countFilledFields(props.setup?.world_building, worldFields)
  const coreCount = countFilledFields(props.setup?.core_concept, coreFields)
  const complete = characters.length > 0 && worldCount === worldFields.length && coreCount === coreFields.length
  return {
    key: 'setup',
    title: '设定',
    status: props.setup ? complete ? '已生成' : '待完善' : '未创建',
    statusTone: props.setup ? complete ? 'done' : 'warning' : 'empty',
    summary: props.setup
      ? `角色 ${characters.length} · 世界观 ${worldCount}/${worldFields.length} · 核心概念 ${coreCount}/${coreFields.length}`
      : '还没有项目基础设定',
    progress: null,
  }
})

const storylineCard = computed<StageCard>(() => {
  const plotlines = asArray(props.storyline?.plotlines)
  const foreshadowing = asArray(props.storyline?.foreshadowing)
  const complete = plotlines.length > 0
  return {
    key: 'storyline',
    title: '故事线',
    status: props.storyline ? complete ? '已生成' : '待完善' : '未创建',
    statusTone: props.storyline ? complete ? 'done' : 'warning' : 'empty',
    summary: props.storyline
      ? `主线 ${plotlines.length} · 伏笔 ${foreshadowing.length}`
      : '还没有主线和伏笔规划',
    progress: null,
  }
})

const outlineCard = computed<StageCard>(() => {
  const outlineChapters = asArray(props.outline?.chapters)
  const plannedChapters = Number(props.outline?.total_chapters || outlineChapters.length || 0)
  const writtenChapters = props.chapters.length
  const progress = plannedChapters > 0 ? Math.min(100, Math.round((writtenChapters / plannedChapters) * 100)) : 0
  return {
    key: 'outline',
    title: '大纲',
    status: props.outline ? `${plannedChapters}章规划` : '未创建',
    statusTone: props.outline ? 'done' : 'empty',
    summary: props.outline
      ? `正文 ${writtenChapters}/${plannedChapters || 0} · ${progress}%`
      : '还没有章节大纲',
    progress: props.outline ? progress : null,
  }
})

const stageCards = computed(() => [setupCard.value, storylineCard.value, outlineCard.value])

const aiStatusLabel = computed(() => {
  if (props.pendingAction) return '待确认'
  if (props.aiLoading) return '运行中'
  if (props.latestActionStatus === 'failed') return '需处理'
  if (props.latestActionStatus === 'cancelled') return '已取消'
  if (props.latestActionStatus === 'revised') return '已修订'
  if (props.latestActionStatus === 'completed' || props.latestActionStatus === 'success') return '已完成'
  return '空闲'
})

const aiStatusClass = computed(() => {
  if (props.pendingAction) return 'dashboard__status--warning'
  if (props.aiLoading) return 'dashboard__status--running'
  if (props.latestActionStatus === 'failed') return 'dashboard__status--danger'
  return 'dashboard__status--idle'
})

const aiTaskTitle = computed(() => {
  if (props.pendingAction?.description) return props.pendingAction.description
  if (props.aiLoading) return 'Hermes 正在处理任务'
  if (props.latestActionLabel) return props.latestActionLabel
  return '暂无进行中的 AI 任务'
})

const totalWordsLabel = computed(() => props.totalWords >= 10000 ? `${(props.totalWords / 10000).toFixed(1)}万` : props.totalWords)
</script>

<template>
  <div class="dashboard">
    <section class="dashboard__section">
      <h3 class="dashboard__section-title">生产总览</h3>
      <article
        v-for="card in stageCards"
        :key="card.key"
        class="dashboard__stage-card"
      >
        <div class="dashboard__stage-head">
          <span class="dashboard__stage-title">{{ card.title }}</span>
          <span class="dashboard__stage-status" :class="`dashboard__stage-status--${card.statusTone}`">{{ card.status }}</span>
        </div>
        <div class="dashboard__stage-summary">{{ card.summary }}</div>
        <div
          v-if="card.progress !== null"
          class="dashboard__stage-progress"
          role="progressbar"
          :aria-valuenow="card.progress"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <span :style="{ width: `${card.progress}%` }" />
        </div>
      </article>
      <div class="dashboard__stats">
        <div class="dashboard__stat">
          <span class="dashboard__stat-value">{{ chapters.length }}</span>
          <span class="dashboard__stat-label">章节</span>
        </div>
        <div class="dashboard__stat">
          <span class="dashboard__stat-value">{{ totalWordsLabel }}</span>
          <span class="dashboard__stat-label">字数</span>
        </div>
      </div>
    </section>

    <section class="dashboard__section">
      <h3 class="dashboard__section-title">AI 任务</h3>
      <div class="dashboard__task">
        <div class="dashboard__task-top">
          <span class="dashboard__task-title">{{ aiTaskTitle }}</span>
          <span class="dashboard__status" :class="aiStatusClass">{{ aiStatusLabel }}</span>
        </div>
        <p v-if="suggestedNextStep" class="dashboard__next">建议：{{ suggestedNextStep }}</p>
      </div>
    </section>

    <section class="dashboard__section">
      <h3 class="dashboard__section-title">项目工具</h3>
      <button class="dashboard__tool" data-testid="dashboard-tool-manuscript" @click="emit('tool', 'manuscript')">
        <span>Calliope</span>
        <small>正文编辑</small>
      </button>
      <button class="dashboard__tool" data-testid="dashboard-tool-versions" @click="emit('tool', 'versions')">
        <span>版本历史</span>
        <small>查看与回滚</small>
      </button>
      <button class="dashboard__tool" data-testid="dashboard-tool-export" @click="emit('tool', 'export')">
        <span>导出</span>
        <small>生成项目文件</small>
      </button>
    </section>
  </div>
</template>

<style scoped>
.dashboard {
  padding: var(--space-2) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.dashboard__section {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.dashboard__section + .dashboard__section {
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-3);
}

.dashboard__section-title {
  margin: 0 0 var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-tertiary);
}

.dashboard__stage-card {
  display: block;
  padding: var(--space-3);
  border: 1px solid transparent;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.64);
  text-align: left;
}

.dashboard__stage-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.dashboard__stage-title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.dashboard__stage-status {
  flex-shrink: 0;
  border-radius: var(--radius-full);
  padding: 0.12rem 0.45rem;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.dashboard__stage-status--done { background: rgba(34, 197, 94, 0.12); color: #16a34a; }
.dashboard__stage-status--warning { background: rgba(245, 158, 11, 0.14); color: #b45309; }
.dashboard__stage-status--empty { background: var(--color-bg-secondary); color: var(--color-text-tertiary); }

.dashboard__stage-summary {
  margin-top: var(--space-2);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  line-height: var(--leading-snug);
}

.dashboard__stage-progress {
  height: 5px;
  margin-top: var(--space-2);
  border-radius: var(--radius-full);
  background: var(--color-bg-secondary);
  overflow: hidden;
}

.dashboard__stage-progress span {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--color-brand);
}

.dashboard__stats {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-2) var(--space-2) 0;
}

.dashboard__stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.dashboard__stat-value {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  line-height: var(--leading-tight);
}

.dashboard__stat-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.dashboard__task {
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-white);
}

.dashboard__task-top {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
}

.dashboard__task-title {
  min-width: 0;
  flex: 1;
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  line-height: var(--leading-snug);
}

.dashboard__status {
  flex-shrink: 0;
  border-radius: var(--radius-full);
  padding: 0.15rem 0.45rem;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.dashboard__status--idle { background: var(--color-bg-secondary); color: var(--color-text-tertiary); }
.dashboard__status--running { background: rgba(59, 130, 246, 0.12); color: #2563eb; }
.dashboard__status--warning { background: rgba(245, 158, 11, 0.14); color: #b45309; }
.dashboard__status--danger { background: rgba(239, 68, 68, 0.12); color: #dc2626; }

.dashboard__next {
  margin: var(--space-2) 0 0;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  line-height: var(--leading-snug);
}

.dashboard__tool {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-2);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-primary);
  text-align: left;
  transition: background var(--transition-fast);
}

.dashboard__tool:hover {
  background: var(--color-bg-secondary);
}

.dashboard__tool span {
  font-size: var(--text-sm);
}

.dashboard__tool small {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}
</style>
