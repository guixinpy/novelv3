import { describe, expect, it } from 'vitest'
import {
  ROUTE_OPT_IN_AGENT_RUN_ACTION_DESCRIPTORS,
  ROUTE_OPT_IN_AGENT_RUN_ACTION_TYPES,
  type RouteOptInAgentRunActionType,
} from './routeOptInAgentRunProjection'

function buildRouteOptInView(
  type: RouteOptInAgentRunActionType,
  status: string,
  data: Record<string, unknown>,
) {
  return ROUTE_OPT_IN_AGENT_RUN_ACTION_DESCRIPTORS[type].buildView({ type, status, data }, status)
}

describe('routeOptInAgentRunProjection', () => {
  it('exposes route opt-in action descriptors', () => {
    expect(ROUTE_OPT_IN_AGENT_RUN_ACTION_TYPES).toEqual([
      'prepare_route_upgrade_contract',
      'preview_pending_action_route_approval_opt_in_apply_contract',
      'apply_pending_action_route_approval_opt_in',
    ])
    for (const type of ROUTE_OPT_IN_AGENT_RUN_ACTION_TYPES) {
      expect(ROUTE_OPT_IN_AGENT_RUN_ACTION_DESCRIPTORS[type]?.type).toBe(type)
      expect(typeof ROUTE_OPT_IN_AGENT_RUN_ACTION_DESCRIPTORS[type]?.buildView).toBe('function')
    }
  })

  it('builds route opt-in contract preview fallback views without leaking approval hashes', () => {
    const view = buildRouteOptInView('preview_pending_action_route_approval_opt_in_apply_contract', 'success', {
      status: 'requires_confirmation',
      approval_contract_hash: 'approval:secret',
      approval_contract: { approval: { approval_contract_hash: 'approval:secret' } },
      recommended_next_tools: ['apply_pending_action_route_approval_opt_in'],
    })

    expect(view?.label).toBe('路由升级契约待确认')
    expect(view?.variant).toBe('neutral')
    expect(view?.detail_items).toContainEqual({ label: '契约状态', value: '等待确认' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
    expect(JSON.stringify(view)).not.toContain('approval:secret')
  })

  it('builds route opt-in apply fallback views without leaking approval hashes', () => {
    const view = buildRouteOptInView('apply_pending_action_route_approval_opt_in', 'success', {
      status: 'success',
      reason: 'route_opt_in_apply_completed',
      write_performed: true,
      approval_verification: {
        drift: { expected_approval_contract_hash: 'approval:secret' },
      },
      recommended_next_tools: ['inspect_agent_dialog_control_plane_projection'],
    })

    expect(view?.label).toBe('路由升级已应用')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '应用状态', value: '成功' })
    expect(view?.detail_items).toContainEqual({ label: '写入结果', value: '已写入' })
    expect(view?.detail_items).toContainEqual({ label: '原因', value: 'route_opt_in_apply_completed' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
    expect(JSON.stringify(view)).not.toContain('approval:secret')
  })
})
