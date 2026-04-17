import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api } from '../api/client'

export interface PendingAction {
  id: string
  type: string
  description: string
  params: Record<string, any>
  requires_confirmation: boolean
}

export interface Diagnosis {
  missing_items: string[]
  completed_items: string[]
  suggested_next_step: string | null
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  pending_action?: PendingAction | null
  diagnosis?: Diagnosis | null
  action_result?: Record<string, any> | null
}

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const projectId = ref<string>('')
  const diagnosis = ref<Diagnosis | null>(null)
  const pendingAction = ref<PendingAction | null>(null)
  const loading = ref(false)

  function init(pid: string) {
    projectId.value = pid
    messages.value = [
      { role: 'assistant', content: '你好，我是墨舟，你的长篇写作助手。有什么想聊的？' },
    ]
    pendingAction.value = null
    loadDiagnosis()
  }

  async function loadDiagnosis() {
    if (!projectId.value) return
    try {
      diagnosis.value = await api.getDiagnosis(projectId.value)
    } catch { /* ignore */ }
  }

  async function sendText(text: string) {
    if (loading.value || !text.trim()) return
    messages.value.push({ role: 'user', content: text })
    loading.value = true
    try {
      const res = await api.sendChat({
        project_id: projectId.value,
        input_type: 'text',
        text,
      })
      const msg: ChatMessage = {
        role: 'assistant',
        content: res.message,
        pending_action: res.pending_action || null,
        diagnosis: res.project_diagnosis || null,
      }
      messages.value.push(msg)
      if (res.pending_action) pendingAction.value = res.pending_action
      if (res.project_diagnosis) diagnosis.value = res.project_diagnosis
    } catch (e: any) {
      messages.value.push({ role: 'assistant', content: `出错了：${e.message}` })
    } finally {
      loading.value = false
    }
  }

  async function sendButtonAction(actionType: string) {
    if (loading.value) return
    loading.value = true
    try {
      const res = await api.sendChat({
        project_id: projectId.value,
        input_type: 'button',
        action_type: actionType,
        params: { project_id: projectId.value },
      })
      const msg: ChatMessage = {
        role: 'assistant',
        content: res.message,
        pending_action: res.pending_action || null,
        diagnosis: res.project_diagnosis || null,
      }
      messages.value.push(msg)
      if (res.pending_action) pendingAction.value = res.pending_action
      if (res.project_diagnosis) diagnosis.value = res.project_diagnosis
    } catch (e: any) {
      messages.value.push({ role: 'assistant', content: `出错了：${e.message}` })
    } finally {
      loading.value = false
    }
  }

  async function resolveAction(decision: 'confirm' | 'cancel' | 'revise', comment = '') {
    if (!pendingAction.value || loading.value) return
    loading.value = true
    const actionId = pendingAction.value.id
    try {
      const res = await api.resolveAction({ action_id: actionId, decision, comment })
      pendingAction.value = null
      const msg: ChatMessage = {
        role: 'system',
        content: res.message,
        action_result: res.action_result || null,
      }
      messages.value.push(msg)
      await loadDiagnosis()
    } catch (e: any) {
      messages.value.push({ role: 'assistant', content: `操作失败：${e.message}` })
    } finally {
      loading.value = false
    }
  }

  return {
    messages, projectId, diagnosis, pendingAction, loading,
    init, loadDiagnosis, sendText, sendButtonAction, resolveAction,
  }
})
