<template>
  <div class="project-list-view">
    <ProjectMatrixHero
      :summary="heroSummary"
      :total-projects="summary.totalProjects"
      :total-words="summary.totalWords"
      :focus-project-name="focusProject?.name"
      :create-project="create"
      :submitting="creating"
    />

    <div class="project-list-view__grid">
      <section class="project-list-view__main">
        <div v-if="projects.length === 0" class="project-list-view__empty">
          <p class="project-list-view__empty-title">矩阵还是空的。</p>
          <p class="project-list-view__empty-copy">
            先创建一个项目，把设定、故事线和大纲放进同一条创作链路里。
          </p>
        </div>

        <div v-else class="project-list-view__matrix">
          <ProjectCard
            v-for="project in projects"
            :key="project.id"
            :project="project"
            :deleting="activeDeletingProjectId === project.id"
            @request-delete="requestProjectDelete(project)"
          />
        </div>
      </section>

      <ProjectFocusRail
        :summary="summary"
        :focus-project="focusProject"
        :focus-insight="focusInsight"
      />
    </div>

    <ConfirmDialog
      :show="isDeleteDialogOpen"
      eyebrow="删除项目"
      :title="deleteDialogTitle"
      :description="deleteDialogDescription"
      confirm-text="确认删除"
      cancel-text="再想想"
      pending-text="删除中..."
      :confirming="activeDeletingProjectId !== null"
      :error-message="deleteDialogErrorMessage"
      @close="deleteDialog.close"
      @confirm="confirmProjectDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import ProjectCard from '../components/ProjectCard.vue'
import ProjectFocusRail from '../components/list/ProjectFocusRail.vue'
import ProjectMatrixHero from '../components/list/ProjectMatrixHero.vue'
import {
  buildProjectInsight,
  buildProjectPortfolioSummary,
  pickFocusProject,
  type ProjectListProject,
} from '../components/list/projectListMeta'
import { useProjectStore } from '../stores/project'
import { createProjectDeleteDialog } from './projectListDeleteDialog'

const store = useProjectStore()
const creating = ref(false)
const deleteDialog = createProjectDeleteDialog()

const projects = computed<ProjectListProject[]>(() => store.projects)
const summary = computed(() => buildProjectPortfolioSummary(projects.value))
const focusProject = computed(() => pickFocusProject(projects.value))
const focusInsight = computed(() => (
  focusProject.value ? buildProjectInsight(focusProject.value) : undefined
))

const heroSummary = computed(() => {
  if (!focusProject.value || !focusInsight.value) {
    return '这里不做项目仓库清单，只帮你决定下一步要不要开工。先新建一个项目，系统会从设定开始把链路铺好。'
  }

  return `当前共 ${summary.value.totalProjects} 个项目，${summary.value.pendingLabel}。最值得继续的是「${focusProject.value.name}」，建议下一步：${focusInsight.value.nextStepLabel}。`
})

const activeDeletingProjectId = computed(() => deleteDialog.deletingProjectId.value)
const isDeleteDialogOpen = computed(() => deleteDialog.isOpen.value)
const deleteDialogErrorMessage = computed(() => deleteDialog.errorMessage.value)

const deleteDialogTitle = computed(() => {
  const name = deleteDialog.targetProject.value?.name
  return name ? `删除「${name}」？` : '删除这个项目？'
})

const deleteDialogDescription = computed(() => {
  const project = deleteDialog.targetProject.value
  if (!project) return ''
  const phase = buildProjectInsight(project).phaseLabel
  return `这会永久清空「${project.name}」的设定、大纲、对话、版本和后台任务记录。当前处于${phase}，删除后无法恢复。`
})

onMounted(() => store.loadProjects())

async function create(payload: { name: string; genre: string }) {
  creating.value = true
  try {
    await store.createProject(payload)
    return true
  } catch {
    return false
  } finally {
    creating.value = false
  }
}

function requestProjectDelete(project: ProjectListProject) {
  deleteDialog.open(project)
}

async function confirmProjectDelete() {
  await deleteDialog.confirm((projectId) => store.deleteProject(projectId))
}
</script>

<style scoped>
.project-list-view {
  display: grid;
  gap: 1.5rem;
}

.project-list-view__grid {
  display: grid;
  gap: 1.5rem;
}

.project-list-view__main {
  min-width: 0;
}

.project-list-view__matrix {
  display: grid;
  gap: 1rem;
}

.project-list-view__empty {
  border: 1px dashed rgba(111, 69, 31, 0.24);
  border-radius: 1.8rem;
  padding: 2.25rem 1.5rem;
  background: rgba(252, 248, 239, 0.7);
  text-align: center;
}

.project-list-view__empty-title {
  color: var(--ink-strong);
  font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
  font-size: 1.8rem;
  line-height: 1.1;
}

.project-list-view__empty-copy {
  margin: 0.75rem auto 0;
  max-width: 28rem;
  color: var(--ink-muted);
  font-size: 0.96rem;
  line-height: 1.7;
}

@media (min-width: 900px) {
  .project-list-view__matrix {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (min-width: 1280px) {
  .project-list-view__grid {
    grid-template-columns: minmax(0, 1fr) 21rem;
    align-items: start;
  }
}
</style>
