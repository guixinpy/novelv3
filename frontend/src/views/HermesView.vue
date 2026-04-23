<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import type { ChatResponse, RefreshTarget, ResolveActionResponse, WorkspacePanel } from '../api/types'
import PhaseProgress from '../components/shared/PhaseProgress.vue'
import type { PhaseItem } from '../components/shared/PhaseProgress.vue'
import ChapterList from '../components/shared/ChapterList.vue'
import ExportModal from '../components/shared/ExportModal.vue'
import VersionsModal from '../components/shared/VersionsModal.vue'
import ChatMessageList from '../components/chat/ChatMessageList.vue'
import ChatInput from '../components/chat/ChatInput.vue'
import BaseButton from '../components/base/BaseButton.vue'
import { parseSlashCommand } from '../components/workspace/chatCommands'
import {
  getActionLabel,
  getActionPanel,
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

// Phase progress
const currentPhase = computed(() => {
  const p = project.currentProject
  if (!p) return 'setup'
  if (p.status === 'writing') return 'writing'
  if (p.status === 'outline_generated') return 'writing'
  if (p.status === 'storyline_generated') return 'outline'
  const phase = String(p.current_phase || '')
  if (phase === 'outline') return 'outline'
  if (phase === 'storyline') return 'storyline'
  return 'setup'
})

const phases = computed<PhaseItem[]>(() => {
  const phase = currentPhase.value
  const phaseOrder = ['setup', 'storyline', 'outline', 'writing']
  const currentIdx = phaseOrder.indexOf(phase)
  return [
    { key: 'setup', label: '设定', status: currentIdx > 0 ? 'done' : currentIdx === 0 ? 'current' : 'pending' },
    { key: 'storyline', label: '故事线', status: currentIdx > 1 ? 'done' : currentIdx === 1 ? 'current' : 'pending' },
    { key: 'outline', label: '大纲', status: currentIdx > 2 ? 'done' : currentIdx === 2 ? 'current' : 'pending' },
    { key: 'writing', label: '正文', status: currentIdx >= 3 ? 'current' : 'pending' },
  ] as PhaseItem[]
})

// Chapters
const chapterItems = computed(() =>
  (project.chapters || []).map((c: any) => ({
    index: c.chapter_index,
    wordCount: c.word_count || 0,
  })),
)

const activeChapterIndex = computed(() => project.chapter?.chapter_index ?? null)

// Action fingerprint watcher (from ProjectDetail.vue)
const latestActionFingerprint = computed(() => {
  const latest = chat.messages[chat.messages.length - 1]?.action_result as
    | { type?: unknown; status?: unknown }
    | undefined
  if (!latest) return ''
  return `${chat.messages.length}:${String(latest.type)}:${String(latest.status)}`
})

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
  await ensurePanelData(workspace.panel, projectId, false, snapshot)
  if (!isActiveHydrationSnapshot(hydrationTracker, snapshot)) return
  ready.value = true
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

async function loadChapter(index: number) {
  const snapshot = currentHydrationSnapshot()
  workspace.applyUserPanel('content', `你刚点了第 ${index} 章`)
  await project.loadChapter(pid.value, index)
  markHydratedTarget(hydrationTracker, snapshot, 'content')
}

async function onExport(format: string) {
  showExportModal.value = false
  await project.exportProject(pid.value, format)
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
        <div class="hermes-subnav__section-label">创作阶段</div>
        <PhaseProgress :phases="phases" />
        <div class="hermes-subnav__divider" />
        <div class="hermes-subnav__section-label">章节</div>
        <ChapterList
          :chapters="chapterItems"
          :active-index="activeChapterIndex"
          @select="loadChapter"
        />
        <div class="hermes-subnav__divider" />
        <div class="hermes-subnav__actions">
          <BaseButton variant="ghost" size="sm" @click="showExportModal = true">
            导出
          </BaseButton>
          <BaseButton variant="ghost" size="sm" @click="openVersionsModal">
            版本历史
          </BaseButton>
        </div>
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

/* Sub-nav styles */
.hermes-subnav {
  display: flex;
  flex-direction: column;
}

.hermes-subnav__section-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--color-text-tertiary);
  padding: var(--space-3) var(--space-3) var(--space-1);
}

.hermes-subnav__divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-2) 0;
}

.hermes-subnav__actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
}
</style>
