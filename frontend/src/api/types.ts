export type DialogState = 'IDLE' | 'CHATTING' | 'PENDING_ACTION' | 'RUNNING' | string
export type ActionStatus = 'idle' | 'pending' | 'running' | 'completed' | 'success' | 'failed' | 'cancelled' | string
export type RefreshTarget = 'setup' | 'storyline' | 'outline' | 'content' | 'versions' | string

export interface PendingAction {
  id: string
  type: string
  description: string
  params: Record<string, unknown>
  requires_confirmation: boolean
}

export interface ActiveAction {
  type: string
  status: ActionStatus
  target_panel: string | null
  reason: string
}

export interface UiHint {
  dialog_state: DialogState
  active_action: ActiveAction
}

export interface ProjectDiagnosis {
  missing_items: string[]
  completed_items: string[]
  suggested_next_step: string | null
}

export interface ChatRequest {
  project_id: string
  input_type: 'text' | 'button'
  text?: string
  action_type?: string
  params?: Record<string, unknown>
}

export interface ChatResponse {
  message: string
  pending_action: PendingAction | null
  ui_hint: UiHint | null
  refresh_targets: RefreshTarget[]
  project_diagnosis: ProjectDiagnosis
}

export interface ResolveActionRequest {
  action_id: string
  decision: 'confirm' | 'cancel' | 'revise'
  comment?: string
}

export interface ResolveActionResult extends Record<string, unknown> {
  type: string
  status: string
  data: Record<string, unknown>
}

export interface ResolveActionResponse {
  dialog_state: DialogState
  action_result: ResolveActionResult
  message: string
  ui_hint: UiHint | null
  refresh_targets: RefreshTarget[]
}

export interface BackgroundTaskResponse {
  task_id: string
  task_type: string
  status: string
  result: any
  error: string | null
  ui_hint: UiHint
  refresh_targets: RefreshTarget[]
  created_at: string | null
  started_at: string | null
  finished_at: string | null
}

export interface ChatHistoryMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  action_result?: Record<string, unknown> | null
  created_at?: string | null
}
