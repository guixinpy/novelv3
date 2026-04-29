import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type {
  ChatHistoryMessage,
  ChatMessageType,
  ChatResponse,
  BackgroundTaskResponse,
  PendingAction as ApiPendingAction,
  ProjectDiagnosis,
  ResolveActionResponse,
  ChapterContent,
  WorkspaceBootstrap,
} from '../api/types'
import type { ChatCommandName } from '../components/workspace/chatCommands'
import { useProjectWorkspaceStore } from './projectWorkspace'

export type PendingAction = ApiPendingAction
export type Diagnosis = ProjectDiagnosis

export interface ChatMessage {
  id?: string
  role: 'user' | 'assistant' | 'system'
  content: string
  message_type?: ChatMessageType | null
  meta?: Record<string, unknown> | null
  pending_action?: PendingAction | null
  diagnosis?: Diagnosis | null
  action_result?: Record<string, unknown> | null
  trace_id?: string | null
}

function toChatMessage(message: ChatHistoryMessage): ChatMessage {
  return {
    ...(message.id ? { id: message.id } : {}),
    role: message.role,
    content: message.content,
    message_type: message.message_type || null,
    meta: message.meta || null,
    pending_action: message.pending_action || null,
    diagnosis: message.diagnosis || null,
    action_result: message.action_result || null,
    ...('trace_id' in message ? { trace_id: message.trace_id || null } : {}),
  }
}

function isTerminalActionResult(actionResult: Record<string, unknown> | null | undefined, actionType: string) {
  if (!actionResult) return false
  return actionResult.type === actionType
    && isTerminalStatus(String(actionResult.status || ''))
}

function isTerminalStatus(status: string) {
  return ['completed', 'success', 'failed', 'cancelled', 'revised'].includes(status)
}

function getActionTaskId(actionResult: Record<string, unknown> | null | undefined) {
  const data = actionResult?.data
  if (!data || typeof data !== 'object') return ''
  const taskId = (data as Record<string, unknown>).task_id
  return typeof taskId === 'string' ? taskId : ''
}

function findRecoverableRunningActionType(history: ChatHistoryMessage[] | null | undefined) {
  if (!history?.length) return null
  const finishedActionTypes = new Set<string>()
  for (let index = history.length - 1; index >= 0; index -= 1) {
    const actionResult = history[index]?.action_result
    const actionType = typeof actionResult?.type === 'string' ? actionResult.type : ''
    const actionStatus = String(actionResult?.status || '')
    if (!actionType || !actionStatus) continue
    if (['completed', 'success', 'failed', 'cancelled', 'revised'].includes(actionStatus)) {
      finishedActionTypes.add(actionType)
      continue
    }
    if (['running', 'generating'].includes(actionStatus) && !finishedActionTypes.has(actionType)) {
      return actionType
    }
  }
  return null
}

const CHAT_HISTORY_PAGE_SIZE = 80

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const projectId = ref<string>('')
  const diagnosis = ref<Diagnosis | null>(null)
  const pendingAction = ref<PendingAction | null>(null)
  const loading = ref(false)
  const historyCursor = ref(0)
  const lastHistoryMessageId = ref<string | null>(null)
  const initVersion = ref(0)

  function captureSnapshot() {
    return {
      pidSnapshot: projectId.value,
      versionSnapshot: initVersion.value,
    }
  }

  function isActiveSnapshot(pidSnapshot: string, versionSnapshot: number) {
    return projectId.value === pidSnapshot && initVersion.value === versionSnapshot
  }

  function setDialogType(_type: 'hermes' | 'athena') {
    // dialogType removed — Athena chat uses athena.ts store.
    // Kept as no-op stub for backward compatibility during transition.
  }

  function resetForProject(pid: string) {
    projectId.value = pid
    messages.value = [
      { role: 'assistant', content: '你好，我是墨舟，你的长篇写作助手。有什么想聊的？' },
    ]
    diagnosis.value = null
    pendingAction.value = null
    loading.value = false
    historyCursor.value = 0
    lastHistoryMessageId.value = null
  }

  function applyHistorySnapshot(
    history: ChatHistoryMessage[] | null | undefined,
    pidSnapshot: string,
    versionSnapshot: number,
  ): boolean {
    if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return false
    if (history && history.length > 0) {
      messages.value = history.map((message) => toChatMessage(message))
    }
    const restoredPendingAction = history
      ? [...history]
        .reverse()
        .map((message) => message.pending_action || null)
        .find((pending) => Boolean(pending)) || null
      : null
    pendingAction.value = restoredPendingAction
    historyCursor.value = history?.length || 0
    lastHistoryMessageId.value = history?.length ? history[history.length - 1]?.id || null : null
    const runningActionType = restoredPendingAction ? null : findRecoverableRunningActionType(history)
    if (runningActionType) {
      loading.value = true
      void pollForCompletion(runningActionType, pidSnapshot, versionSnapshot)
    }
    return true
  }

  async function init(pid: string) {
    initVersion.value += 1
    const versionSnapshot = initVersion.value
    resetForProject(pid)
    await Promise.all([
      loadHistory(pid, versionSnapshot),
      loadDiagnosis(pid, versionSnapshot),
    ])
  }

  function initFromWorkspaceBootstrap(pid: string, bootstrap: WorkspaceBootstrap) {
    initVersion.value += 1
    const versionSnapshot = initVersion.value
    resetForProject(pid)
    diagnosis.value = bootstrap.diagnosis
    applyHistorySnapshot(bootstrap.dialogs.hermes?.messages || [], pid, versionSnapshot)
  }

  async function loadHistory(pidSnapshot = projectId.value, versionSnapshot = initVersion.value): Promise<boolean> {
    if (!pidSnapshot) return false
    try {
      const history = await api.getMessages(pidSnapshot, 'hermes', { limit: CHAT_HISTORY_PAGE_SIZE })
      return applyHistorySnapshot(history, pidSnapshot, versionSnapshot)
    } catch { /* first visit, no history */ }
    return false
  }

  async function loadDiagnosis(pidSnapshot = projectId.value, versionSnapshot = initVersion.value) {
    if (!pidSnapshot) return
    try {
      const nextDiagnosis = await api.getDiagnosis(pidSnapshot)
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return
      diagnosis.value = nextDiagnosis
    } catch { /* ignore */ }
  }

  async function sendText(text: string): Promise<ChatResponse | null> {
    if (loading.value || !text.trim()) return null
    const { pidSnapshot, versionSnapshot } = captureSnapshot()
    messages.value.push({ role: 'user', content: text })
    loading.value = true
    try {
      const res = await api.sendChat({
        project_id: pidSnapshot,
        input_type: 'text',
        text,
      })
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return null
      const msg: ChatMessage = {
        role: 'assistant',
        content: res.message,
        message_type: res.message_type || null,
        meta: res.meta || null,
        pending_action: res.pending_action || null,
        diagnosis: res.project_diagnosis || null,
        trace_id: res.trace_id || null,
      }
      messages.value.push(msg)
      historyCursor.value += 2
      if (res.pending_action) pendingAction.value = res.pending_action
      if (res.project_diagnosis) diagnosis.value = res.project_diagnosis
      return res
    } catch (e: any) {
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return null
      messages.value.push({ role: 'assistant', content: `出错了：${e.message}` })
      return null
    } finally {
      if (isActiveSnapshot(pidSnapshot, versionSnapshot)) {
        loading.value = false
      }
    }
  }

  async function sendButtonAction(actionType: string): Promise<ChatResponse | null> {
    if (loading.value) return null
    const { pidSnapshot, versionSnapshot } = captureSnapshot()
    loading.value = true
    try {
      const res = await api.sendChat({
        project_id: pidSnapshot,
        input_type: 'button',
        action_type: actionType,
        params: { project_id: pidSnapshot },
      })
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return null
      const msg: ChatMessage = {
        role: 'assistant',
        content: res.message,
        message_type: res.message_type || null,
        meta: res.meta || null,
        pending_action: res.pending_action || null,
        diagnosis: res.project_diagnosis || null,
        trace_id: res.trace_id || null,
      }
      messages.value.push(msg)
      historyCursor.value += 1
      if (res.pending_action) pendingAction.value = res.pending_action
      if (res.project_diagnosis) diagnosis.value = res.project_diagnosis
      return res
    } catch (e: any) {
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return null
      messages.value.push({ role: 'assistant', content: `出错了：${e.message}` })
      return null
    } finally {
      if (isActiveSnapshot(pidSnapshot, versionSnapshot)) {
        loading.value = false
      }
    }
  }

  async function resolveAction(decision: 'confirm' | 'cancel' | 'revise', comment = ''): Promise<ResolveActionResponse | null> {
    if (!pendingAction.value || loading.value) return null
    const { pidSnapshot, versionSnapshot } = captureSnapshot()
    loading.value = true
    const actionId = pendingAction.value.id
    let keepLoadingUntilTerminal = false
    try {
      const res = await api.resolveAction({ action_id: actionId, decision, comment })
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return null
      pendingAction.value = null
      const msg: ChatMessage = {
        role: 'system',
        content: res.message,
        action_result: res.action_result || null,
      }
      messages.value.push(msg)
      historyCursor.value += 1
      if (decision === 'confirm') {
        keepLoadingUntilTerminal = true
        const actionType = String(res.action_result?.type || '')
        const taskId = getActionTaskId(res.action_result)
        if (taskId) {
          void pollTaskCompletion(taskId, actionType, pidSnapshot, versionSnapshot)
        } else {
          void pollForCompletion(actionType, pidSnapshot, versionSnapshot)
        }
      }
      await loadDiagnosis(pidSnapshot, versionSnapshot)
      return res
    } catch (e: any) {
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return null
      messages.value.push({ role: 'assistant', content: `操作失败：${e.message}` })
      return null
    } finally {
      if (isActiveSnapshot(pidSnapshot, versionSnapshot) && !keepLoadingUntilTerminal) {
        loading.value = false
      }
    }
  }

  async function sendCommand(name: ChatCommandName, args: string, rawInput: string): Promise<ChatResponse | null> {
    if (loading.value || !name) return null
    const { pidSnapshot, versionSnapshot } = captureSnapshot()
    messages.value.push({ role: 'user', content: rawInput })
    loading.value = true
    try {
      const res = await api.sendChat({
        project_id: pidSnapshot,
        input_type: 'command',
        command_name: name,
        command_args: args,
      })
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return null
      if (name === 'compact' || name === 'clear') {
        const historyLoaded = await loadHistory(pidSnapshot, versionSnapshot)
        if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return null
        if (!historyLoaded) {
          messages.value.push({
            role: 'system',
            content: '命令已执行，但历史刷新失败，请手动刷新。',
          })
        }
      } else {
        const msg: ChatMessage = {
          role: 'assistant',
          content: res.message,
          message_type: res.message_type || null,
          meta: res.meta || null,
          pending_action: res.pending_action || null,
          diagnosis: res.project_diagnosis || null,
          trace_id: res.trace_id || null,
        }
        messages.value.push(msg)
        historyCursor.value += 2
      }
      pendingAction.value = res.pending_action || null
      if (res.project_diagnosis) diagnosis.value = res.project_diagnosis
      return res
    } catch (e: any) {
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return null
      messages.value.push({ role: 'assistant', content: `出错了：${e.message}` })
      return null
    } finally {
      if (isActiveSnapshot(pidSnapshot, versionSnapshot)) {
        loading.value = false
      }
    }
  }

  async function regenerateRevision(revisionId: string): Promise<ChapterContent | null> {
    if (loading.value || !revisionId) return null
    const { pidSnapshot, versionSnapshot } = captureSnapshot()
    loading.value = true
    try {
      const chapter = await api.regenerateRevision(pidSnapshot, revisionId)
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return null
      await loadHistory(pidSnapshot, versionSnapshot)
      await loadDiagnosis(pidSnapshot, versionSnapshot)
      return chapter
    } catch (e: any) {
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return null
      messages.value.push({ role: 'assistant', content: `修订重生成失败：${e.message}` })
      return null
    } finally {
      if (isActiveSnapshot(pidSnapshot, versionSnapshot)) {
        loading.value = false
      }
    }
  }

  async function pollForCompletion(
    actionType: string,
    pidSnapshot = projectId.value,
    versionSnapshot = initVersion.value,
  ) {
    if (!pidSnapshot || !actionType) return
    const maxAttempts = 30
    let reachedTerminal = false
    try {
      for (let i = 0; i < maxAttempts; i++) {
        if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) break
        await new Promise(r => setTimeout(r, 3000))
        try {
          if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) break
          const currentLastMessageId = getCurrentLastMessageId()
          const canLoadIncrementally = Boolean(currentLastMessageId)
          const history = await api.getMessages(
            pidSnapshot,
            'hermes',
            canLoadIncrementally
              ? { after_id: currentLastMessageId as string }
              : { limit: CHAT_HISTORY_PAGE_SIZE },
          )
          if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) break
          const newMessages = canLoadIncrementally
            ? history || []
            : (history || []).slice(historyCursor.value)
          if (newMessages.length) {
            for (const message of newMessages) {
              messages.value.push(toChatMessage(message))
            }
            historyCursor.value = canLoadIncrementally
              ? historyCursor.value + newMessages.length
              : (history || []).length
            lastHistoryMessageId.value = newMessages[newMessages.length - 1]?.id || lastHistoryMessageId.value
            await loadDiagnosis(pidSnapshot, versionSnapshot)
            if (newMessages.some((message) => isTerminalActionResult(message.action_result || null, actionType))) {
              reachedTerminal = true
              break
            }
          }
        } catch { /* retry */ }
      }
    } finally {
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return // eslint-disable-line no-unsafe-finally
      loading.value = false
      if (!reachedTerminal) {
        messages.value.push({
          role: 'system',
          content: '后台任务状态获取超时，请稍后刷新重试。',
        })
      }
    }
  }

  function getCurrentLastMessageId() {
    if (lastHistoryMessageId.value) return lastHistoryMessageId.value
    for (let index = messages.value.length - 1; index >= 0; index -= 1) {
      const id = messages.value[index]?.id
      if (id) return id
    }
    return null
  }

  async function appendNewMessages(pidSnapshot: string, versionSnapshot: number) {
    const currentLastMessageId = getCurrentLastMessageId()
    const canLoadIncrementally = Boolean(currentLastMessageId)
    const history = await api.getMessages(
      pidSnapshot,
      'hermes',
      canLoadIncrementally
        ? { after_id: currentLastMessageId as string }
        : { limit: CHAT_HISTORY_PAGE_SIZE },
    )
    if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return []
    const newMessages = canLoadIncrementally
      ? history || []
      : (history || []).slice(historyCursor.value)
    if (newMessages.length) {
      for (const message of newMessages) {
        messages.value.push(toChatMessage(message))
      }
      historyCursor.value = canLoadIncrementally
        ? historyCursor.value + newMessages.length
        : (history || []).length
      lastHistoryMessageId.value = newMessages[newMessages.length - 1]?.id || lastHistoryMessageId.value
    }
    return newMessages
  }

  async function pollTaskCompletion(
    taskId: string,
    actionType: string,
    pidSnapshot = projectId.value,
    versionSnapshot = initVersion.value,
  ) {
    if (!pidSnapshot || !taskId) return
    const workspace = useProjectWorkspaceStore()
    const maxAttempts = 60
    let reachedTerminal = false
    try {
      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) break
        if (attempt > 0) await new Promise(r => setTimeout(r, 1000))
        let task: BackgroundTaskResponse | null = null
        try {
          task = await api.getBackgroundTask(taskId)
        } catch {
          continue
        }
        if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) break
        if (!isTerminalStatus(String(task.status || ''))) continue
        reachedTerminal = true
        workspace.markDirty(task.refresh_targets || [])
        const newMessages = await appendNewMessages(pidSnapshot, versionSnapshot)
        if (!newMessages.some((message) => isTerminalActionResult(message.action_result || null, actionType))) {
          await loadHistory(pidSnapshot, versionSnapshot)
        }
        await loadDiagnosis(pidSnapshot, versionSnapshot)
        break
      }
    } finally {
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return // eslint-disable-line no-unsafe-finally
      loading.value = false
      if (!reachedTerminal) {
        messages.value.push({
          role: 'system',
          content: '后台任务状态获取超时，请稍后刷新重试。',
        })
      }
    }
  }

  return {
    messages, projectId, diagnosis, pendingAction, loading,
    init, initFromWorkspaceBootstrap, loadDiagnosis, setDialogType, sendText, sendCommand, sendButtonAction, resolveAction, regenerateRevision,
  }
})
