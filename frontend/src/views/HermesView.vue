<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import type { ChatResponse, RefreshTarget, ResolveActionResponse, WorkspacePanel } from '../api/types'
import ProjectDashboard from '../components/shared/ProjectDashboard.vue'
import ExportModal from '../components/shared/ExportModal.vue'
import VersionsModal from '../components/shared/VersionsModal.vue'
import ChatMessageList from '../components/chat/ChatMessageList.vue'
import ChatInput from '../components/chat/ChatInput.vue'
import { parseSlashCommand } from '../components/workspace/chatCommands'
import {
  getActionLabel,
  getActionRefreshTargets,
  getPanelRefreshTargets,
  getVersionRefreshTarget,
  getVersionTypeLabel,
  isFinishedActionStatus,
  normalizeActionStatus,
} from '../components/workspace/workspaceMeta'
import {
  beginHydration,
  createHydrationTracker,
  isActiveHydrationSnapshot,
  markHydratedTarget,
  markHydratedTargets,
  type HydrationSnapshot,
} from './projectDetailHydration'
import { useChatStore } from '../stores/chat'
import { useProjectStore } from '../stores/project'
import { useWorkspaceStore } from '../stores/workspace'

type UiAwareResponse =
  | Pick<ChatResponse, 'ui_hint' | 'refresh_targets'>
  | Pick<ResolveActionResponse, 'ui_hint' | 'refresh_targets'>

const route = useRoute()
const router = useRouter()
const project = useProjectStore()
const chat = useChatStore()
const workspace = useWorkspaceStore()
const pid = computed(() => route.params.id as string)
const ready = ref(false)
const hydrationTracker = createHydrationTracker()
const hydratedTargets = hydrationTracker.targets

// Modal state
const showExportModal = ref(false)
const showVersionsModal = ref(false)
const handledRevisionIds = ref(new Set<string>())

// Project stats
const totalWords = computed(() => {
  return (project.chapters || []).reduce((sum: number, c: any) => sum + (c.word_count || 0), 0)
})

// Action fingerprint watcher (from ProjectDetail.vue)
const latestActionFingerprint = computed(() => {
  const latest = chat.messages[chat.messages.length - 1]?.action_result as
    | { type?: unknown; status?: unknown }
    | undefined
  if (!latest) return ''
  return `${chat.messages.length}:${String(latest.type)}:${String(latest.status)}`
})

const latestActionResult = computed(() => {
  for (let index = chat.messages.length - 1; index >= 0; index -= 1) {
    const actionResult = chat.messages[index]?.action_result as { type?: unknown; status?: unknown } | undefined
    if (typeof actionResult?.type === 'string' || typeof actionResult?.status === 'string') return actionResult
  }
  return null
})

const latestActionLabel = computed(() => {
  const actionType = typeof latestActionResult.value?.type === 'string' ? latestActionResult.value.type : ''
  return actionType ? getActionLabel(actionType) : ''
})

const latestActionStatus = computed(() => {
  const status = latestActionResult.value?.status
  return typeof status === 'string' ? status : null
})

const suggestedNextStep = computed(() => chat.diagnosis?.suggested_next_step || null)

onMounted(async () => {
  await initialize(pid.value)
})

watch(pid, (nextPid, prevPid) => {
  if (!nextPid || nextPid === prevPid) return
  void initialize(nextPid)
})

watch(
  () => workspace.panel,
  (panel, previousPanel) => {
    if (!ready.value || panel === previousPanel) return
    void ensurePanelData(panel)
  },
)

watch(latestActionFingerprint, async (fingerprint) => {
  if (!fingerprint) return
  const latest = chat.messages[chat.messages.length - 1]?.action_result as
    | { type?: unknown; status?: unknown }
    | undefined
  const status = normalizeActionStatus(latest?.status)
  const actionType = typeof latest?.type === 'string' ? latest.type : ''
  if (!isFinishedActionStatus(status)) return
  workspace.settleUiAction(status)
  await refreshProjectTargets(getActionRefreshTargets(actionType, status))
})

async function initialize(projectId: string) {
  ready.value = false
  const snapshot = beginHydration(hydrationTracker, projectId)
  project.resetProjectScopedState(projectId)
  workspace.reset()
  await Promise.all([
    chat.init(projectId),
    project.loadProject(projectId),
  ])
  if (!markHydratedTarget(hydrationTracker, snapshot, 'project')) return
  await Promise.all([
    ensurePanelData(workspace.panel, projectId, false, snapshot),
    project.loadSetup(projectId).catch(() => {}),
    project.loadStoryline(projectId).catch(() => {}),
    project.loadOutline(projectId).catch(() => {}),
    project.loadChapters(projectId).catch(() => {}),
  ])
  if (!isActiveHydrationSnapshot(hydrationTracker, snapshot)) return
  ready.value = true
  await handleRevisionQuery(projectId)
}

async function handleRevisionQuery(projectId = pid.value) {
  const revisionId = typeof route.query.revision_id === 'string' ? route.query.revision_id : ''
  if (!revisionId || handledRevisionIds.value.has(revisionId)) return
  handledRevisionIds.value.add(revisionId)
  const { revision_id: _revisionId, ...restQuery } = route.query
  void router.replace({ query: restQuery })
  workspace.applyUserPanel('content', '你提交了章节修订，Hermes 正在重新生成')
  const chapter = await chat.regenerateRevision(revisionId)
  if (!chapter) return
  await refreshProjectTargets(['content', 'versions'], currentHydrationSnapshot(projectId))
  await project.loadChapter(projectId, chapter.chapter_index)
}

function currentHydrationSnapshot(projectId = pid.value): HydrationSnapshot {
  return { projectId, version: hydrationTracker.version }
}

function shouldIgnoreMissingTarget(target: RefreshTarget, error: unknown) {
  if (target === 'project') return false
  const message = error instanceof Error ? error.message : String(error || '')
  return /not found/i.test(message)
}

async function loadTarget(projectId: string, target: RefreshTarget) {
  try {
    switch (target) {
      case 'project': await project.loadProject(projectId); break
      case 'setup': await project.loadSetup(projectId); break
      case 'storyline': await project.loadStoryline(projectId); break
      case 'outline': await project.loadOutline(projectId); break
      case 'content': await project.loadChapters(projectId); break
      case 'topology': await project.loadTopology(projectId); break
      case 'versions': await project.loadVersions(projectId, project.versionsNodeType); break
      case 'preferences': await project.loadPreferences(projectId); break
    }
  } catch (error) {
    if (shouldIgnoreMissingTarget(target, error)) return
    throw error
  }
}

async function ensurePanelData(
  panel: WorkspacePanel,
  projectId = pid.value,
  force = false,
  snapshot = currentHydrationSnapshot(projectId),
) {
  for (const target of getPanelRefreshTargets(panel)) {
    if (!isActiveHydrationSnapshot(hydrationTracker, snapshot)) return
    if (!force && hydratedTargets.has(target)) continue
    await loadTarget(projectId, target)
    markHydratedTarget(hydrationTracker, snapshot, target)
  }
}

async function refreshProjectTargets(targets: RefreshTarget[], snapshot = currentHydrationSnapshot()) {
  if (!targets.length) return []
  const successTargets = await project.refreshTargets(pid.value, targets)
  if (!isActiveHydrationSnapshot(hydrationTracker, snapshot)) return []
  markHydratedTargets(hydrationTracker, snapshot, successTargets)
  if (successTargets.includes('content') && project.chapter?.chapter_index != null) {
    await project.loadChapter(pid.value, project.chapter.chapter_index)
  }
  return successTargets
}

async function handleResponse(res: UiAwareResponse | null) {
  if (!res) return
  workspace.applyUiHint(res.ui_hint)
  await refreshProjectTargets(res.refresh_targets)
}

async function onSend(text: string) {
  const parsed = parseSlashCommand(text)
  if (chat.pendingAction && !(parsed.kind === 'command' && parsed.name === 'clear')) return
  workspace.applyUserPanel(workspace.panel, '你发送了一条消息')
  const res = parsed.kind === 'command'
    ? await chat.sendCommand(parsed.name, parsed.args, parsed.rawInput)
    : await chat.sendText(parsed.text)
  await handleResponse(res)
}

async function onDecide(decision: string, comment?: string) {
  const reason = decision === 'confirm'
    ? '你确认执行当前动作'
    : decision === 'cancel'
      ? '你取消了当前动作'
      : `你提交了修改意见${comment?.trim() ? `：${comment.trim()}` : ''}`
  const decisionPanel = workspace.mode === 'locked' && workspace.lockedPanel
    ? workspace.lockedPanel
    : workspace.panel
  workspace.applyUserPanel(decisionPanel, reason)
  const res = await chat.resolveAction(decision as 'confirm' | 'cancel' | 'revise', comment)
  await handleResponse(res)
}

async function onExport(format: string) {
  showExportModal.value = false
  await project.exportProject(pid.value, format)
}

async function onDashboardTool(tool: 'manuscript' | 'versions' | 'export') {
  if (tool === 'manuscript') {
    await router.push(`/projects/${pid.value}/manuscript`)
    return
  }
  if (tool === 'versions') {
    openVersionsModal()
    return
  }
  showExportModal.value = true
}

async function onFilterVersions(type: string) {
  const snapshot = currentHydrationSnapshot()
  const reason = type
    ? `你筛选了${getVersionTypeLabel(type)}版本`
    : '你查看全部版本记录'
  workspace.applyUserPanel('versions', reason)
  await project.loadVersions(pid.value, type || undefined)
  markHydratedTarget(hydrationTracker, snapshot, 'versions')
}

async function onRollback(versionId: string) {
  workspace.applyUserPanel('versions', '你发起了版本回滚')
  const version = project.versions.find((item: any) => item.id === versionId)
  await project.rollbackVersion(pid.value, versionId)
  const targets: RefreshTarget[] = ['versions']
  const relatedTarget = getVersionRefreshTarget(version?.node_type)
  if (relatedTarget) targets.push(relatedTarget)
  await refreshProjectTargets(targets)
}

async function onDeleteVersion(versionId: string) {
  workspace.applyUserPanel('versions', '你删除了一条版本记录')
  await api.deleteVersion(pid.value, versionId)
  await refreshProjectTargets(['versions'])
}

function openVersionsModal() {
  showVersionsModal.value = true
  void refreshProjectTargets(['versions'])
}
</script>

<template>
  <div v-if="project.currentProject && ready" class="hermes-view">
    <!-- Sub-nav content: rendered into AppShell SubNav slot via teleport -->
    <Teleport to="[data-subnav-content]">
      <div class="hermes-subnav">
        <ProjectDashboard
          :setup="project.setup"
          :storyline="project.storyline"
          :outline="project.outline"
          :chapters="project.chapters || []"
          :total-words="totalWords"
          :pending-action="chat.pendingAction"
          :ai-loading="chat.loading"
          :latest-action-label="latestActionLabel"
          :latest-action-status="latestActionStatus"
          :suggested-next-step="suggestedNextStep"
          @tool="onDashboardTool"
        />
      </div>
    </Teleport>

    <!-- Main content: Chat interface -->
    <div class="hermes-view__chat">
      <ChatMessageList
        :messages="chat.messages"
        :loading="chat.loading"
        @decide="onDecide"
      />
      <ChatInput
        :loading="chat.loading"
        :disabled="false"
        :has-pending-action="!!chat.pendingAction"
        @send="onSend"
      />
    </div>

    <!-- Modals -->
    <ExportModal
      :open="showExportModal"
      @close="showExportModal = false"
      @export="onExport"
    />
    <VersionsModal
      :open="showVersionsModal"
      :versions="project.versions"
      :project-id="pid"
      @close="showVersionsModal = false"
      @filter="onFilterVersions"
      @rollback="onRollback"
      @delete-version="onDeleteVersion"
    />
  </div>
  <div v-else class="hermes-view__loading">
    加载项目工作区...
  </div>
</template>

<style scoped>
.hermes-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  /* Override content-area padding for full-bleed chat */
  margin: calc(-1 * var(--content-padding));
}

.hermes-view__chat {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.hermes-view__loading {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

.hermes-subnav {
  display: flex;
  flex-direction: column;
}
</style>
