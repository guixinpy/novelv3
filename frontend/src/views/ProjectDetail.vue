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
const hydratedTargets = new Set<RefreshTarget>()

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
  hydratedTargets.clear()
  project.resetProjectScopedState(projectId)
  workspace.reset()
  chat.init(projectId)
  await project.loadProject(projectId)
  hydratedTargets.add('project')
  await ensurePanelData(workspace.panel, projectId)
  ready.value = true
}

async function loadTarget(projectId: string, target: RefreshTarget) {
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
}

async function ensurePanelData(panel: WorkspacePanel, projectId = pid.value, force = false) {
  for (const target of getPanelRefreshTargets(panel)) {
    if (!force && hydratedTargets.has(target)) continue
    await loadTarget(projectId, target)
    hydratedTargets.add(target)
  }
}

async function refreshProjectTargets(targets: RefreshTarget[]) {
  if (!targets.length) return
  await project.refreshTargets(pid.value, targets)
  for (const target of targets) {
    hydratedTargets.add(target)
  }
  if (targets.includes('content') && project.chapter?.chapter_index != null) {
    await project.loadChapter(pid.value, project.chapter.chapter_index)
  }
}

async function handleResponse(res: UiAwareResponse | null) {
  if (!res) return
  workspace.applyUiHint(res.ui_hint)
  await refreshProjectTargets(res.refresh_targets)
}

async function send(text: string) {
  if (chat.pendingAction) return
  const res = await chat.sendText(text)
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
  const res = await chat.resolveAction(decision as 'confirm' | 'cancel' | 'revise', comment)
  await handleResponse(res)
}

function onSelectPanel(panel: WorkspacePanel) {
  workspace.applyUserPanel(panel, `你切换到${getWorkspaceTabLabel(panel)}`)
}

async function loadChapter(index: number) {
  workspace.applyUserPanel('content', `你刚点了第 ${index} 章`)
  await project.loadChapter(pid.value, index)
  hydratedTargets.add('content')
}

async function onExport(format: string) {
  await project.exportProject(pid.value, format)
}

async function onFilterVersions(type: string) {
  const reason = type
    ? `你筛选了${getVersionTypeLabel(type)}版本`
    : '你查看全部版本记录'
  workspace.applyUserPanel('versions', reason)
  await project.loadVersions(pid.value, type || undefined)
  hydratedTargets.add('versions')
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
