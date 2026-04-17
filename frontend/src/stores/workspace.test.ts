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
