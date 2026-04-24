<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProjectStore } from '../stores/project'
import { useManuscriptStore } from '../stores/manuscript'
import ChapterList from '../components/shared/ChapterList.vue'
import ManuscriptEditor from '../components/manuscript/ManuscriptEditor.vue'
import RevisionSummaryPanel from '../components/manuscript/RevisionSummaryPanel.vue'
import RevisionSubmitModal from '../components/manuscript/RevisionSubmitModal.vue'

const route = useRoute()
const router = useRouter()
const project = useProjectStore()
const manuscript = useManuscriptStore()
const pid = computed(() => route.params.id as string)
const submitOpen = ref(false)

const chapterItems = computed(() =>
  (project.chapters || []).map((c: any) => ({
    index: c.chapter_index,
    wordCount: c.word_count || 0,
  })),
)

const activeIndex = computed(() => manuscript.selectedChapterIndex)
const canSubmit = computed(() => manuscript.hasPendingFeedback && activeIndex.value !== null)

async function onSelectChapter(index: number) {
  await manuscript.loadChapter(pid.value, index)
}

async function submitRevision() {
  if (activeIndex.value === null) return
  const revision = await manuscript.submitRevision(pid.value, activeIndex.value)
  submitOpen.value = false
  await router.push({ path: `/projects/${pid.value}/hermes`, query: { revision_id: revision.id } })
}

onMounted(async () => {
  await project.loadProject(pid.value)
  await project.loadChapters(pid.value)
  const firstChapter = chapterItems.value[0]
  if (firstChapter) await onSelectChapter(firstChapter.index)
})

watch(pid, () => {
  manuscript.reset()
})
</script>

<template>
  <div class="manuscript-view">
    <Teleport to="[data-subnav-content]">
      <div class="manuscript-subnav">
        <div class="manuscript-subnav__label">章节</div>
        <ChapterList :chapters="chapterItems" :active-index="activeIndex" @select="onSelectChapter" />
        <div class="manuscript-subnav__stats">
          <span>批注 {{ manuscript.annotations.length }}</span>
          <span>修正 {{ manuscript.corrections.length }}</span>
        </div>
        <button class="manuscript-subnav__submit" :disabled="!canSubmit" @click="submitOpen = true">
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
</style>
