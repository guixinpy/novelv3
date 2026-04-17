import type { ActionStatus, RefreshTarget, WorkspacePanel } from '../../api/types'

export type WorkspaceTab = {
  id: WorkspacePanel
  label: string
}

export const WORKSPACE_TABS: WorkspaceTab[] = [
  { id: 'overview', label: '概览' },
  { id: 'setup', label: '设定' },
  { id: 'storyline', label: '故事线' },
  { id: 'outline', label: '大纲' },
  { id: 'content', label: '正文' },
  { id: 'topology', label: '拓扑图' },
  { id: 'versions', label: '版本历史' },
  { id: 'preferences', label: '偏好设置' },
]

const PANEL_REFRESH_TARGETS: Record<WorkspacePanel, RefreshTarget[]> = {
  overview: ['project'],
  setup: ['setup'],
  storyline: ['storyline'],
  outline: ['outline'],
  content: ['content'],
  topology: ['topology'],
  versions: ['versions'],
  preferences: ['preferences'],
}

const ACTION_PANEL_MAP: Record<string, WorkspacePanel> = {
  preview_setup: 'setup',
  generate_setup: 'setup',
  preview_storyline: 'storyline',
  generate_storyline: 'storyline',
  preview_outline: 'outline',
  generate_outline: 'outline',
  consistency_deep_check: 'content',
}

const ACTION_REFRESH_TARGETS: Record<string, RefreshTarget[]> = {
  generate_setup: ['setup', 'versions'],
  generate_storyline: ['storyline', 'versions'],
  generate_outline: ['outline', 'versions'],
  consistency_deep_check: ['content'],
}

const ACTION_LABELS: Record<string, string> = {
  preview_setup: '生成设定',
  preview_storyline: '生成故事线',
  preview_outline: '生成大纲',
}

const VERSION_TYPE_LABELS: Record<string, string> = {
  setup: '设定',
  storyline: '故事线',
  outline: '大纲',
  chapter: '章节',
}

const ALL_ACTION_STATUSES = new Set<ActionStatus>([
  'idle',
  'pending',
  'running',
  'completed',
  'success',
  'failed',
  'cancelled',
  'revised',
])

const FINISHED_ACTION_STATUSES = new Set<ActionStatus>([
  'completed',
  'success',
  'failed',
  'cancelled',
  'revised',
])

export function getWorkspaceTabs() {
  return WORKSPACE_TABS
}

export function getWorkspaceTabLabel(panel: WorkspacePanel) {
  return WORKSPACE_TABS.find((tab) => tab.id === panel)?.label ?? '概览'
}

export function getPanelRefreshTargets(panel: WorkspacePanel) {
  return PANEL_REFRESH_TARGETS[panel] || []
}

export function getActionPanel(actionType: string) {
  return ACTION_PANEL_MAP[actionType] ?? null
}

export function getActionRefreshTargets(actionType: string, status: ActionStatus) {
  if (status !== 'completed' && status !== 'success') return []
  return ACTION_REFRESH_TARGETS[actionType] || []
}

export function getActionLabel(actionType: string) {
  return ACTION_LABELS[actionType] ?? '快捷动作'
}

export function getVersionTypeLabel(type: string) {
  return VERSION_TYPE_LABELS[type] ?? type
}

export function getVersionRefreshTarget(nodeType?: string): RefreshTarget | null {
  if (nodeType === 'setup') return 'setup'
  if (nodeType === 'storyline') return 'storyline'
  if (nodeType === 'outline') return 'outline'
  if (nodeType === 'chapter') return 'content'
  return null
}

export function normalizeActionStatus(status: unknown): ActionStatus | null {
  if (typeof status !== 'string') return null
  if (!ALL_ACTION_STATUSES.has(status as ActionStatus)) return null
  return status as ActionStatus
}

export function isFinishedActionStatus(status: ActionStatus | null): status is ActionStatus {
  return status !== null && FINISHED_ACTION_STATUSES.has(status)
}
