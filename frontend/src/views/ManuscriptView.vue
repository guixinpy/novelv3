<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { useManuscriptStore } from '../stores/manuscript'
import { useModelTraceStore } from '../stores/modelTraces'
import { useProjectWorkspaceStore } from '../stores/projectWorkspace'
import ChapterList from '../components/shared/ChapterList.vue'
import ManuscriptEditor from '../components/manuscript/ManuscriptEditor.vue'
import RevisionSummaryPanel from '../components/manuscript/RevisionSummaryPanel.vue'
import RevisionSubmitModal from '../components/manuscript/RevisionSubmitModal.vue'
import ModelTraceDrawer from '../components/modelTrace/ModelTraceDrawer.vue'

const route = useRoute()
const router = useRouter()
const project = useProjectStore()
const manuscript = useManuscriptStore()
const modelTrace = useModelTraceStore()
const projectWorkspace = useProjectWorkspaceStore()
const pid = computed(() => route.params.id as string)
const submitOpen = ref(false)
const activeTraceId = ref<string | null>(null)
const loadingMoreChapters = ref(false)
const CHAPTER_WINDOW_DEFAULT_LIMIT = 200
type WordTargetStatus = 'under' | 'within' | 'over' | 'untracked'

const targetWordRange = computed(() => {
  const targetWords = Number(project.currentProject?.target_word_count || 0)
  const targetChapters = Number(project.currentProject?.target_chapter_count || 0)
  if (!Number.isFinite(targetWords) || !Number.isFinite(targetChapters) || targetWords <= 0 || targetChapters <= 0) {
    return null
  }
  const average = Math.max(1, Math.round(targetWords / targetChapters))
  return {
    low: Math.max(1, Math.round(average * 0.85)),
    high: Math.max(1, Math.round(average * 1.15)),
  }
})

const chapterItems = computed(() => {
  const range = targetWordRange.value
  return (project.chapters || []).map((c: any) => {
    const wordCount = Number(c.word_count || 0)
    const target = chapterWordTarget(wordCount, range)
    return {
    index: c.chapter_index,
    wordCount,
    wordTargetStatus: target.status,
    wordTargetLabel: target.label,
  }
  })
})

const activeIndex = computed(() => manuscript.selectedChapterIndex)
const canSubmit = computed(() => manuscript.hasPendingFeedback && activeIndex.value !== null)
const selectedChapterTraceId = computed(() => manuscript.chapter?.last_generation_trace_id || null)
const chapterTotal = computed(() => project.chaptersTotal || chapterItems.value.length)

function hasChapterSummary(index: number) {
  return chapterItems.value.some((chapter) => chapter.index === index)
}

function chapterWordTarget(wordCount: number, range: { low: number; high: number } | null): { status: WordTargetStatus; label: string } {
  const formatted = wordCount.toLocaleString()
  if (!range) return { status: 'untracked', label: `${formatted}字` }
  if (wordCount < range.low) return { status: 'under', label: `${formatted}字 偏短` }
  if (wordCount > range.high) return { status: 'over', label: `${formatted}字 偏长` }
  return { status: 'within', label: `${formatted}字` }
}

function chapterWindowOffset(chapterIndex: number, total: number, limit: number) {
  const safeLimit = Math.max(1, limit || CHAPTER_WINDOW_DEFAULT_LIMIT)
  const safeTotal = Math.max(total || 0, chapterIndex)
  const centeredOffset = Math.max(chapterIndex - Math.ceil(safeLimit / 2), 0)
  const maxOffset = Math.max(safeTotal - safeLimit, 0)
  return Math.min(centeredOffset, maxOffset)
}

async function loadRememberedChapterWindow(projectId: string, chapterIndex: number) {
  if (hasChapterSummary(chapterIndex)) return
  if (!project.chaptersHasMore && project.chaptersTotal <= chapterItems.value.length) return
  const limit = project.chaptersLimit || CHAPTER_WINDOW_DEFAULT_LIMIT
  const offset = chapterWindowOffset(chapterIndex, project.chaptersTotal, limit)
  await project.loadChapters(projectId, true, { offset, limit })
}

async function onSelectChapter(index: number) {
  await selectChapter(pid.value, index)
}

async function selectChapter(projectId: string, index: number, force = false) {
  closeTrace()
  if (force) {
    await manuscript.loadChapter(projectId, index)
  } else {
    await manuscript.ensureChapter(projectId, index)
  }
  projectWorkspace.rememberManuscriptChapter(projectId, index)
}

async function submitRevision() {
  if (activeIndex.value === null) return
  const revision = await manuscript.submitRevision(pid.value, activeIndex.value)
  submitOpen.value = false
  await router.push({ path: `/projects/${pid.value}/hermes`, query: { revision_id: revision.id } })
}

async function loadMoreChapters() {
  if (loadingMoreChapters.value || !project.chaptersHasMore) return
  loadingMoreChapters.value = true
  try {
    await project.loadMoreChapters(pid.value)
  } finally {
    loadingMoreChapters.value = false
  }
}

function openTrace(traceId: string) {
  if (!traceId) return
  activeTraceId.value = traceId
}

function closeTrace() {
  activeTraceId.value = null
  modelTrace.closeTrace()
}

async function initialize(projectId: string) {
  await project.loadProject(projectId)
  await project.loadChapters(projectId, true)
  const rememberedIndex = projectWorkspace.lastManuscriptChapterByProject[projectId]
  if (rememberedIndex) await loadRememberedChapterWindow(projectId, rememberedIndex)
  const initialChapter =
    chapterItems.value.find((chapter) => chapter.index === rememberedIndex) ||
    chapterItems.value[0]
  if (initialChapter) await selectChapter(projectId, initialChapter.index, true)
}

onMounted(() => void initialize(pid.value))

watch(pid, (next, prev) => {
  if (!next || next === prev) return
  closeTrace()
  manuscript.reset()
  void initialize(next)
})
</script>

<template>
  <div class="manuscript-view" data-testid="workspace-manuscript">
    <Teleport to="[data-subnav-content]">
      <div class="manuscript-subnav">
        <div class="manuscript-subnav__label">章节</div>
        <ChapterList
          :chapters="chapterItems"
          :active-index="activeIndex"
          :total="chapterTotal"
          :has-more="project.chaptersHasMore"
          :loading-more="loadingMoreChapters"
          @select="onSelectChapter"
          @load-more="loadMoreChapters"
        />
        <div class="manuscript-subnav__stats">
          <span>批注 {{ manuscript.annotations.length }}</span>
          <span>修正 {{ manuscript.corrections.length }}</span>
        </div>
        <button
          v-if="selectedChapterTraceId"
          type="button"
          class="manuscript-subnav__trace"
          @click="openTrace(selectedChapterTraceId)"
        >
          生成上下文
        </button>
        <button type="button" class="manuscript-subnav__submit" :disabled="!canSubmit" @click="submitOpen = true">
          提交修订
        </button>
      </div>
    </Teleport>

    <main class="manuscript-view__main">
      <div v-if="manuscript.loading" class="manuscript-view__placeholder">加载正文中...</div>
      <div v-else-if="manuscript.error" class="manuscript-view__placeholder manuscript-view__placeholder--error">{{ manuscript.error }}</div>
      <ManuscriptEditor
        v-else-if="manuscript.chapter"
        :title="manuscript.chapter.title"
        :paragraphs="manuscript.paragraphs"
        :annotations="manuscript.annotations"
        :corrections="manuscript.corrections"
        @add-annotation="manuscript.addAnnotation"
        @add-correction="manuscript.addCorrection"
      />
      <div v-else class="manuscript-view__placeholder">请选择章节</div>
    </main>

    <RevisionSummaryPanel
      :annotations="manuscript.annotations"
      :corrections="manuscript.corrections"
      @remove-annotation="manuscript.removeAnnotation"
      @remove-correction="manuscript.removeCorrection"
    />

    <RevisionSubmitModal
      :open="submitOpen"
      :annotations="manuscript.annotations"
      :corrections="manuscript.corrections"
      :submitting="manuscript.submitting"
      @close="submitOpen = false"
      @confirm="submitRevision"
    />

    <ModelTraceDrawer
      :project-id="pid"
      :trace-id="activeTraceId"
      :open="!!activeTraceId"
      @close="closeTrace"
    />
  </div>
</template>

<style scoped>
.manuscript-view {
  display: flex;
  height: 100%;
  min-width: 0;
  background: var(--color-bg-white);
}

.manuscript-view__main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 0 var(--space-6);
}

.manuscript-view__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-tertiary);
  font-size: var(--text-lg);
}

.manuscript-view__placeholder--error {
  color: var(--color-error);
}

.manuscript-subnav__label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-tertiary);
  padding: var(--space-3) var(--space-3) var(--space-1);
}

.manuscript-subnav__stats {
  display: flex;
  justify-content: space-between;
  padding: var(--space-3);
  border-top: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.manuscript-subnav__submit {
  width: calc(100% - var(--space-6));
  margin: 0 var(--space-3) var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-brand);
  color: var(--color-bg-white);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
}

.manuscript-subnav__submit:disabled {
  background: var(--color-bg-secondary);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}

.manuscript-subnav__trace {
  display: flex;
  align-items: center;
  justify-content: center;
  width: calc(100% - var(--space-6));
  height: 32px;
  margin: var(--space-3) var(--space-3) var(--space-2);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  line-height: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.manuscript-subnav__trace:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}
</style>
