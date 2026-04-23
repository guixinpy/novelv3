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
const newProject = ref({ name: '', genre: '', targetChapters: '', targetWords: '' })

const deleteTarget = ref<any>(null)
const deleting = ref(false)

const columns: BaseTableColumn[] = [
  { key: 'name', label: '项目名称' },
  { key: 'genre', label: '类型', width: '100px' },
  { key: 'current_word_count', label: '字数', width: '100px', align: 'right' },
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
  const date = new Date(dateStr)
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
  creating.value = true
  try {
    await store.createProject({
      name,
      genre: newProject.value.genre.trim() || undefined,
    })
    showCreateDialog.value = false
    newProject.value = { name: '', genre: '', targetChapters: '', targetWords: '' }
  } finally {
    creating.value = false
  }
}
</script>

<template>
  <div class="project-list-view">
    <div class="project-list-view__header">
      <h1 class="project-list-view__title">项目</h1>
      <BaseButton variant="primary" size="sm" @click="showCreateDialog = true">
        新建项目
      </BaseButton>
    </div>

    <div v-if="projects.length === 0" class="project-list-view__empty">
      <p class="project-list-view__empty-text">还没有项目</p>
      <BaseButton variant="primary" size="sm" @click="showCreateDialog = true">
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
      @close="showCreateDialog = false"
    >
      <div class="project-list-view__form">
        <BaseInput
          v-model="newProject.name"
          label="项目名称"
          placeholder="输入项目名称"
        />
        <BaseInput
          v-model="newProject.genre"
          label="题材类型"
          placeholder="如：科幻、悬疑、言情"
        />
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

.project-list-view__form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}
</style>
