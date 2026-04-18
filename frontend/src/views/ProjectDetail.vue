<template>
  <div v-if="project.currentProject && ready">
    <ProjectWorkspaceShell>
      <template #chat>
        <ChatWorkspace
          :project="project.currentProject"
          :tabs="tabs"
          :panel="workspace.panel"
          :mode="workspace.mode"
          :source="workspace.source"
          :reason="workspace.reason"
          :messages="chat.messages"
          :diagnosis="chat.diagnosis"
          :pending-action="chat.pendingAction"
          :loading="chat.loading"
          @send="send"
          @action="onQuickAction"
          @decide="onDecide"
        />
      </template>
      <template #inspector>
        <InspectorPanel
          :project="project.currentProject"
          :project-id="pid"
          :tabs="tabs"
          :panel="workspace.panel"
          :mode="workspace.mode"
          :locked-panel="workspace.lockedPanel"
          :source="workspace.source"
          :reason="workspace.reason"
          :diagnosis="chat.diagnosis"
          :setup="project.setup"
          :storyline="project.storyline"
          :outline="project.outline"
          :chapters="project.chapters"
          :selected-chapter="project.chapter"
          :topology="project.topology"
          :versions="project.versions"
          @select-panel="onSelectPanel"
          @toggle-lock="workspace.toggleLock()"
          @export="onExport"
          @select-chapter="loadChapter"
          @filter-versions="onFilterVersions"
          @rollback-version="onRollback"
          @delete-version="onDeleteVersion"
        />
      </template>
    </ProjectWorkspaceShell>
  </div>
  <div
    v-else
    class="rounded-[2rem] border border-[color:var(--line-soft)] bg-[rgba(251,247,239,0.82)] px-6 py-14 text-center text-sm text-[color:var(--ink-muted)] shadow-[0_24px_44px_rgba(70,47,23,0.1)]"
  >
    加载项目工作区...
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api/client'
import type { ChatResponse, RefreshTarget, ResolveActionResponse, WorkspacePanel } from '../api/types'
import ChatWorkspace from '../components/workspace/ChatWorkspace.vue'
import InspectorPanel from '../components/workspace/InspectorPanel.vue'
import ProjectWorkspaceShell from '../components/workspace/ProjectWorkspaceShell.vue'
import { parseSlashCommand } from '../components/workspace/chatCommands'
import {
  getActionLabel,
  getActionPanel,
  getActionRefreshTargets,
  getPanelRefreshTargets,
  getVersionRefreshTarget,
  getVersionTypeLabel,
  getWorkspaceTabLabel,
  getWorkspaceTabs,
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

const tabs = getWorkspaceTabs()

const route = useRoute()
const project = useProjectStore()
const chat = useChatStore()
const workspace = useWorkspaceStore()
const pid = computed(() => route.params.id as string)
const ready = ref(false)
const hydrationTracker = createHydrationTracker()
const hydratedTargets = hydrationTracker.targets

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
  return {
    projectId,
    version: hydrationTracker.version,
  }
}

function shouldIgnoreMissingTarget(target: RefreshTarget, error: unknown) {
  if (target === 'project') return false
  const message = error instanceof Error ? error.message : String(error || '')
  return /not found/i.test(message)
}

async function loadTarget(projectId: string, target: RefreshTarget) {
  try {
    switch (target) {
      case 'project':
        await project.loadProject(projectId)
        break
      case 'setup':
        await project.loadSetup(projectId)
        break
      case 'storyline':
        await project.loadStoryline(projectId)
        break
      case 'outline':
        await project.loadOutline(projectId)
        break
      case 'content':
        await project.loadChapters(projectId)
        break
      case 'topology':
        await project.loadTopology(projectId)
        break
      case 'versions':
        await project.loadVersions(projectId, project.versionsNodeType)
        break
      case 'preferences':
        await project.loadPreferences(projectId)
        break
    }
  } catch (error) {
    if (shouldIgnoreMissingTarget(target, error)) {
      return
    }
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

async function send(text: string) {
  const parsed = parseSlashCommand(text)
  if (chat.pendingAction && !(parsed.kind === 'command' && parsed.name === 'clear')) return
  workspace.applyUserPanel(workspace.panel, '你发送了一条消息')
  const res = parsed.kind === 'command'
    ? await chat.sendCommand(parsed.name, parsed.args, parsed.rawInput)
    : await chat.sendText(parsed.text)
  await handleResponse(res)
}

async function onQuickAction(type: string) {
  if (chat.pendingAction) return
  const panel = getActionPanel(type)
  if (panel) {
    workspace.applyUserPanel(panel, `你选择了${getActionLabel(type)}`)
  }
  const res = await chat.sendButtonAction(type)
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

function onSelectPanel(panel: WorkspacePanel) {
  workspace.applyUserPanel(panel, `你切换到${getWorkspaceTabLabel(panel)}`)
}

async function loadChapter(index: number) {
  const snapshot = currentHydrationSnapshot()
  workspace.applyUserPanel('content', `你刚点了第 ${index} 章`)
  await project.loadChapter(pid.value, index)
  markHydratedTarget(hydrationTracker, snapshot, 'content')
}

async function onExport(format: string) {
  workspace.applyUserPanel('overview', `你导出了 ${format.toUpperCase()} 文件`)
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
  const version = project.versions.find((item) => item.id === versionId)
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
</script>
