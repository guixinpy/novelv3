import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'
import type {
  ChatResponse,
  PendingAction as ApiPendingAction,
  ProjectDiagnosis,
  ResolveActionResponse,
} from '../api/types'

export type PendingAction = ApiPendingAction
export type Diagnosis = ProjectDiagnosis

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  pending_action?: PendingAction | null
  diagnosis?: Diagnosis | null
  action_result?: Record<string, unknown> | null
}

function toChatMessage(message: any): ChatMessage {
  return {
    role: message.role,
    content: message.content,
    pending_action: message.pending_action || null,
    diagnosis: message.diagnosis || null,
    action_result: message.action_result || null,
  }
}

function isTerminalActionResult(actionResult: Record<string, unknown> | null | undefined, actionType: string) {
  if (!actionResult) return false
  return actionResult.type === actionType
    && ['completed', 'success', 'failed', 'cancelled', 'revised'].includes(String(actionResult.status || ''))
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const projectId = ref<string>('')
  const diagnosis = ref<Diagnosis | null>(null)
  const pendingAction = ref<PendingAction | null>(null)
  const loading = ref(false)
  const historyCursor = ref(0)
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

  function init(pid: string) {
    initVersion.value += 1
    const versionSnapshot = initVersion.value
    projectId.value = pid
    messages.value = [
      { role: 'assistant', content: '你好，我是墨舟，你的长篇写作助手。有什么想聊的？' },
    ]
    diagnosis.value = null
    pendingAction.value = null
    loading.value = false
    historyCursor.value = 0
    void loadHistory(pid, versionSnapshot)
    void loadDiagnosis(pid, versionSnapshot)
  }

  async function loadHistory(pidSnapshot = projectId.value, versionSnapshot = initVersion.value) {
    if (!pidSnapshot) return
    try {
      const history = await api.getMessages(pidSnapshot)
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) return
      if (history && history.length > 0) {
        messages.value = history.map((message) => toChatMessage(message))
      }
      historyCursor.value = history?.length || 0
    } catch { /* first visit, no history */ }
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
        pending_action: res.pending_action || null,
        diagnosis: res.project_diagnosis || null,
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
        pending_action: res.pending_action || null,
        diagnosis: res.project_diagnosis || null,
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
        void pollForCompletion(String(res.action_result?.type || ''), pidSnapshot, versionSnapshot)
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

  async function pollForCompletion(
    actionType: string,
    pidSnapshot = projectId.value,
    versionSnapshot = initVersion.value,
  ) {
    if (!pidSnapshot || !actionType) return
    const maxAttempts = 30
    for (let i = 0; i < maxAttempts; i++) {
      if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) break
      await new Promise(r => setTimeout(r, 3000))
      try {
        if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) break
        const history = await api.getMessages(pidSnapshot)
        if (!isActiveSnapshot(pidSnapshot, versionSnapshot)) break
        if (history && history.length > historyCursor.value) {
          const newMessages = history.slice(historyCursor.value)
          for (const message of newMessages) {
            messages.value.push(toChatMessage(message))
          }
          historyCursor.value = history.length
          await loadDiagnosis(pidSnapshot, versionSnapshot)
          if (newMessages.some((message) => isTerminalActionResult(message.action_result || null, actionType))) {
            if (isActiveSnapshot(pidSnapshot, versionSnapshot)) {
              loading.value = false
            }
            break
          }
        }
      } catch { /* retry */ }
    }
  }

  return {
    messages, projectId, diagnosis, pendingAction, loading,
    init, loadDiagnosis, sendText, sendButtonAction, resolveAction,
  }
})
