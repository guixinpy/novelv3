<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api/client'
import type {
  ChatResponse,
  PendingActionSafetyAction,
  RefreshTarget,
  ResolveActionResponse,
  WorkspacePanel,
  WritingAgentRunDetail,
  WritingAgentToolRequest,
} from '../api/types'
import ProjectDashboard from '../components/shared/ProjectDashboard.vue'
import ExportModal from '../components/shared/ExportModal.vue'
import VersionsModal from '../components/shared/VersionsModal.vue'
import ChatMessageList from '../components/chat/ChatMessageList.vue'
import ChatInput from '../components/chat/ChatInput.vue'
import ModelTraceDrawer from '../components/modelTrace/ModelTraceDrawer.vue'
import AgentRunDrawer from '../components/writingAgent/AgentRunDrawer.vue'
import {
  chatCommandRegistry,
  normalizeChatCommandDefinitions,
  parseSlashCommand,
  type ChatCommandDefinition,
} from '../components/workspace/chatCommands'
import {
  getActionLabel,
  getActionRefreshTargets,
  getPanelRefreshTargets,
  getVersionRefreshTargets,
  getVersionTypeLabel,
  isFinishedActionStatus,
  normalizeActionStatus,
} from '../components/workspace/workspaceMeta'
import {
  beginHydration,
  createHydrationTracker,
  getInitialProjectHydrationTargets,
  isActiveHydrationSnapshot,
  markHydratedTarget,
  markHydratedTargets,
  shouldHydratePanelTarget,
  type HydrationSnapshot,
} from './projectDetailHydration'
import { createActionReplayGuard } from './hermesActionReplay'
import { useChatStore } from '../stores/chat'
import { useModelTraceStore } from '../stores/modelTraces'
import { useProjectStore } from '../stores/project'
import { useProjectWorkspaceStore } from '../stores/projectWorkspace'
import { useWorkspaceStore } from '../stores/workspace'

type UiAwareResponse =
  | Pick<ChatResponse, 'ui_hint' | 'refresh_targets'>
  | Pick<ResolveActionResponse, 'ui_hint' | 'refresh_targets'>

type WritingControlAction = 'start' | 'pause' | 'resume'
type RecoveryExecutePayload = { sourceRunId: string; planHash: string }
type RecommendedFollowupExecutePayload = { sourceRunId: string; planHash: string }
type PlannerPlanExecutePayload = {
  sourceRunId: string
  sourcePlanId: string
  goal: string
  tools: Array<Record<string, unknown>>
  planner: Record<string, unknown>
  approvalContractHash?: string
  approvalContract?: Record<string, unknown>
}
type RouteUpgradeApplyPayload = {
  sourceRunId: string
  pendingActionId: string
  approvalContractHash: string
  approvalContract: Record<string, unknown>
}
type MemoryTreePanelResultRow = {
  key: string
  levelLabel: string
  title: string
  chapterLabel: string
  summary: string
  relevanceLabel: string
  expandNodeId: string
  canExpand: boolean
  depth: number
}

const route = useRoute()
const router = useRouter()
const project = useProjectStore()
const chat = useChatStore()
const modelTrace = useModelTraceStore()
const workspace = useWorkspaceStore()
const projectWorkspace = useProjectWorkspaceStore()
const pid = computed(() => route.params.id as string)
const ready = ref(false)
const hydrationTracker = createHydrationTracker()
const hydratedTargets = hydrationTracker.targets
const actionReplayGuard = createActionReplayGuard()

// Modal state
const showExportModal = ref(false)
const showVersionsModal = ref(false)
const handledRevisionIds = ref(new Set<string>())
const activeTraceId = ref<string | null>(null)
const activeAgentRunId = ref<string | null>(null)
const activeAgentRun = ref<WritingAgentRunDetail | null>(null)
const agentRunLoading = ref(false)
const agentRunError = ref('')
const writingControlLoading = ref(false)
const chatCommands = ref<ChatCommandDefinition[]>(chatCommandRegistry)
const memoryTreeNavigationHistory = computed(() => projectWorkspace.memoryTreeHistoryForProject(pid.value))
const memoryTreePanelQuery = ref('')
const memoryTreePanelLoading = ref(false)
const memoryTreePanelError = ref('')
const memoryTreePanelSearchText = computed(() => safeMemoryTreeDisplayValue(memoryTreePanelQuery.value))
const canSearchMemoryTreePanel = computed(() => Boolean(memoryTreePanelSearchText.value) && !memoryTreePanelLoading.value)
const memoryTreePanelOutput = computed(() => latestRunToolOutput(activeAgentRun.value, 'inspect_agent_memory_tree'))
const memoryTreePanelSummary = computed(() => recordValue(memoryTreePanelOutput.value?.summary))
const memoryTreePanelSummaryLabel = computed(() => {
  const counts = [
    ['卷', numberValue(memoryTreePanelSummary.value.volume_nodes)],
    ['章节', numberValue(memoryTreePanelSummary.value.chapter_nodes)],
    ['场景', numberValue(memoryTreePanelSummary.value.scene_nodes)],
    ['节拍', numberValue(memoryTreePanelSummary.value.beat_nodes)],
  ]
  return counts
    .filter((item): item is [string, number] => item[1] !== null)
    .map(([label, count]) => `${label} ${count}`)
    .join(' / ')
})
const memoryTreePanelNodes = computed(() => recordList(memoryTreePanelOutput.value?.nodes))
const memoryTreePanelNavigation = computed(() => recordValue(memoryTreePanelOutput.value?.navigation))
const memoryTreePanelExpandedNodeId = computed(() => stringValue(memoryTreePanelNavigation.value.expanded_node_id))
const memoryTreePanelExpandedNodeLabel = computed(() => {
  const expandedNodeId = memoryTreePanelExpandedNodeId.value
  if (!expandedNodeId) return ''
  const node = memoryTreePanelNodes.value.find((item) => stringValue(item.id) === expandedNodeId)
  return safeMemoryTreeDisplayValue(node?.title) || chapterIndexLabel(node?.chapter_index) || '当前节点'
})
const memoryTreePanelNodeCount = computed(() => memoryTreePanelNodes.value.length)
const memoryTreePanelResultRows = computed<MemoryTreePanelResultRow[]>(() => (
  orderMemoryTreePanelNodes(memoryTreePanelNodes.value).map(({ node, depth }, index) => {
    const level = stringValue(node.level)
    const relevance = recordValue(node.relevance)
    const score = numberValue(relevance.score)
    const title = safeMemoryTreeDisplayValue(node.title) || '未命名节点'
    const expandNodeId = stringValue(node.id)
    const canExpand = Boolean(expandNodeId) && stringList(node.children).length > 0
    return {
      key: `memory-tree-panel-result:${index}`,
      levelLabel: memoryTreeLevelLabel(level),
      title,
      chapterLabel: chapterIndexLabel(node.chapter_index),
      summary: safeMemoryTreeDisplayValue(node.summary),
      relevanceLabel: score !== null ? `相关度 ${score.toFixed(2)}` : '',
      expandNodeId,
      canExpand,
      depth,
    }
  })
))

// Project stats
const totalWords = computed(() => {
  const projectWordCount = Number(project.currentProject?.current_word_count || 0)
  if (projectWordCount > 0) return projectWordCount
  return (project.chapters || []).reduce((sum: number, c: any) => sum + (c.word_count || 0), 0)
})

const selectedChapterTraceId = computed(() => project.chapter?.last_generation_trace_id || null)

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
  if (!actionReplayGuard.shouldProcess(fingerprint)) return
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
  closeTrace()
  await loadChatCommandCatalog()
  const snapshot = beginHydration(hydrationTracker, projectId)
  const projectChanged = projectWorkspace.enterProject(projectId)
  if (projectChanged) {
    project.resetProjectScopedState(projectId)
    workspace.reset()
  }
  const hasWarmWorkspace =
    !projectChanged &&
    project.currentProject?.id === projectId &&
    chat.projectId === projectId &&
    !!chat.diagnosis
  if (hasWarmWorkspace) {
    markHydratedTargets(hydrationTracker, snapshot, ['project', 'setup', 'storyline', 'outline', 'content', 'versions'])
  } else try {
    const bootstrap = await api.getWorkspaceBootstrap(projectId)
    if (!isActiveHydrationSnapshot(hydrationTracker, snapshot)) return
    project.applyWorkspaceBootstrap(bootstrap)
    chat.initFromWorkspaceBootstrap(projectId, bootstrap)
    markHydratedTargets(hydrationTracker, snapshot, ['project', 'content', 'versions'])
  } catch {
    await Promise.all([
      chat.init(projectId),
      project.loadProject(projectId),
    ])
    if (!markHydratedTarget(hydrationTracker, snapshot, 'project')) return
  }
  actionReplayGuard.markInitial(latestActionFingerprint.value)
  const initialTargets = new Set<RefreshTarget>(getInitialProjectHydrationTargets(chat.diagnosis))
  for (const target of getPanelRefreshTargets(workspace.panel)) {
    if (target !== 'project') initialTargets.add(target)
  }
  initialTargets.add('content')
  await Promise.all([
    ...[...initialTargets].filter((target) => !hydratedTargets.has(target)).map((target) => loadTarget(projectId, target).then(() => {
      markHydratedTarget(hydrationTracker, snapshot, target)
    }).catch(() => {})),
  ])
  if (!isActiveHydrationSnapshot(hydrationTracker, snapshot)) return
  ready.value = true
  await handleRevisionQuery(projectId)
}

async function loadChatCommandCatalog() {
  try {
    const catalog = await api.getChatCommandCatalog()
    chatCommands.value = normalizeChatCommandDefinitions(catalog.commands)
  } catch {
    chatCommands.value = chatCommandRegistry
  }
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
  await refreshProjectTargets(['project', 'content', 'versions', 'writing_state'], currentHydrationSnapshot(projectId))
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
    if (!force && !shouldHydratePanelTarget(target, chat.diagnosis)) continue
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
  const parsed = parseSlashCommand(text, chatCommands.value)
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

async function onSafetyAction(action: PendingActionSafetyAction) {
  workspace.applyUserPanel(workspace.panel, '你请求生成审批契约')
  const run = await chat.preparePendingActionSafetyAction(action)
  if (!run) return
  activeAgentRunId.value = run.id
  activeAgentRun.value = run
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

async function onWritingControl(action: WritingControlAction) {
  if (writingControlLoading.value) return
  writingControlLoading.value = true
  try {
    if (action === 'pause') {
      workspace.applyUserPanel('content', '你暂停了连续写作')
      await project.pauseWriting(pid.value)
      return
    }
    if (action === 'resume') {
      workspace.applyUserPanel('content', '你继续连续写作')
      await project.resumeWriting(pid.value)
      return
    }
    workspace.applyUserPanel('content', '你开始连续写作')
    await project.startWriting(pid.value)
  } finally {
    writingControlLoading.value = false
  }
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

async function onLoadMoreVersions() {
  await project.loadMoreVersions(pid.value)
}

async function onRollback(versionId: string) {
  workspace.applyUserPanel('versions', '你发起了版本回滚')
  const version = project.versions.find((item: any) => item.id === versionId)
  await project.rollbackVersion(pid.value, versionId)
  const targets: RefreshTarget[] = ['versions']
  targets.push(...getVersionRefreshTargets(version?.node_type))
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

function openTrace(traceId: string) {
  if (!traceId) return
  activeTraceId.value = traceId
}

function closeTrace() {
  activeTraceId.value = null
  modelTrace.closeTrace()
}

async function openAgentRun(runId: string) {
  const targetRunId = String(runId || '').trim()
  if (!targetRunId) return
  activeAgentRunId.value = targetRunId
  activeAgentRun.value = null
  agentRunError.value = ''
  agentRunLoading.value = true
  try {
    activeAgentRun.value = await api.getAgentRun(pid.value, targetRunId)
  } catch (err) {
    agentRunError.value = err instanceof Error ? err.message : '加载 Agent 运行详情失败'
  } finally {
    agentRunLoading.value = false
  }
}

async function refreshAgentRun() {
  if (!activeAgentRunId.value) return
  await openAgentRun(activeAgentRunId.value)
}

function closeAgentRun() {
  activeAgentRunId.value = null
  activeAgentRun.value = null
  agentRunError.value = ''
  agentRunLoading.value = false
}

function openMemoryTreeHistoryRun(runId: string | undefined) {
  if (!runId) return
  void openAgentRun(runId)
}

async function submitMemoryTreePanelSearch() {
  const query = memoryTreePanelSearchText.value
  if (!query || memoryTreePanelLoading.value) return
  memoryTreePanelError.value = ''
  memoryTreePanelLoading.value = true
  agentRunError.value = ''
  try {
    const run = await api.createAgentRun(pid.value, {
      goal: `搜索 Memory Tree：${query}`,
      entrypoint: 'ui_memory_tree_panel_search',
      tools: [
        {
          tool_name: 'inspect_agent_memory_tree',
          params: {
            query,
            include_ancestors: true,
            max_depth: 2,
          },
        },
      ],
      input: {
        memory_tree_panel_search: true,
        query,
      },
    })
    activeAgentRunId.value = run.id
    activeAgentRun.value = run
    projectWorkspace.appendMemoryTreeHistory(pid.value, {
      key: `${run.id}:panel-search:${memoryTreeNavigationHistory.value.length}`,
      label: `搜索：${query}`,
      runId: run.id,
    })
    memoryTreePanelQuery.value = ''
  } catch (err) {
    memoryTreePanelError.value = err instanceof Error ? err.message : '搜索 Memory Tree 失败'
  } finally {
    memoryTreePanelLoading.value = false
  }
}

async function expandMemoryTreePanelNode(row: MemoryTreePanelResultRow) {
  if (!row.canExpand || !row.expandNodeId || memoryTreePanelLoading.value) return
  memoryTreePanelError.value = ''
  memoryTreePanelLoading.value = true
  agentRunError.value = ''
  try {
    const run = await api.createAgentRun(pid.value, {
      goal: `展开 Memory Tree：${row.title}`,
      entrypoint: 'ui_memory_tree_panel_expand',
      tools: [
        {
          tool_name: 'inspect_agent_memory_tree',
          params: {
            expand_node_id: row.expandNodeId,
            include_ancestors: true,
            max_depth: 1,
          },
        },
      ],
      input: {
        memory_tree_panel_expand: true,
        source_run_id: activeAgentRun.value?.id || '',
        expand_node_label: row.title,
      },
    })
    activeAgentRunId.value = run.id
    activeAgentRun.value = run
    projectWorkspace.appendMemoryTreeHistory(pid.value, {
      key: `${run.id}:panel-expand:${memoryTreeNavigationHistory.value.length}`,
      label: `节点展开：${row.title}`,
      runId: run.id,
    })
  } catch (err) {
    memoryTreePanelError.value = err instanceof Error ? err.message : '展开 Memory Tree 失败'
  } finally {
    memoryTreePanelLoading.value = false
  }
}

async function executeRecoveryFromRun(payload: RecoveryExecutePayload) {
  agentRunError.value = ''
  agentRunLoading.value = true
  try {
    const run = await api.createAgentRun(pid.value, {
      goal: '执行恢复计划',
      entrypoint: 'ui_recovery_execute',
      input: {
        auto_plan: true,
        recovery_run_id: payload.sourceRunId,
        execute_recovery: true,
        confirm_execute: true,
        recovery_plan_hash: payload.planHash,
      },
    })
    activeAgentRunId.value = run.id
    activeAgentRun.value = run
    chat.appendAgentRunExecutionFeedback(run)
  } catch (err) {
    agentRunError.value = err instanceof Error ? err.message : '执行恢复计划失败'
  } finally {
    agentRunLoading.value = false
  }
}

async function executeRecommendedFollowupsFromRun(payload: RecommendedFollowupExecutePayload) {
  agentRunError.value = ''
  agentRunLoading.value = true
  try {
    const run = await api.createAgentRun(pid.value, {
      goal: '执行推荐后继工具链',
      entrypoint: 'ui_recommended_followup_execute',
      input: {
        auto_plan: true,
        recommended_followup_run_id: payload.sourceRunId,
        execute_recommended_followups: true,
        confirm_execute: true,
        recommended_followup_plan_hash: payload.planHash,
      },
    })
    activeAgentRunId.value = run.id
    activeAgentRun.value = run
    chat.appendRecommendedFollowupExecutionFeedback(run)
  } catch (err) {
    agentRunError.value = err instanceof Error ? err.message : '执行推荐后继失败'
  } finally {
    agentRunLoading.value = false
  }
}

async function executePlannerPlanFromRun(payload: PlannerPlanExecutePayload) {
  const tools = normalizePlannerToolRequests(payload.tools)
  if (!payload.sourceRunId || !payload.sourcePlanId || !tools.length || !payload.planner) return
  if (payload.sourceRunId !== activeAgentRunId.value || payload.sourceRunId !== activeAgentRun.value?.id) return
  const memoryTreeHistoryLabel = memoryTreeContinuationHistoryLabel(payload, tools)
  const approvalContract = recordValue(payload.approvalContract)
  const approvalBinding = payload.approvalContractHash && Object.keys(approvalContract).length
    ? {
        confirm_execute: true,
        approval_contract_hash: payload.approvalContractHash,
        approval_contract: approvalContract,
      }
    : {}
  agentRunError.value = ''
  agentRunLoading.value = true
  try {
    const run = await api.createAgentRun(pid.value, {
      goal: payload.goal || '执行规划工具链',
      entrypoint: 'ui_planner_continuation_execute',
      tools,
      input: {
        planner_continuation: true,
        source_run_id: payload.sourceRunId,
        source_plan_id: payload.sourcePlanId,
        ...approvalBinding,
        planner: payload.planner,
      },
    })
    activeAgentRunId.value = run.id
    activeAgentRun.value = run
    if (memoryTreeHistoryLabel) {
      projectWorkspace.appendMemoryTreeHistory(pid.value, {
        key: `${run.id}:${payload.sourcePlanId}:${memoryTreeNavigationHistory.value.length}`,
        label: memoryTreeHistoryLabel,
        runId: run.id,
      })
    }
    chat.appendPlannerContinuationFeedback(run)
  } catch (err) {
    agentRunError.value = err instanceof Error ? err.message : '执行规划工具链失败'
  } finally {
    agentRunLoading.value = false
  }
}

function normalizePlannerToolRequests(tools: Array<Record<string, unknown>>): WritingAgentToolRequest[] {
  return tools.flatMap((tool) => {
    const toolName = stringValue(tool.tool_name)
    if (!toolName) return []
    const request: WritingAgentToolRequest = { tool_name: toolName }
    const commandArgs = stringValue(tool.command_args)
    if (commandArgs) request.command_args = commandArgs
    const params = recordValue(tool.params)
    if (Object.keys(params).length) request.params = params
    const planner = recordValue(tool.planner)
    if (Object.keys(planner).length) request.planner = planner
    return [request]
  })
}

function memoryTreeContinuationHistoryLabel(
  payload: PlannerPlanExecutePayload,
  tools: WritingAgentToolRequest[],
) {
  const memoryTreeTool = tools.find((tool) => tool.tool_name === 'inspect_agent_memory_tree')
  if (!memoryTreeTool) return ''
  const params = recordValue(memoryTreeTool.params)
  const query = safeMemoryTreeDisplayValue(params.query)
  if (query) return `搜索：${query}`
  const goalLabel = safeMemoryTreeDisplayValue(String(payload.goal || '').replace(/^(展开|搜索) Memory Tree：/, ''))
  const prefix = payload.sourcePlanId.includes('search')
    ? '搜索'
    : payload.sourcePlanId.includes('drilldown') ? '推荐展开' : '节点展开'
  return goalLabel ? `${prefix}：${goalLabel}` : prefix
}

function safeMemoryTreeDisplayValue(value: unknown) {
  const normalized = stringValue(value).replace(/\s+/g, ' ')
  if (!normalized) return ''
  if (/[A-Za-z_]+:[A-Za-z0-9_-]+/.test(normalized)) return ''
  if (/source_refs|source_id|approval_contract|approval:|chapter-content-\d+|memory-\d+/i.test(normalized)) return ''
  return normalized.slice(0, 48)
}

function recordValue(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function recordList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value.filter((item): item is Record<string, unknown> => (
    item !== null && typeof item === 'object' && !Array.isArray(item)
  ))
}

function stringList(value: unknown) {
  if (!Array.isArray(value)) return []
  return value.map(stringValue).filter(Boolean)
}

function stringValue(value: unknown) {
  return typeof value === 'string' ? value.trim() : ''
}

function numberValue(value: unknown) {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  return null
}

function chapterIndexLabel(value: unknown) {
  const chapterIndex = numberValue(value)
  return chapterIndex !== null ? `第${chapterIndex}章` : ''
}

function memoryTreeLevelLabel(level: unknown) {
  const value = stringValue(level)
  if (value === 'volume') return '卷'
  if (value === 'chapter') return '章节'
  if (value === 'scene') return '场景'
  if (value === 'beat') return '节拍'
  return value || '节点'
}

function latestRunToolOutput(run: WritingAgentRunDetail | null, toolName: string) {
  const steps = Array.isArray(run?.steps) ? run.steps : []
  for (let index = steps.length - 1; index >= 0; index -= 1) {
    const step = steps[index]
    if (step?.tool_name !== toolName) continue
    const output = recordValue(step.output)
    if (Object.keys(output).length) return output
  }
  return null
}

function orderMemoryTreePanelNodes(nodes: Record<string, unknown>[]) {
  const indexedRows = nodes.map((node, index) => ({
    id: stringValue(node.id),
    node,
    index,
  }))
  const rowsById = new Map<string, typeof indexedRows[number]>()
  const childrenById = new Map<string, string[]>()
  const appendChild = (parentId: string, childId: string) => {
    if (!parentId || !childId || !rowsById.has(parentId) || !rowsById.has(childId)) return
    const childIds = childrenById.get(parentId) || []
    if (!childIds.includes(childId)) childIds.push(childId)
    childrenById.set(parentId, childIds)
  }

  for (const row of indexedRows) {
    if (row.id && !rowsById.has(row.id)) rowsById.set(row.id, row)
  }
  for (const row of indexedRows) {
    if (!row.id) continue
    appendChild(stringValue(row.node.parent_id), row.id)
    for (const childId of stringList(row.node.children)) appendChild(row.id, childId)
  }

  const visited = new Set<number>()
  const orderedRows: Array<{ node: Record<string, unknown>; depth: number }> = []
  const visit = (row: typeof indexedRows[number], depth: number) => {
    if (visited.has(row.index)) return
    visited.add(row.index)
    orderedRows.push({ node: row.node, depth })
    if (!row.id) return
    for (const childId of childrenById.get(row.id) || []) {
      const child = rowsById.get(childId)
      if (child) visit(child, depth + 1)
    }
  }

  for (const row of indexedRows) {
    const parentId = stringValue(row.node.parent_id)
    if (!row.id || !parentId || !rowsById.has(parentId)) visit(row, 0)
  }
  for (const row of indexedRows) visit(row, 0)
  return orderedRows
}

async function applyRouteUpgradeFromRun(payload: RouteUpgradeApplyPayload) {
  if (!payload.pendingActionId || !payload.approvalContractHash || !payload.approvalContract) return
  if (payload.sourceRunId !== activeAgentRunId.value || payload.sourceRunId !== activeAgentRun.value?.id) return
  if (payload.pendingActionId !== chat.pendingAction?.id) return
  agentRunError.value = ''
  agentRunLoading.value = true
  try {
    const run = await api.createAgentRun(pid.value, {
      goal: '应用待确认操作的路由升级审批契约',
      entrypoint: 'pending_action_route_upgrade_apply',
      tools: [
        {
          tool_name: 'apply_pending_action_route_approval_opt_in',
          params: {
            pending_action_id: payload.pendingActionId,
            confirm_apply: true,
            approval_contract_hash: payload.approvalContractHash,
            approval_contract: payload.approvalContract,
          },
        },
      ],
      input: {
        safety_action: { kind: 'apply_route_upgrade_contract' },
        source_run_id: payload.sourceRunId,
        pending_action_id: payload.pendingActionId,
      },
    })
    activeAgentRunId.value = run.id
    activeAgentRun.value = run
    chat.appendRouteUpgradeApplyFeedback(run)
  } catch (err) {
    agentRunError.value = err instanceof Error ? err.message : '应用路由升级失败'
  } finally {
    agentRunLoading.value = false
  }
}
</script>

<template>
  <div v-if="project.currentProject && ready" class="hermes-view" data-testid="workspace-hermes">
    <!-- Sub-nav content: rendered into AppShell SubNav slot via teleport -->
    <Teleport to="[data-subnav-content]">
      <div class="hermes-subnav">
        <ProjectDashboard
          :setup="project.setup"
          :storyline="project.storyline"
          :outline="project.outline"
          :chapters="project.chapters || []"
          :chapters-total="project.chaptersTotal"
          :total-words="totalWords"
          :pending-action="chat.pendingAction"
          :ai-loading="chat.loading"
          :latest-action-label="latestActionLabel"
          :latest-action-status="latestActionStatus"
          :suggested-next-step="suggestedNextStep"
          :writing-state="project.writingState"
          :writing-task-diagnostics="project.writingTaskDiagnostics"
          :writing-task-recommendations="project.writingTaskRecommendations"
          :writing-task-progress="project.writingTaskProgress"
          :writing-control-loading="writingControlLoading"
          @tool="onDashboardTool"
          @writing-control="onWritingControl"
        />
        <section
          class="hermes-memory-tree-panel"
          data-testid="memory-tree-history-panel"
          aria-label="Memory Tree 浏览历史"
        >
          <header class="hermes-memory-tree-panel__header">
            <span>Memory Tree</span>
            <strong>{{ memoryTreeNavigationHistory.length }}</strong>
          </header>
          <form class="hermes-memory-tree-panel__search" @submit.prevent="submitMemoryTreePanelSearch">
            <input
              v-model="memoryTreePanelQuery"
              type="search"
              data-testid="memory-tree-panel-query"
              aria-label="搜索 Memory Tree"
              placeholder="搜索长期记忆"
              :disabled="memoryTreePanelLoading"
            />
            <button
              type="submit"
              data-testid="memory-tree-panel-search"
              :disabled="!canSearchMemoryTreePanel"
            >
              {{ memoryTreePanelLoading ? '搜索中' : '搜索' }}
            </button>
          </form>
          <p v-if="memoryTreePanelError" class="hermes-memory-tree-panel__error">
            {{ memoryTreePanelError }}
          </p>
          <section
            v-if="memoryTreePanelResultRows.length"
            class="hermes-memory-tree-panel__results"
            data-testid="memory-tree-panel-results"
            aria-label="Memory Tree 最近结果"
          >
            <header class="hermes-memory-tree-panel__results-header">
              <span>最近结果</span>
              <strong>返回 {{ memoryTreePanelNodeCount }} 个</strong>
            </header>
            <p v-if="memoryTreePanelSummaryLabel" class="hermes-memory-tree-panel__result-summary">
              {{ memoryTreePanelSummaryLabel }}
            </p>
            <p
              v-if="memoryTreePanelExpandedNodeLabel"
              class="hermes-memory-tree-panel__expanded-state"
              data-testid="memory-tree-panel-expanded-state"
            >
              当前展开：{{ memoryTreePanelExpandedNodeLabel }}
            </p>
            <ol class="hermes-memory-tree-panel__result-list">
              <li
                v-for="row in memoryTreePanelResultRows"
                :key="row.key"
                :data-depth="row.depth"
                :style="{ '--memory-tree-depth': row.depth }"
                data-testid="memory-tree-panel-result-node"
              >
                <span class="hermes-memory-tree-panel__result-level">{{ row.levelLabel }}</span>
                <div class="hermes-memory-tree-panel__result-content">
                  <div>
                    <strong>{{ row.title }}</strong>
                    <span v-if="row.chapterLabel">{{ row.chapterLabel }}</span>
                    <span v-if="row.relevanceLabel">{{ row.relevanceLabel }}</span>
                  </div>
                  <p v-if="row.summary">{{ row.summary }}</p>
                  <button
                    v-if="row.canExpand"
                    type="button"
                    class="hermes-memory-tree-panel__result-expand"
                    data-testid="memory-tree-panel-result-expand"
                    :disabled="memoryTreePanelLoading"
                    @click="expandMemoryTreePanelNode(row)"
                  >
                    展开
                  </button>
                </div>
              </li>
            </ol>
          </section>
          <ol v-if="memoryTreeNavigationHistory.length" class="hermes-memory-tree-panel__list">
            <li
              v-for="item in memoryTreeNavigationHistory"
              :key="item.key"
            >
              <button
                type="button"
                data-testid="memory-tree-history-open"
                :disabled="!item.runId"
                @click="openMemoryTreeHistoryRun(item.runId)"
              >
                {{ item.label }}
              </button>
            </li>
          </ol>
          <p v-else class="hermes-memory-tree-panel__empty">暂无浏览历史</p>
        </section>
        <button
          v-if="selectedChapterTraceId"
          type="button"
          class="hermes-subnav__trace"
          @click="openTrace(selectedChapterTraceId)"
        >
          生成上下文
        </button>
      </div>
    </Teleport>

    <!-- Main content: Chat interface -->
    <div class="hermes-view__chat">
      <ChatMessageList
        :messages="chat.messages"
        :loading="chat.loading"
        @decide="onDecide"
        @safety-action="onSafetyAction"
        @open-trace="openTrace"
        @open-agent-run="openAgentRun"
        @execute-recommended-followups="executeRecommendedFollowupsFromRun"
      />
      <ChatInput
        :loading="chat.loading"
        :disabled="false"
        :has-pending-action="!!chat.pendingAction"
        :commands="chatCommands"
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
      :total="project.versionsTotal"
      :has-more="project.versionsHasMore"
      :project-id="pid"
      @close="showVersionsModal = false"
      @filter="onFilterVersions"
      @load-more="onLoadMoreVersions"
      @rollback="onRollback"
      @delete-version="onDeleteVersion"
    />
    <ModelTraceDrawer
      :project-id="pid"
      :trace-id="activeTraceId"
      :open="!!activeTraceId"
      @close="closeTrace"
    />
    <AgentRunDrawer
      :open="!!activeAgentRunId"
      :run="activeAgentRun"
      :loading="agentRunLoading"
      :error="agentRunError"
      :pending-action-id="chat.pendingAction?.id || null"
      :memory-tree-history="memoryTreeNavigationHistory"
      @close="closeAgentRun"
      @refresh="refreshAgentRun"
      @execute-recovery="executeRecoveryFromRun"
      @execute-recommended-followups="executeRecommendedFollowupsFromRun"
      @execute-planner-plan="executePlannerPlanFromRun"
      @apply-route-upgrade="applyRouteUpgradeFromRun"
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

.hermes-memory-tree-panel {
  display: grid;
  gap: var(--space-2);
  margin: var(--space-3);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-secondary);
}

.hermes-memory-tree-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.hermes-memory-tree-panel__header strong {
  color: var(--color-text-tertiary);
  font-weight: var(--font-medium);
}

.hermes-memory-tree-panel__search {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 56px;
  gap: var(--space-1);
}

.hermes-memory-tree-panel__search input,
.hermes-memory-tree-panel__search button {
  min-height: 30px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: var(--text-xs);
}

.hermes-memory-tree-panel__search input {
  min-width: 0;
  padding: 0 var(--space-2);
  background: var(--color-bg-white);
  color: var(--color-text-primary);
}

.hermes-memory-tree-panel__search input::placeholder {
  color: var(--color-text-tertiary);
}

.hermes-memory-tree-panel__search input:focus {
  border-color: var(--color-primary);
  outline: none;
}

.hermes-memory-tree-panel__search button {
  padding: 0 var(--space-2);
  background: var(--color-text-primary);
  color: var(--color-bg-white);
  font-weight: var(--font-medium);
  white-space: nowrap;
}

.hermes-memory-tree-panel__search button:disabled {
  cursor: default;
  opacity: 0.45;
}

.hermes-memory-tree-panel__error,
.hermes-memory-tree-panel__empty {
  margin: 0;
  font-size: var(--text-xs);
  line-height: 1.5;
}

.hermes-memory-tree-panel__error {
  color: var(--color-danger);
}

.hermes-memory-tree-panel__empty {
  color: var(--color-text-tertiary);
}

.hermes-memory-tree-panel__results {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
}

.hermes-memory-tree-panel__results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
}

.hermes-memory-tree-panel__results-header strong {
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
  white-space: nowrap;
}

.hermes-memory-tree-panel__result-summary {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.hermes-memory-tree-panel__expanded-state {
  margin: 0;
  padding: var(--space-1) var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-muted);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.hermes-memory-tree-panel__result-list {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.hermes-memory-tree-panel__result-list li {
  display: grid;
  grid-template-columns: 2.5rem minmax(0, 1fr);
  gap: var(--space-2);
  padding-left: calc(var(--space-2) * var(--memory-tree-depth, 0));
  padding-top: var(--space-1);
  padding-bottom: var(--space-1);
  border-top: 1px solid var(--color-border);
}

.hermes-memory-tree-panel__result-level {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  white-space: nowrap;
}

.hermes-memory-tree-panel__result-content {
  display: grid;
  gap: 2px;
  min-width: 0;
}

.hermes-memory-tree-panel__result-content div {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
  align-items: baseline;
  min-width: 0;
}

.hermes-memory-tree-panel__result-content strong {
  min-width: 0;
  color: var(--color-text-primary);
  font-size: var(--text-xs);
  overflow-wrap: anywhere;
}

.hermes-memory-tree-panel__result-content span,
.hermes-memory-tree-panel__result-content p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.hermes-memory-tree-panel__result-expand {
  justify-self: start;
  min-height: 24px;
  margin-top: 2px;
  padding: 0 var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  line-height: 1;
}

.hermes-memory-tree-panel__result-expand:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-text-primary);
}

.hermes-memory-tree-panel__result-expand:disabled {
  cursor: default;
  opacity: 0.55;
}

.hermes-memory-tree-panel__list {
  display: grid;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  list-style: none;
}

.hermes-memory-tree-panel__list button {
  width: 100%;
  min-height: 28px;
  padding: 0 var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg-white);
  color: var(--color-text-secondary);
  font-size: var(--text-xs);
  text-align: left;
  overflow-wrap: anywhere;
}

.hermes-memory-tree-panel__list button:hover:not(:disabled) {
  border-color: var(--color-primary);
  color: var(--color-text-primary);
}

.hermes-memory-tree-panel__list button:disabled {
  cursor: default;
  opacity: 0.55;
}

.hermes-subnav__trace {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  max-width: calc(100% - var(--space-6));
  margin: var(--space-3);
  padding: 0 var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  line-height: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hermes-subnav__trace:hover {
  color: var(--color-text-primary);
  background: var(--color-bg-secondary);
}
</style>
