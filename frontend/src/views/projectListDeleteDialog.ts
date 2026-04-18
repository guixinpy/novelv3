import { computed, ref } from 'vue'
import type { ProjectListProject } from '../components/list/projectListMeta'

type DeleteHandler = (projectId: string) => Promise<void>

export function createProjectDeleteDialog() {
  const targetProject = ref<ProjectListProject | null>(null)
  const deletingProjectId = ref<string | null>(null)
  const errorMessage = ref('')
  const isOpen = computed(() => targetProject.value !== null)

  function open(project: ProjectListProject) {
    targetProject.value = project
    errorMessage.value = ''
  }

  function close() {
    if (deletingProjectId.value) return
    targetProject.value = null
    errorMessage.value = ''
  }

  async function confirm(removeProject: DeleteHandler) {
    if (!targetProject.value || deletingProjectId.value) return false

    const projectId = targetProject.value.id
    deletingProjectId.value = projectId
    errorMessage.value = ''

    try {
      await removeProject(projectId)
      targetProject.value = null
      return true
    } catch {
      errorMessage.value = '删除失败，请稍后重试。'
      return false
    } finally {
      deletingProjectId.value = null
    }
  }

  return {
    targetProject,
    deletingProjectId,
    errorMessage,
    isOpen,
    open,
    close,
    confirm,
  }
}
