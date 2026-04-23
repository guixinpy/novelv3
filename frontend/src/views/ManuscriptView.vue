<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useProjectStore } from '../stores/project'
import ChapterList from '../components/shared/ChapterList.vue'

const route = useRoute()
const project = useProjectStore()
const pid = computed(() => route.params.id as string)

const chapterItems = computed(() =>
  (project.chapters || []).map((c: any) => ({
    index: c.chapter_index,
    wordCount: c.word_count || 0,
  })),
)

function onSelectChapter(_index: number) {
  // Placeholder — manuscript editor not yet implemented
}

onMounted(async () => {
  await project.loadProject(pid.value)
  await project.loadChapters(pid.value)
})
</script>

<template>
  <div class="manuscript-view">
    <!-- Sub-nav content -->
    <Teleport to="[data-subnav-content]">
      <div class="manuscript-subnav">
        <div class="manuscript-subnav__label">章节</div>
        <ChapterList
          :chapters="chapterItems"
          :active-index="null"
          @select="onSelectChapter"
        />
      </div>
    </Teleport>

    <!-- Main content: placeholder -->
    <div class="manuscript-view__placeholder">
      正文编辑器即将推出
    </div>
  </div>
</template>

<style scoped>
.manuscript-view {
  height: 100%;
}

.manuscript-view__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-tertiary);
  font-size: var(--text-lg);
}

.manuscript-subnav__label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-tertiary);
  padding: var(--space-3) var(--space-3) var(--space-1);
}
</style>
