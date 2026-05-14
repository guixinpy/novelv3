<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import type { AthenaEvolutionPlan, ChapterSummary } from '../../api/types'
import type { AthenaNarrativeView } from '../../views/athenaNavigation'

type RecordValue = Record<string, unknown>

interface StorylineMilestone {
  key: string
  chapterIndex: number | null
  title: string
  summary: string
}

interface StorylinePlotline {
  key: string
  name: string
  type: string
  milestones: StorylineMilestone[]
}

const props = defineProps<{
  plan: AthenaEvolutionPlan | null
  chapters: ChapterSummary[]
  view: AthenaNarrativeView
  loading?: boolean
}>()

const collapsedPlotlineKeys = ref<Set<string>>(new Set())
const plotlineMilestoneWindowStarts = ref<Record<string, number>>({})
const foreshadowingWindowStart = ref(0)
const chapterSearch = ref('')
const activeChapterIndex = ref<number | null>(null)
const chapterVolumeStart = ref(1)
const chapterWindowStart = ref(1)
const CHAPTERS_PER_VOLUME = 100
const CHAPTER_WINDOW_SIZE = 50
const CHAPTER_SEARCH_RESULT_LIMIT = 100
const STORYLINE_AUTO_COLLAPSE_MILESTONE_THRESHOLD = 120
const STORYLINE_MILESTONE_WINDOW_SIZE = 80
const FORESHADOWING_WINDOW_SIZE = 100
let initializedPlotlineCollapseSignature = ''

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

const plotlines = computed<StorylinePlotline[]>(() =>
  asRecords(props.plan?.storyline?.plotlines || props.plan?.outline?.plotlines)
    .map((plotline, index): StorylinePlotline => ({
      key: toText(plotline.name, `plotline-${index}`),
      name: toText(plotline.name, '未命名线索'),
      type: toText(plotline.type, '未分类'),
      milestones: asRecords(plotline.milestones)
        .map((milestone, milestoneIndex) => ({
          key: `${index}-${milestoneIndex}`,
          chapterIndex: toNumber(milestone.chapter_index ?? milestone.chapter),
          title: toText(milestone.title || milestone.summary || milestone.event, '未命名节点'),
          summary: uniqueSummary(
            toText(milestone.summary || milestone.description || milestone.event),
            toText(milestone.title || milestone.summary || milestone.event, '未命名节点'),
          ),
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

const visibleForeshadowingItems = computed(() =>
  foreshadowingItems.value.slice(foreshadowingWindowStart.value, foreshadowingWindowStart.value + FORESHADOWING_WINDOW_SIZE),
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

const filteredOutlineChapters = computed(() => {
  const query = chapterSearch.value.trim().toLocaleLowerCase()
  if (!query) return outlineChapters.value

  return outlineChapters.value.filter((chapter) => {
    const searchable = [
      `第${chapter.chapterIndex}章`,
      chapter.title,
      chapter.summary,
      chapter.purpose,
      ...chapter.characters,
      ...chapter.scenes,
    ].join(' ').toLocaleLowerCase()
    return searchable.includes(query)
  })
})

const chapterVolumes = computed(() => {
  if (!outlineChapters.value.length) return []
  const firstChapter = outlineChapters.value[0].chapterIndex ?? 1
  const lastChapter = outlineChapters.value[outlineChapters.value.length - 1].chapterIndex ?? firstChapter
  const firstVolumeStart = volumeStartForChapter(firstChapter)
  const volumes: Array<{ start: number; end: number; label: string }> = []
  for (let start = firstVolumeStart; start <= lastChapter; start += CHAPTERS_PER_VOLUME) {
    const end = Math.min(start + CHAPTERS_PER_VOLUME - 1, lastChapter)
    volumes.push({ start, end, label: `第${start}-${end}章` })
  }
  return volumes
})

const activeVolume = computed(() =>
  chapterVolumes.value.find((volume) => volume.start === chapterVolumeStart.value) ?? chapterVolumes.value[0] ?? null,
)

const visibleOutlineChapters = computed(() => {
  if (chapterSearch.value.trim()) return filteredOutlineChapters.value.slice(0, CHAPTER_SEARCH_RESULT_LIMIT)
  const volume = activeVolume.value
  if (!volume) return []
  const windowEnd = Math.min(chapterWindowStart.value + CHAPTER_WINDOW_SIZE - 1, volume.end)
  return outlineChapters.value.filter((chapter) =>
    chapter.chapterIndex !== null
    && chapter.chapterIndex >= chapterWindowStart.value
    && chapter.chapterIndex <= windowEnd,
  )
})

const jumpableOutlineChapters = computed(() => {
  if (chapterSearch.value.trim()) return visibleOutlineChapters.value
  const volume = activeVolume.value
  if (!volume) return []
  return outlineChapters.value.filter((chapter) =>
    chapter.chapterIndex !== null
    && chapter.chapterIndex >= volume.start
    && chapter.chapterIndex <= volume.end,
  )
})

const chapterWindowRangeLabel = computed(() => {
  const volume = activeVolume.value
  if (chapterSearch.value.trim()) {
    const total = filteredOutlineChapters.value.length
    const visible = visibleOutlineChapters.value.length
    return total > visible ? `搜索结果 ${visible}/${total} 章，请缩小关键词` : `搜索结果 ${visible} 章`
  }
  if (!volume) return '暂无章节'
  const end = Math.min(chapterWindowStart.value + CHAPTER_WINDOW_SIZE - 1, volume.end)
  return `当前显示第${chapterWindowStart.value}-${end}章`
})

const canPagePrevious = computed(() => Boolean(activeVolume.value && chapterWindowStart.value > activeVolume.value.start))
const canPageNext = computed(() => {
  const volume = activeVolume.value
  return Boolean(volume && chapterWindowStart.value + CHAPTER_WINDOW_SIZE <= volume.end)
})

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
  if (value === '' || value === null || value === undefined) return null
  const numberValue = Number(value)
  return Number.isFinite(numberValue) ? numberValue : null
}

function toTextArray(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value.map((item) => toText(item)).filter(Boolean)
}

function uniqueSummary(summary: string, title: string) {
  return summary && summary !== title ? summary : ''
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

function chapterStatusLabel(status: string | undefined) {
  const labels: Record<string, string> = {
    draft: '草稿',
    generated: '已生成',
    done: '已完成',
    completed: '已完成',
    pending: '待生成',
  }
  return status ? labels[status] || status : ''
}

function plotlineTypeLabel(type: string) {
  const labels: Record<string, string> = {
    main: '主线',
    sub: '支线',
    subplot: '支线',
    branch: '支线',
    parallel: '并行线',
  }
  return labels[type] || type
}

function isMainPlotlineType(type: string) {
  return type.toLocaleLowerCase() === 'main' || type === '主线'
}

function isPlotlineCollapsed(key: string) {
  return collapsedPlotlineKeys.value.has(key)
}

function togglePlotline(key: string) {
  const next = new Set(collapsedPlotlineKeys.value)
  if (next.has(key)) next.delete(key)
  else next.add(key)
  collapsedPlotlineKeys.value = next
}

function visiblePlotlineMilestones(plotline: StorylinePlotline) {
  const start = plotlineMilestoneWindowStart(plotline.key)
  return plotline.milestones.slice(start, start + STORYLINE_MILESTONE_WINDOW_SIZE)
}

function plotlineMilestoneWindowStart(key: string) {
  return plotlineMilestoneWindowStarts.value[key] ?? 0
}

function plotlineMilestoneWindowEnd(plotline: StorylinePlotline) {
  return Math.min(plotlineMilestoneWindowStart(plotline.key) + STORYLINE_MILESTONE_WINDOW_SIZE, plotline.milestones.length)
}

function plotlineMilestoneWindowLabel(plotline: StorylinePlotline) {
  const start = plotlineMilestoneWindowStart(plotline.key)
  return `当前显示 ${start + 1}-${plotlineMilestoneWindowEnd(plotline)} / ${plotline.milestones.length} 个节点`
}

function canPagePlotlineMilestonesPrevious(plotline: StorylinePlotline) {
  return plotlineMilestoneWindowStart(plotline.key) > 0
}

function canPagePlotlineMilestonesNext(plotline: StorylinePlotline) {
  return plotlineMilestoneWindowEnd(plotline) < plotline.milestones.length
}

function pagePlotlineMilestones(plotline: StorylinePlotline, direction: -1 | 1) {
  const current = plotlineMilestoneWindowStart(plotline.key)
  const maxStart = Math.max(0, plotline.milestones.length - STORYLINE_MILESTONE_WINDOW_SIZE)
  const nextStart = direction > 0
    ? Math.min(current + STORYLINE_MILESTONE_WINDOW_SIZE, maxStart)
    : Math.max(current - STORYLINE_MILESTONE_WINDOW_SIZE, 0)
  plotlineMilestoneWindowStarts.value = {
    ...plotlineMilestoneWindowStarts.value,
    [plotline.key]: nextStart,
  }
}

const foreshadowingWindowEnd = computed(() =>
  Math.min(foreshadowingWindowStart.value + FORESHADOWING_WINDOW_SIZE, foreshadowingItems.value.length),
)

const foreshadowingWindowLabel = computed(() =>
  `当前显示 ${foreshadowingWindowStart.value + 1}-${foreshadowingWindowEnd.value} / ${foreshadowingItems.value.length} 条伏笔`,
)

const canPageForeshadowingPrevious = computed(() => foreshadowingWindowStart.value > 0)
const canPageForeshadowingNext = computed(() => foreshadowingWindowEnd.value < foreshadowingItems.value.length)

function pageForeshadowing(direction: -1 | 1) {
  const maxStart = Math.max(0, foreshadowingItems.value.length - FORESHADOWING_WINDOW_SIZE)
  foreshadowingWindowStart.value = direction > 0
    ? Math.min(foreshadowingWindowStart.value + FORESHADOWING_WINDOW_SIZE, maxStart)
    : Math.max(foreshadowingWindowStart.value - FORESHADOWING_WINDOW_SIZE, 0)
}

function selectChapterJump(value: string) {
  const chapterIndex = toNumber(value)
  if (chapterIndex === null) return
  chapterSearch.value = ''
  activeChapterIndex.value = chapterIndex
  setChapterWindowFor(chapterIndex)
  void nextTick(() => {
    const target = document.querySelector(`[data-narrative-chapter-index="${chapterIndex}"]`)
    target?.scrollIntoView({ block: 'center', behavior: 'smooth' })
  })
}

function selectChapterVolume(value: string) {
  const start = toNumber(value)
  if (start === null) return
  chapterVolumeStart.value = start
  chapterWindowStart.value = start
  activeChapterIndex.value = null
}

function pageChapters(direction: -1 | 1) {
  const volume = activeVolume.value
  if (!volume) return
  chapterWindowStart.value = direction > 0
    ? Math.min(chapterWindowStart.value + CHAPTER_WINDOW_SIZE, volume.end)
    : Math.max(chapterWindowStart.value - CHAPTER_WINDOW_SIZE, volume.start)
}

function setChapterWindowFor(chapterIndex: number) {
  const volumeStart = volumeStartForChapter(chapterIndex)
  chapterVolumeStart.value = volumeStart
  chapterWindowStart.value = volumeStart + Math.floor((chapterIndex - volumeStart) / CHAPTER_WINDOW_SIZE) * CHAPTER_WINDOW_SIZE
}

function volumeStartForChapter(chapterIndex: number) {
  return Math.floor((chapterIndex - 1) / CHAPTERS_PER_VOLUME) * CHAPTERS_PER_VOLUME + 1
}

watch(outlineChapters, (chapters) => {
  const firstChapter = chapters[0]?.chapterIndex ?? 1
  const lastChapter = chapters[chapters.length - 1]?.chapterIndex ?? firstChapter
  if (chapterVolumeStart.value < volumeStartForChapter(firstChapter) || chapterVolumeStart.value > lastChapter) {
    chapterVolumeStart.value = volumeStartForChapter(firstChapter)
    chapterWindowStart.value = chapterVolumeStart.value
  }
}, { immediate: true })

watch(plotlines, (items) => {
  const signature = items
    .map((plotline) => `${plotline.key}:${plotline.type}:${plotline.milestones.length}`)
    .join('|')
  if (signature === initializedPlotlineCollapseSignature) return
  initializedPlotlineCollapseSignature = signature
  plotlineMilestoneWindowStarts.value = {}

  const totalMilestones = items.reduce((total, plotline) => total + plotline.milestones.length, 0)
  if (totalMilestones < STORYLINE_AUTO_COLLAPSE_MILESTONE_THRESHOLD) {
    collapsedPlotlineKeys.value = new Set()
    return
  }
  collapsedPlotlineKeys.value = new Set(
    items
      .filter((plotline) => !isMainPlotlineType(plotline.type))
      .map((plotline) => plotline.key),
  )
}, { immediate: true })

watch(foreshadowingItems, (items) => {
  const maxStart = Math.max(0, items.length - FORESHADOWING_WINDOW_SIZE)
  if (foreshadowingWindowStart.value > maxStart) {
    foreshadowingWindowStart.value = 0
  }
}, { immediate: true })
</script>

<template>
  <section class="narrative-workbench">
    <div v-if="loading && !plan" class="narrative-workbench__empty">正在读取叙事规划...</div>
    <div v-else-if="!plan" class="narrative-workbench__empty">尚未生成叙事规划</div>
    <template v-else>
      <div class="narrative-workbench__metrics">
        <div v-for="metric in metrics" :key="metric.label" class="narrative-workbench__metric">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
        </div>
      </div>

      <div v-if="view === 'storyline'" class="narrative-workbench__plotlines" data-testid="storyline-tree">
        <article v-for="plotline in plotlines" :key="plotline.key" class="narrative-workbench__plotline" data-testid="storyline-branch">
          <header class="narrative-workbench__branch-header">
            <button
              type="button"
              class="narrative-workbench__tree-toggle"
              data-testid="storyline-toggle"
              :aria-expanded="!isPlotlineCollapsed(plotline.key)"
              @click="togglePlotline(plotline.key)"
            >
              {{ isPlotlineCollapsed(plotline.key) ? '+' : '-' }}
            </button>
            <div>
              <span>{{ plotlineTypeLabel(plotline.type) }} · {{ plotline.milestones.length }} 个节点</span>
              <h3>{{ plotline.name }}</h3>
            </div>
          </header>
          <div
            v-if="plotline.milestones.length > STORYLINE_MILESTONE_WINDOW_SIZE && !isPlotlineCollapsed(plotline.key)"
            class="narrative-workbench__milestone-window"
          >
            <span>{{ plotlineMilestoneWindowLabel(plotline) }}</span>
            <div>
              <button
                type="button"
                data-testid="storyline-milestone-prev"
                :disabled="!canPagePlotlineMilestonesPrevious(plotline)"
                @click="pagePlotlineMilestones(plotline, -1)"
              >
                上一组
              </button>
              <button
                type="button"
                data-testid="storyline-milestone-next"
                :disabled="!canPagePlotlineMilestonesNext(plotline)"
                @click="pagePlotlineMilestones(plotline, 1)"
              >
                下一组
              </button>
            </div>
          </div>
          <ol v-if="visiblePlotlineMilestones(plotline).length && !isPlotlineCollapsed(plotline.key)" class="narrative-workbench__milestones">
            <li v-for="milestone in visiblePlotlineMilestones(plotline)" :key="milestone.key" class="narrative-workbench__milestone">
              <span>第{{ milestone.chapterIndex ?? '?' }}章</span>
              <strong>{{ milestone.title }}</strong>
              <p v-if="milestone.summary">{{ milestone.summary }}</p>
            </li>
          </ol>
          <div v-else-if="!isPlotlineCollapsed(plotline.key)" class="narrative-workbench__subtle">暂无节点</div>
        </article>
      </div>

      <div v-else-if="view === 'chapters'" class="narrative-workbench__chapters">
        <div class="narrative-workbench__chapter-tools">
          <input
            v-model="chapterSearch"
            data-testid="chapter-search"
            type="search"
            placeholder="搜索章节、摘要、角色、场景"
          >
          <select
            data-testid="chapter-volume"
            :value="activeVolume?.start ?? ''"
            @change="selectChapterVolume(($event.target as HTMLSelectElement).value)"
          >
            <option v-for="volume in chapterVolumes" :key="volume.start" :value="volume.start">
              {{ volume.label }}
            </option>
          </select>
          <select
            data-testid="chapter-jump"
            :value="activeChapterIndex ?? ''"
            @change="selectChapterJump(($event.target as HTMLSelectElement).value)"
          >
            <option value="">跳转章节</option>
            <option v-for="chapter in jumpableOutlineChapters" :key="chapter.key" :value="chapter.chapterIndex ?? ''">
              第{{ chapter.chapterIndex }}章 · {{ chapter.title }}
            </option>
          </select>
        </div>
        <div class="narrative-workbench__chapter-window" aria-label="章节窗口">
          <span>{{ chapterWindowRangeLabel }}</span>
          <div>
            <button type="button" :disabled="!canPagePrevious" @click="pageChapters(-1)">上一组</button>
            <button type="button" :disabled="!canPageNext" @click="pageChapters(1)">下一组</button>
          </div>
        </div>
        <article
          v-for="chapter in visibleOutlineChapters"
          :key="chapter.key"
          class="narrative-workbench__chapter"
          :class="{ 'narrative-workbench__chapter--active': chapter.chapterIndex === activeChapterIndex }"
          :data-testid="`chapter-${chapter.chapterIndex}`"
          :data-narrative-chapter-index="chapter.chapterIndex"
        >
          <header>
            <span>第{{ chapter.chapterIndex }}章</span>
            <h3>{{ chapter.title }}</h3>
            <em v-if="chapterStatus(chapter.chapterIndex)">{{ chapterStatusLabel(chapterStatus(chapter.chapterIndex)?.status) }}</em>
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
        <div v-if="visibleOutlineChapters.length === 0" class="narrative-workbench__empty">没有匹配的章节</div>
      </div>

      <div v-else-if="view === 'foreshadowing'" class="narrative-workbench__foreshadowing">
        <div v-if="foreshadowingItems.length > FORESHADOWING_WINDOW_SIZE" class="narrative-workbench__foreshadowing-window">
          <span>{{ foreshadowingWindowLabel }}</span>
          <div>
            <button
              type="button"
              data-testid="foreshadowing-prev"
              :disabled="!canPageForeshadowingPrevious"
              @click="pageForeshadowing(-1)"
            >
              上一组
            </button>
            <button
              type="button"
              data-testid="foreshadowing-next"
              :disabled="!canPageForeshadowingNext"
              @click="pageForeshadowing(1)"
            >
              下一组
            </button>
          </div>
        </div>
        <article v-for="item in visibleForeshadowingItems" :key="item.key" class="narrative-workbench__hint">
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

.narrative-workbench__branch-header {
  align-items: flex-start;
}

.narrative-workbench__tree-toggle {
  flex: 0 0 24px;
  width: 24px;
  height: 24px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-brand);
  font-size: var(--text-base);
  line-height: 1;
  cursor: pointer;
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
  gap: 0;
  margin-left: 12px;
  padding-left: var(--space-4);
  border-left: 2px solid var(--color-border);
  list-style: none;
}

.narrative-workbench__milestone {
  position: relative;
  padding: 0 0 var(--space-3) var(--space-4);
}

.narrative-workbench__milestone::before {
  content: '';
  position: absolute;
  top: 8px;
  left: -5px;
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-brand);
  box-shadow: 0 0 0 3px var(--color-brand-light);
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

.narrative-workbench__chapter-tools {
  position: sticky;
  top: 0;
  z-index: 1;
  display: grid;
  grid-template-columns: minmax(220px, 1fr) minmax(140px, 180px) minmax(180px, 280px);
  gap: var(--space-2);
  padding-bottom: var(--space-3);
  background: var(--color-bg-primary);
}

.narrative-workbench__chapter-tools input,
.narrative-workbench__chapter-tools select {
  min-width: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.narrative-workbench__chapter-window {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.narrative-workbench__milestone-window {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  margin: var(--space-2) 0 var(--space-3) 36px;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.narrative-workbench__foreshadowing-window {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
}

.narrative-workbench__chapter-window div {
  display: flex;
  gap: var(--space-2);
}

.narrative-workbench__milestone-window div {
  display: flex;
  gap: var(--space-2);
}

.narrative-workbench__foreshadowing-window div {
  display: flex;
  gap: var(--space-2);
}

.narrative-workbench__chapter-window button {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  cursor: pointer;
}

.narrative-workbench__milestone-window button {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  cursor: pointer;
}

.narrative-workbench__foreshadowing-window button {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  padding: var(--space-1) var(--space-2);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  cursor: pointer;
}

.narrative-workbench__chapter-window button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.narrative-workbench__milestone-window button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.narrative-workbench__foreshadowing-window button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.narrative-workbench__chapter--active {
  border-left: 3px solid var(--color-brand);
  padding-left: var(--space-3);
  background: var(--color-brand-light);
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

  .narrative-workbench__chapter-tools {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
