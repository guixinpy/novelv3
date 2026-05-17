<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import BaseButton from '../components/base/BaseButton.vue'
import BaseInput from '../components/base/BaseInput.vue'
import BaseModal from '../components/base/BaseModal.vue'
import BaseBadge from '../components/base/BaseBadge.vue'
import BaseTable from '../components/base/BaseTable.vue'
import ConfirmDialog from '../components/base/ConfirmDialog.vue'
import type { BaseTableColumn } from '../components/base/BaseTable.vue'
import { useProjectStore } from '../stores/project'

const router = useRouter()
const store = useProjectStore()

const showCreateDialog = ref(false)
const creating = ref(false)
const newProject = ref({ name: '', genre: '', aiModel: 'deepseek-chat', targetChapters: '', targetWords: '' })
const aiModelOptions = [
  { value: 'deepseek-chat', label: 'DeepSeek Chat' },
  { value: 'deepseek-reasoner', label: 'DeepSeek Reasoner' },
]

const deleteTarget = ref<any>(null)
const deleting = ref(false)
const updatingModelId = ref('')

const columns: BaseTableColumn[] = [
  { key: 'name', label: '项目名称' },
  { key: 'genre', label: '类型', width: '100px' },
  { key: 'current_word_count', label: '字数', width: '100px', align: 'right' },
  { key: 'ai_model', label: '模型', width: '170px' },
  { key: 'status', label: '状态', width: '100px' },
  { key: 'updated_at', label: '最后修改', width: '140px' },
  { key: 'actions', label: '操作', width: '60px', align: 'center' },
]

const projects = computed(() => store.projects)

const statusMap: Record<string, { label: string; variant: 'success' | 'warning' | 'neutral' }> = {
  writing: { label: '写作中', variant: 'success' },
  outline_generated: { label: '大纲完成', variant: 'success' },
  storyline_generated: { label: '故事线完成', variant: 'warning' },
  draft: { label: '草稿', variant: 'neutral' },
}

function getStatusInfo(status: string) {
  return statusMap[status] || { label: '进行中', variant: 'neutral' as const }
}

function formatRelativeTime(dateStr: string) {
  if (!dateStr) return ''
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/i.test(dateStr) ? dateStr : `${dateStr}Z`
  const date = new Date(normalized)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}小时前`
  const diffDay = Math.floor(diffHr / 24)
  return `${diffDay}天前`
}

onMounted(() => store.loadProjects())

function onRowClick(row: Record<string, unknown>) {
  router.push(`/projects/${row.id}/hermes`)
}

function requestDelete(project: any, event: Event) {
  event.stopPropagation()
  deleteTarget.value = project
}

async function updateProjectModel(project: any, event: Event) {
  event.stopPropagation()
  const aiModel = (event.target as HTMLSelectElement).value
  const projectId = String(project.id || '')
  if (!projectId || aiModel === project.ai_model) return
  updatingModelId.value = projectId
  try {
    await store.updateProjectModel(projectId, aiModel)
  } finally {
    updatingModelId.value = ''
  }
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await store.deleteProject(deleteTarget.value.id)
  } finally {
    deleting.value = false
    deleteTarget.value = null
  }
}

async function createProject() {
  const name = newProject.value.name.trim()
  if (!name) return
  const targetChapterCount = Number(newProject.value.targetChapters)
  const targetWordCount = Number(newProject.value.targetWords)
  creating.value = true
  try {
    await store.createProject({
      name,
      genre: newProject.value.genre.trim() || undefined,
      ai_model: newProject.value.aiModel,
      ...(Number.isFinite(targetChapterCount) && targetChapterCount > 0 ? { target_chapter_count: targetChapterCount } : {}),
      ...(Number.isFinite(targetWordCount) && targetWordCount > 0 ? { target_word_count: targetWordCount } : {}),
    })
    showCreateDialog.value = false
    newProject.value = { name: '', genre: '', aiModel: 'deepseek-chat', targetChapters: '', targetWords: '' }
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="project-list-view">
    <div class="project-list-view__header">
      <h1 class="project-list-view__title">项目</h1>
      <BaseButton data-testid="project-create-button" variant="primary" size="sm" @click="showCreateDialog = true">
        新建项目
      </BaseButton>
    </div>

    <div v-if="projects.length === 0" class="project-list-view__empty">
      <p class="project-list-view__empty-text">还没有项目</p>
      <BaseButton data-testid="project-create-button" variant="primary" size="sm" @click="showCreateDialog = true">
        新建项目
      </BaseButton>
    </div>

    <BaseTable
      v-else
      :columns="columns"
      :data="projects"
      row-key="id"
      clickable
      @row-click="onRowClick"
    >
      <template #cell-name="{ value }">
        <span class="project-list-view__name">{{ value }}</span>
      </template>
      <template #cell-current_word_count="{ value }">
        {{ Number(value || 0).toLocaleString() }}
      </template>
      <template #cell-ai_model="{ row, value }">
        <select
          :data-testid="`project-row-ai-model-${row.id}`"
          class="project-list-view__row-select"
          :value="String(value || 'deepseek-chat')"
          :disabled="updatingModelId === String(row.id)"
          @click.stop
          @change="updateProjectModel(row, $event)"
        >
          <option v-for="option in aiModelOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </template>
      <template #cell-status="{ value }">
        <BaseBadge :variant="getStatusInfo(String(value)).variant" size="sm">
          {{ getStatusInfo(String(value)).label }}
        </BaseBadge>
      </template>
      <template #cell-updated_at="{ value }">
        {{ formatRelativeTime(String(value || '')) }}
      </template>
      <template #cell-actions="{ row }">
        <button
          class="project-list-view__delete"
          title="删除"
          @click="requestDelete(row, $event)"
        >
          🗑
        </button>
      </template>
    </BaseTable>

    <!-- Create dialog -->
    <BaseModal
      :open="showCreateDialog"
      title="新建项目"
      width="420px"
      test-id="project-create-modal"
      @close="showCreateDialog = false"
    >
      <div class="project-list-view__form">
        <BaseInput
          data-testid="project-name-input"
          v-model="newProject.name"
          label="项目名称"
          placeholder="输入项目名称"
        />
        <BaseInput
          v-model="newProject.genre"
          label="题材类型"
          placeholder="如：科幻、悬疑、言情"
        />
        <label class="project-list-view__field">
          <span class="project-list-view__field-label">生成模型</span>
          <select
            v-model="newProject.aiModel"
            data-testid="project-ai-model-select"
            class="project-list-view__select"
          >
            <option v-for="option in aiModelOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <BaseInput
          v-model="newProject.targetChapters"
          label="目标章节数"
          placeholder="如：20"
        />
        <BaseInput
          v-model="newProject.targetWords"
          label="目标字数"
          placeholder="如：200000"
        />
      </div>
      <template #footer>
        <BaseButton variant="ghost" size="sm" @click="showCreateDialog = false">
          取消
        </BaseButton>
        <BaseButton
          data-testid="project-create-submit"
          variant="primary"
          size="sm"
          :loading="creating"
          :disabled="!newProject.name.trim()"
          @click="createProject"
        >
          创建
        </BaseButton>
      </template>
    </BaseModal>

    <!-- Delete confirm -->
    <ConfirmDialog
      :open="!!deleteTarget"
      :title="`删除「${deleteTarget?.name || ''}」？`"
      message="删除后所有数据将永久丢失，无法恢复。"
      confirm-text="确认删除"
      cancel-text="取消"
      variant="danger"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />
  </div>
</template>

<style scoped>
.project-list-view {
  max-width: 960px;
  margin: 0 auto;
}

.project-list-view__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-6);
}

.project-list-view__title {
  font-size: var(--text-xl);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.project-list-view__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) 0;
  gap: var(--space-4);
}

.project-list-view__empty-text {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.project-list-view__name {
  font-weight: var(--font-medium);
}

.project-list-view__delete {
  opacity: 0.5;
  transition: opacity var(--transition-fast);
  font-size: var(--text-sm);
}

.project-list-view__delete:hover {
  opacity: 1;
}

.project-list-view__row-select {
  width: 150px;
  min-height: 30px;
  padding: 0 var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.project-list-view__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.project-list-view__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.project-list-view__field-label {
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.project-list-view__select {
  width: 100%;
  min-height: 38px;
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font: inherit;
}
</style>
