import { describe, expect, it } from 'vitest'
import {
  RECOVERY_AGENT_RUN_ACTION_DESCRIPTORS,
  RECOVERY_AGENT_RUN_ACTION_TYPES,
  type RecoveryAgentRunActionType,
  buildAgentRunExecutionFeedback,
  buildRecommendedFollowupExecutionFeedback,
} from './recoveryAgentRunProjection'

function buildRecoveryView(
  type: RecoveryAgentRunActionType,
  status: string,
  data: Record<string, unknown>,
) {
  return RECOVERY_AGENT_RUN_ACTION_DESCRIPTORS[type].buildView({ type, status, data }, status)
}

describe('recoveryAgentRunProjection', () => {
  it('exposes recovery action descriptors and feedback builders', () => {
    expect(RECOVERY_AGENT_RUN_ACTION_TYPES).toEqual([
      'plan_recovery_tools',
      'plan_recommended_followups',
      'ui_recovery_execute',
      'ui_recommended_followup_execute',
    ])
    for (const type of RECOVERY_AGENT_RUN_ACTION_TYPES) {
      expect(RECOVERY_AGENT_RUN_ACTION_DESCRIPTORS[type]?.type).toBe(type)
      expect(typeof RECOVERY_AGENT_RUN_ACTION_DESCRIPTORS[type]?.buildView).toBe('function')
    }
    expect(typeof buildAgentRunExecutionFeedback).toBe('function')
    expect(typeof buildRecommendedFollowupExecutionFeedback).toBe('function')
  })

  it('builds fallback views for recovery preview action results', () => {
    const view = buildRecoveryView('plan_recovery_tools', 'success', {
      source_run_id: 'source-run-123456',
      agent_profile: 'drafting_worker',
      agent_profile_definition: {
        version: 'phase212.agent_profile_definition.v1',
        status: 'known',
        profile: 'drafting_worker',
        display_name: '创作执行者',
        role: 'worker',
        tier: 'worker',
        delegation_allowed: false,
        delegate_to_profiles: [],
        source: 'planner_trace',
      },
      agent_tool_discovery: {
        version: 'phase210.agent_tool_discovery_projection.v1',
        status: 'applied',
        scope_applied: true,
        scope_source: 'agent_profile',
        requested_profile: 'drafting_worker',
        effective_profile: 'drafting_worker',
        visible_tool_count: 12,
        filtered_by_profile_count: 7,
        filter_stages: ['profile'],
      },
      recovery: { status: 'recommended' },
      execution_policy: { status: 'ready' },
      tools: [{ tool_name: 'prepare_generate_chapter_execution' }],
      route_decision: {
        selected_route: 'recover_blocked_run',
        reason_code: 'recoverable_run_found',
      },
    })

    expect(view?.label).toBe('恢复预览已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '来源运行', value: 'source-r' })
    expect(view?.detail_items).toContainEqual({ label: '继续路由', value: '恢复阻塞运行' })
    expect(view?.detail_items).toContainEqual({ label: '路由原因', value: '发现可恢复运行' })
    expect(view?.detail_items).toContainEqual({ label: '恢复状态', value: '建议恢复' })
    expect(view?.detail_items).toContainEqual({ label: '执行策略', value: '可执行' })
    expect(view?.detail_items).toContainEqual({ label: '恢复工具', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: 'Agent 身份', value: '创作执行者' })
    expect(view?.detail_items).toContainEqual({ label: 'Agent 角色', value: 'worker' })
    expect(view?.detail_items).toContainEqual({ label: '编排层级', value: 'worker' })
    expect(view?.detail_items).toContainEqual({ label: '委派', value: '不可委派' })
    expect(view?.detail_items).toContainEqual({ label: '工具面', value: '已按身份收窄' })
    expect(view?.detail_items).toContainEqual({ label: '可见工具', value: '12 个' })
    expect(view?.detail_items).toContainEqual({ label: '已过滤', value: '7 个' })
  })

  it('builds fallback views for recommended followup preview action results', () => {
    const view = buildRecoveryView('plan_recommended_followups', 'success', {
      status: 'completed',
      source_run_id: 'source-run-abcdef',
      recommended_followups: {
        status: 'recommended',
        post_approval_continuation_tools: [
          { tool_name: 'summarize_longform_context', params: { chapter_index: 3 } },
          { tool_name: 'preflight_writing', params: { chapter_index: 3 } },
        ],
        provenance_write_tools: [{ tool_name: 'repair_longform_maintenance', params: {} }],
      },
      tools: [{ tool_name: 'inspect_agent_memory_route' }],
      worker_dispatch: {
        summary: {
          workers: 1,
          planned_tasks: 1,
          blocked_tasks: 0,
          issues: 0,
        },
        route_registry: {
          status: 'passed',
          summary: {
            routes: 35,
            ready_routes: 35,
            unrouted_allowed_tools: 0,
            issues: 0,
          },
        },
      },
      route_decision: {
        selected_route: 'recommended_followups',
        reason_code: 'recommended_followups_found',
      },
    })

    expect(view?.label).toBe('推荐后继预览已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '来源运行', value: 'source-r' })
    expect(view?.detail_items).toContainEqual({ label: '继续路由', value: '推荐后继' })
    expect(view?.detail_items).toContainEqual({ label: '路由原因', value: '发现上一轮推荐后继' })
    expect(view?.detail_items).toContainEqual({ label: '推荐状态', value: '已推荐' })
    expect(view?.detail_items).toContainEqual({ label: '自动后继', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: 'Worker 分派', value: '1 个 worker' })
    expect(view?.detail_items).toContainEqual({ label: '分派任务', value: '1 个任务' })
    expect(view?.detail_items).toContainEqual({ label: '路由审计', value: '通过' })
    expect(view?.detail_items).toContainEqual({ label: '未路由工具', value: '0 个' })
    expect(view?.detail_items).toContainEqual({ label: '写后续跑', value: '2 个工具' })
    expect(view?.detail_items).toContainEqual({ label: '需确认修复', value: '1 个' })
    expect(JSON.stringify(view)).not.toContain('repair_longform_maintenance')
  })

  it('builds fallback views with declared delegate profile targets', () => {
    const view = buildRecoveryView('plan_recovery_tools', 'success', {
      agent_profile: 'orchestrator',
      agent_profile_definition: {
        version: 'phase212.agent_profile_definition.v1',
        status: 'known',
        profile: 'orchestrator',
        display_name: '编排主控',
        role: 'orchestrator',
        tier: 'reasoning',
        delegation_allowed: true,
        delegate_to_profiles: [
          'drafting_worker',
          'reviewer_worker',
          'world_model_worker',
          'recovery_worker',
        ],
        source: 'planner_trace',
      },
    })

    expect(view?.detail_items).toContainEqual({ label: 'Agent 身份', value: '编排主控' })
    expect(view?.detail_items).toContainEqual({ label: '委派', value: '可委派' })
    expect(view?.detail_items).toContainEqual({ label: '可委派目标', value: '4 个声明' })
  })

  it('builds fallback views with profile policy audit status', () => {
    const view = buildRecoveryView('plan_recovery_tools', 'success', {
      agent_profile: 'orchestrator',
      agent_profile_policy_audit: {
        version: 'phase215.agent_profile_policy_audit.v1',
        status: 'needs_attention',
        summary: { issues: 2, delegate_edges: 4 },
        issues: [
          {
            code: 'delegate_target_missing_definition',
            profile: 'orchestrator',
            target: 'ghost_worker',
          },
        ],
      },
    })

    expect(view?.detail_items).toContainEqual({ label: 'Agent 身份', value: '编排主控' })
    expect(view?.detail_items).toContainEqual({ label: '策略审计', value: '需关注：2 个问题' })
    expect(JSON.stringify(view?.detail_items)).not.toContain('delegate_target_missing_definition')
    expect(JSON.stringify(view?.detail_items)).not.toContain('ghost_worker')
  })

  it('builds fallback views for recovery execution action results', () => {
    const view = buildRecoveryView('ui_recovery_execute', 'running', { agent_run_id: 'run-running' })

    expect(view?.label).toBe('恢复执行中')
    expect(view?.variant).toBe('neutral')
    expect(view?.detail_items).toContainEqual({ label: '运行 ID', value: 'run-running' })
  })

  it('builds recovery execution feedback without leaking plan hash', () => {
    const message = buildAgentRunExecutionFeedback({
      id: 'run-executed',
      project_id: 'project-1',
      goal: '执行恢复计划',
      status: 'success',
      entrypoint: 'ui_recovery_execute',
      input: { recovery_plan_hash: 'plan-hash-1' },
      output: null,
      error: null,
      agent_profile: 'recovery_worker',
      agent_profile_definition: {
        version: 'phase212.agent_profile_definition.v1',
        status: 'known',
        profile: 'recovery_worker',
        display_name: '恢复维护者',
        role: 'worker',
        tier: 'worker',
        delegation_allowed: false,
        delegate_to_profiles: [],
        source: 'planner_trace',
      },
      agent_tool_discovery: {
        version: 'phase210.agent_tool_discovery_projection.v1',
        status: 'applied',
        scope_applied: true,
        scope_source: 'agent_profile',
        requested_profile: 'recovery_worker',
        effective_profile: 'recovery_worker',
        visible_tool_count: 9,
        filtered_by_profile_count: 10,
        filter_stages: ['profile'],
      },
      agent_command_contracts: {
        source: 'planner_trace.agent_health_projection.command_contracts',
        summary: {
          agent_control_commands: 2,
          gap_count: 0,
        },
      },
      agent_control_plane_readiness: {
        source: 'planner_trace.agent_health_projection.control_plane_readiness',
        status: 'ready',
        version: 'phase46.agent_control_plane_readiness.v1',
        summary: {
          tool_gap_count: 0,
          command_gap_count: 0,
          total_gap_count: 0,
        },
        recommended_next_tools: ['inspect_agent_health_projection'],
      },
      steps: [],
    })

    expect(message.role).toBe('system')
    expect(message.content).toContain('恢复执行已创建')
    expect(message.action_result?.type).toBe('ui_recovery_execute')
    expect(message.action_result?.data).toEqual({ agent_run_id: 'run-executed' })
    expect(message.action_result_view?.label).toBe('恢复执行已完成')
    expect(message.action_result_view.detail_items).toContainEqual({ label: 'Agent 身份', value: '恢复维护者' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: 'Agent 角色', value: 'worker' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '编排层级', value: 'worker' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '委派', value: '不可委派' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '工具面', value: '已按身份收窄' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '可见工具', value: '9 个' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '已过滤', value: '10 个' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '命令契约', value: '已投影' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '控制命令', value: '2 个' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '契约缺口', value: '0 个' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '控制平面', value: '可继续编排' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '控制面缺口', value: '0 个' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '工具缺口', value: '0 个' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '命令缺口', value: '0 个' })
    expect(message.action_result_view.detail_items).toContainEqual({ label: '建议检查', value: '1 项' })
    expect(message.meta?.agent_run_id).toBe('run-executed')
    expect(JSON.stringify(message)).not.toContain('plan-hash-1')
    expect(JSON.stringify(message)).not.toContain('planner_trace.agent_health_projection.command_contracts')
    expect(JSON.stringify(message)).not.toContain('planner_trace.agent_health_projection.control_plane_readiness')
    expect(JSON.stringify(message)).not.toContain('inspect_agent_health_projection')
  })

  it('builds failed recovery execution feedback with an error summary', () => {
    const message = buildAgentRunExecutionFeedback({
      id: 'run-failed',
      project_id: 'project-1',
      goal: '执行恢复计划',
      status: 'failed',
      entrypoint: 'ui_recovery_execute',
      input: { recovery_plan_hash: 'plan-hash-2' },
      output: null,
      error: ' 工具执行失败：缺少章节上下文 ',
      steps: [],
    })

    expect(message.action_result_view.label).toBe('恢复执行失败')
    expect(message.action_result_view.variant).toBe('error')
    expect(message.action_result_view.detail_items).toContainEqual({
      label: '错误摘要',
      value: '工具执行失败：缺少章节上下文',
    })
    expect(JSON.stringify(message)).not.toContain('plan-hash-2')
  })
})
