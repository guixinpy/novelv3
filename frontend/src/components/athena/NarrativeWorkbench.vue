<script setup lang="ts">
import { computed } from 'vue'
import type { AthenaEvolutionPlan, ChapterSummary } from '../../api/types'
import type { AthenaNarrativeView } from '../../views/athenaNavigation'

type RecordValue = Record<string, unknown>

const props = defineProps<{
  plan: AthenaEvolutionPlan | null
  chapters: ChapterSummary[]
  view: AthenaNarrativeView
}>()

const outlineChapters = computed(() =>
  asRecords(props.plan?.outline?.chapters)
    .map((chapter, index) => ({
      chapterIndex: toNumber(chapter.chapter_index),
      key: toText(chapter.chapter_index, `chapter-${index}`),
      title: toText(chapter.title, '未命名章节'),
      summary: toText(chapter.summary),
      scenes: toTextArray(chapter.scenes),
      characters: toTextArray(chapter.characters),
      purpose: toText(chapter.purpose),
      raw: chapter,
    }))
    .filter((chapter) => chapter.chapterIndex !== null)
    .sort((left, right) => Number(left.chapterIndex) - Number(right.chapterIndex)),
)

const plotlines = computed(() =>
  asRecords(props.plan?.storyline?.plotlines || props.plan?.outline?.plotlines)
    .map((plotline, index) => ({
      key: toText(plotline.name, `plotline-${index}`),
      name: toText(plotline.name, '未命名线索'),
      type: toText(plotline.type, '未分类'),
      milestones: asRecords(plotline.milestones)
        .map((milestone, milestoneIndex) => ({
          key: `${index}-${milestoneIndex}`,
          chapterIndex: toNumber(milestone.chapter_index),
          title: toText(milestone.title || milestone.summary || milestone.event, '未命名节点'),
          summary: toText(milestone.summary || milestone.description || milestone.event),
        })),
    })),
)

const foreshadowingItems = computed(() =>
  asRecords(props.plan?.storyline?.foreshadowing)
    .map((item, index) => ({
      key: `${toText(item.hint, 'hint')}-${index}`,
      hint: toText(item.hint, '未命名伏笔'),
      plantedChapter: toNumber(item.planted_chapter),
      resolvedChapter: toNumber(item.resolved_chapter),
      status: toText(item.status, 'unknown'),
    }))
    .sort((left, right) => Number(left.plantedChapter ?? 0) - Number(right.plantedChapter ?? 0)),
)

const chapterStatusByIndex = computed(() => {
  const map = new Map<number, ChapterSummary>()
  for (const chapter of props.chapters) {
    map.set(Number(chapter.chapter_index), chapter)
  }
  return map
})

const metrics = computed(() => [
  { label: '章节规划', value: outlineChapters.value.length },
  { label: '故事线', value: plotlines.value.length },
  { label: '伏笔', value: foreshadowingItems.value.length },
])

function asRecord(value: unknown): RecordValue | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null
}

function asRecords(value: unknown): RecordValue[] {
  return Array.isArray(value) ? value.map(asRecord).filter((item): item is RecordValue => item !== null) : []
}

function toText(value: unknown, fallback = '') {
  if (typeof value === 'string' && value.trim()) return value
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value)
  return fallback
}

function toNumber(value: unknown): number | null {
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : null
}

function toTextArray(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.map((item) => toText(item)).filter(Boolean)
}

function chapterStatus(chapterIndex: number | null) {
  if (chapterIndex === null) return null
  return chapterStatusByIndex.value.get(chapterIndex) || null
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    resolved: '已回收',
    planted: '已埋设',
    pending: '待回收',
    unknown: '未标注',
  }
  return labels[status] || status
}
</script>

<template>
  <section class="narrative-workbench">
    <div v-if="!plan" class="narrative-workbench__empty">尚未生成叙事规划</div>
    <template v-else>
      <div class="narrative-workbench__metrics">
        <div v-for="metric in metrics" :key="metric.label" class="narrative-workbench__metric">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
        </div>
      </div>

      <div v-if="view === 'storyline'" class="narrative-workbench__plotlines">
        <article v-for="plotline in plotlines" :key="plotline.key" class="narrative-workbench__plotline">
          <header>
            <span>{{ plotline.type }}</span>
            <h3>{{ plotline.name }}</h3>
          </header>
          <div v-if="plotline.milestones.length" class="narrative-workbench__milestones">
            <div v-for="milestone in plotline.milestones" :key="milestone.key" class="narrative-workbench__milestone">
              <span>第{{ milestone.chapterIndex ?? '?' }}章</span>
              <strong>{{ milestone.title }}</strong>
              <p v-if="milestone.summary">{{ milestone.summary }}</p>
            </div>
          </div>
          <div v-else class="narrative-workbench__subtle">暂无节点</div>
        </article>
      </div>

      <div v-else-if="view === 'chapters'" class="narrative-workbench__chapters">
        <article v-for="chapter in outlineChapters" :key="chapter.key" class="narrative-workbench__chapter">
          <header>
            <span>第{{ chapter.chapterIndex }}章</span>
            <h3>{{ chapter.title }}</h3>
            <em v-if="chapterStatus(chapter.chapterIndex)">{{ chapterStatus(chapter.chapterIndex)?.status }}</em>
          </header>
          <p>{{ chapter.summary || '暂无章节摘要' }}</p>
          <dl>
            <template v-if="chapter.purpose">
              <dt>叙事功能</dt>
              <dd>{{ chapter.purpose }}</dd>
            </template>
            <template v-if="chapter.characters.length">
              <dt>角色</dt>
              <dd>{{ chapter.characters.join(' / ') }}</dd>
            </template>
            <template v-if="chapter.scenes.length">
              <dt>场景</dt>
              <dd>{{ chapter.scenes.join(' / ') }}</dd>
            </template>
          </dl>
        </article>
      </div>

      <div v-else-if="view === 'foreshadowing'" class="narrative-workbench__foreshadowing">
        <article v-for="item in foreshadowingItems" :key="item.key" class="narrative-workbench__hint">
          <header>
            <span>{{ statusLabel(item.status) }}</span>
            <strong>第{{ item.plantedChapter ?? '?' }}章 → 第{{ item.resolvedChapter ?? '?' }}章</strong>
          </header>
          <p>{{ item.hint }}</p>
        </article>
        <div v-if="foreshadowingItems.length === 0" class="narrative-workbench__empty">暂无伏笔记录</div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.narrative-workbench {
  height: 100%;
  overflow: auto;
  padding: var(--space-4);
}

.narrative-workbench__metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.narrative-workbench__metric {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-2);
}

.narrative-workbench__metric span,
.narrative-workbench__plotline header span,
.narrative-workbench__chapter header span,
.narrative-workbench__hint header span,
.narrative-workbench__milestone span,
.narrative-workbench__subtle {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.narrative-workbench__metric strong {
  color: var(--color-text-primary);
  font-size: var(--text-lg);
}

.narrative-workbench__plotlines,
.narrative-workbench__chapters,
.narrative-workbench__foreshadowing {
  display: grid;
  gap: var(--space-3);
}

.narrative-workbench__plotline,
.narrative-workbench__chapter,
.narrative-workbench__hint {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-3);
}

.narrative-workbench__plotline header,
.narrative-workbench__chapter header,
.narrative-workbench__hint header {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.narrative-workbench__plotline h3,
.narrative-workbench__chapter h3 {
  color: var(--color-text-primary);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
}

.narrative-workbench__chapter header em {
  color: var(--color-brand);
  font-size: var(--text-xs);
  font-style: normal;
}

.narrative-workbench__chapter p,
.narrative-workbench__hint p,
.narrative-workbench__milestone p {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}

.narrative-workbench__milestones {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--space-3);
}

.narrative-workbench__milestone {
  border-left: 2px solid var(--color-border);
  padding-left: var(--space-3);
}

.narrative-workbench__milestone strong,
.narrative-workbench__hint strong {
  display: block;
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.narrative-workbench__chapter dl {
  display: grid;
  grid-template-columns: minmax(80px, auto) minmax(0, 1fr);
  gap: var(--space-2);
  margin-top: var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.narrative-workbench__chapter dd {
  overflow-wrap: anywhere;
  color: var(--color-text-primary);
}

.narrative-workbench__empty {
  padding: var(--space-8) 0;
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

@media (max-width: 760px) {
  .narrative-workbench__metrics {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
