import { describe, expect, it } from 'vitest'
import { applyUiHint, createWorkspaceState, settleUiAction } from './workspace'

describe('workspace orchestration', () => {
  it('auto 模式下 ai target -> panel 跳转到 outline，source=ai', () => {
    const state = createWorkspaceState()

    applyUiHint(state, {
      dialog_state: 'PENDING_ACTION',
      active_action: {
        type: 'generate_outline',
        status: 'pending',
        target_panel: 'outline',
        reason: '等待用户确认',
      },
    })

    expect(state.panel).toBe('outline')
    expect(state.source).toBe('ai')
    expect(state.mode).toBe('auto')
  })

  it('locked 模式下 task completed -> 回 lockedPanel=versions', () => {
    const state = createWorkspaceState()

    state.mode = 'locked'
    state.panel = 'outline'
    state.lockedPanel = 'versions'
    state.source = 'user'

    settleUiAction(state, {
      type: 'generate_outline',
      status: 'completed',
      target_panel: 'outline',
      reason: '后台任务状态更新',
    })

    expect(state.panel).toBe('versions')
    expect(state.mode).toBe('locked')
    expect(state.source).toBe('user')
  })
})
