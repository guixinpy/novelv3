import { describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { applyUiHint, applyUserPanel, createWorkspaceState, settleUiAction, useWorkspaceStore } from './workspace'
import type { WorkspaceState } from './workspace'

describe('workspace orchestration', () => {
  it('applyUserPanel(state, panel, reason) 仅更新用户选择和原因，不自动锁定，且返回新对象', () => {
    const state = createWorkspaceState()

    const next = applyUserPanel(state, 'outline', 'user-click-tab')

    expect(next).not.toBe(state)
    expect(next.panel).toBe('outline')
    expect(next.lastUserPanel).toBe('outline')
    expect(next.reason).toBe('user-click-tab')
    expect(next.source).toBe('user')
    expect(next.mode).toBe('auto')
    expect(next.lockedPanel).toBe(null)
    expect(state.panel).toBe('overview')
  })

  it('auto 模式下 ai target -> panel 跳转到 outline，source=ai', () => {
    const state = createWorkspaceState()

    const next = applyUiHint(state, {
      dialog_state: 'PENDING_ACTION',
      active_action: {
        type: 'generate_outline',
        status: 'pending',
        target_panel: 'outline',
        reason: '等待用户确认',
      },
    })

    expect(next).not.toBe(state)
    expect(next.panel).toBe('outline')
    expect(next.source).toBe('ai')
    expect(next.mode).toBe('auto')
    expect(next.reason).toBe('等待用户确认')
  })

  it('locked 模式下 task completed -> 回 lockedPanel=versions', () => {
    const state = createWorkspaceState()

    const lockedState: WorkspaceState = {
      ...state,
      mode: 'locked',
      panel: 'outline',
      lockedPanel: 'versions',
      source: 'ai',
      reason: '后台任务运行中',
      returnPanel: 'outline',
    }

    const next = settleUiAction(lockedState, 'completed')

    expect(next).not.toBe(lockedState)
    expect(next.panel).toBe('versions')
    expect(next.lockedPanel).toBe('versions')
    expect(next.mode).toBe('locked')
    expect(next.source).toBe('system')
  })

  it('locked 模式下 cancelled/revised -> 回 lockedPanel=versions，避免借道悬挂', () => {
    const state = createWorkspaceState()

    for (const status of ['cancelled', 'revised'] as const) {
      const lockedState: WorkspaceState = {
        ...state,
        mode: 'locked',
        panel: 'outline',
        lockedPanel: 'versions',
        source: 'ai',
        reason: '待确认动作结束',
        returnPanel: 'outline',
      }

      const next = settleUiAction(lockedState, status)

      expect(next).not.toBe(lockedState)
      expect(next.panel).toBe('versions')
      expect(next.lockedPanel).toBe('versions')
      expect(next.mode).toBe('locked')
      expect(next.source).toBe('system')
      expect(next.returnPanel).toBe(null)
    }
  })

  it('locked 模式下 action failed -> 停留失败面板 content，不回 lockedPanel', () => {
    const state = createWorkspaceState()

    const lockedState: WorkspaceState = {
      ...state,
      mode: 'locked',
      panel: 'versions',
      lockedPanel: 'versions',
      source: 'user',
      reason: '保持查看版本历史',
      returnPanel: null,
    }

    const next = applyUiHint(lockedState, {
      dialog_state: 'RUNNING',
      active_action: {
        type: 'generate_chapter',
        status: 'failed',
        target_panel: 'content',
        reason: '正文生成失败',
      },
    })

    expect(next).not.toBe(lockedState)
    expect(next.panel).toBe('content')
    expect(next.lockedPanel).toBe('versions')
    expect(next.mode).toBe('locked')
    expect(next.source).toBe('ai')
    expect(next.reason).toBe('正文生成失败')
    expect(next.returnPanel).toBe(null)
  })

  it('toggleLock() 解锁时清理 stale lockedPanel 和 returnPanel，但保留当前 panel', () => {
    setActivePinia(createPinia())
    const store = useWorkspaceStore()

    store.applyUserPanel('versions', 'user-open-versions')
    store.toggleLock()
    store.applyUiHint({
      dialog_state: 'RUNNING',
      active_action: {
        type: 'generate_chapter',
        status: 'running',
        target_panel: 'content',
        reason: '正在生成正文',
      },
    })

    store.toggleLock()

    expect(store.mode).toBe('auto')
    expect(store.panel).toBe('content')
    expect(store.lockedPanel).toBe(null)
    expect(store.returnPanel).toBe(null)
    expect(store.source).toBe('user')
    expect(store.reason).toBe('toggle-lock')
  })

  it('store reset() 会清理跨项目残留状态', () => {
    setActivePinia(createPinia())
    const store = useWorkspaceStore()

    store.applyUserPanel('outline', 'user-click-tab')
    store.toggleLock()
    store.applyUiHint({
      dialog_state: 'PENDING_ACTION',
      active_action: {
        type: 'generate_outline',
        status: 'pending',
        target_panel: 'outline',
        reason: '等待用户确认',
      },
    })

    store.reset()

    expect(store.mode).toBe('auto')
    expect(store.panel).toBe('overview')
    expect(store.lockedPanel).toBe(null)
    expect(store.source).toBe('system')
    expect(store.reason).toBe('')
    expect(store.lastUserPanel).toBe(null)
    expect(store.returnPanel).toBe(null)
  })
})
