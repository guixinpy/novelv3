import { describe, expect, it } from 'vitest'
import {
  buildAgentRunActionResultView,
  buildAgentRunExecutionFeedback,
  getAgentRunActionDescriptor,
  getAgentRunIdFromMessage,
  isAgentRunActionType,
} from './agentRunProjection'
import {
  LONGFORM_AGENT_RUN_ACTION_DESCRIPTORS,
  LONGFORM_AGENT_RUN_ACTION_TYPES,
} from './longformAgentRunProjection'

describe('agentRunProjection', () => {
  it('exposes longform action descriptors from a dedicated module', () => {
    expect(LONGFORM_AGENT_RUN_ACTION_TYPES).toEqual([
      'inspect_longform_chapter_batch',
      'execute_longform_chapter_batch_preflight',
      'prepare_longform_chapter_batch_execution',
      'execute_longform_chapter_batch',
      'review_longform_chapter_batch_execution',
      'route_longform_chapter_batch_after_review',
    ])
    for (const type of LONGFORM_AGENT_RUN_ACTION_TYPES) {
      expect(LONGFORM_AGENT_RUN_ACTION_DESCRIPTORS[type]?.type).toBe(type)
      expect(typeof LONGFORM_AGENT_RUN_ACTION_DESCRIPTORS[type]?.buildView).toBe('function')
    }
  })

  it('extracts run ids only from supported agent run action messages', () => {
    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'plan_recovery_tools',
        status: 'success',
        data: { agent_run_id: 'run-preview' },
      },
    })).toBe('run-preview')

    expect(getAgentRunIdFromMessage({
      action_result_view: {
        type: 'ui_recovery_execute',
        status: 'success',
        label: '恢复执行已完成',
        variant: 'success',
      },
      meta: { agent_run_id: 'run-executed' },
    })).toBe('run-executed')

    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'unknown_tool',
        status: 'success',
        data: { agent_run_id: 'run-hidden' },
      },
    })).toBe('')
  })

  it('recognizes supported agent run action types', () => {
    expect(isAgentRunActionType('plan_recovery_tools')).toBe(true)
    expect(isAgentRunActionType('ui_recovery_execute')).toBe(true)
    expect(isAgentRunActionType('inspect_agent_trace_audit')).toBe(true)
    expect(isAgentRunActionType('prepare_route_upgrade_contract')).toBe(true)
    expect(isAgentRunActionType('inspect_longform_chapter_batch')).toBe(true)
    expect(isAgentRunActionType('execute_longform_chapter_batch_preflight')).toBe(true)
    expect(isAgentRunActionType('prepare_longform_chapter_batch_execution')).toBe(true)
    expect(isAgentRunActionType('execute_longform_chapter_batch')).toBe(true)
    expect(isAgentRunActionType('review_longform_chapter_batch_execution')).toBe(true)
    expect(isAgentRunActionType('route_longform_chapter_batch_after_review')).toBe(true)
    expect(isAgentRunActionType('preview_pending_action_route_approval_opt_in_apply_contract')).toBe(true)
    expect(isAgentRunActionType('apply_pending_action_route_approval_opt_in')).toBe(true)
    expect(isAgentRunActionType('generate_chapter')).toBe(false)
  })

  it('exposes registered agent run action descriptors', () => {
    expect(getAgentRunActionDescriptor('plan_recovery_tools')?.type).toBe('plan_recovery_tools')
    expect(getAgentRunActionDescriptor('ui_recovery_execute')?.type).toBe('ui_recovery_execute')
    expect(getAgentRunActionDescriptor('inspect_agent_trace_audit')?.type).toBe('inspect_agent_trace_audit')
    expect(getAgentRunActionDescriptor('prepare_route_upgrade_contract')?.type).toBe('prepare_route_upgrade_contract')
    expect(getAgentRunActionDescriptor('inspect_longform_chapter_batch')?.type).toBe('inspect_longform_chapter_batch')
    expect(getAgentRunActionDescriptor('execute_longform_chapter_batch_preflight')?.type).toBe('execute_longform_chapter_batch_preflight')
    expect(getAgentRunActionDescriptor('prepare_longform_chapter_batch_execution')?.type).toBe('prepare_longform_chapter_batch_execution')
    expect(getAgentRunActionDescriptor('execute_longform_chapter_batch')?.type).toBe('execute_longform_chapter_batch')
    expect(getAgentRunActionDescriptor('review_longform_chapter_batch_execution')?.type).toBe('review_longform_chapter_batch_execution')
    expect(getAgentRunActionDescriptor('route_longform_chapter_batch_after_review')?.type).toBe('route_longform_chapter_batch_after_review')
    expect(getAgentRunActionDescriptor('preview_pending_action_route_approval_opt_in_apply_contract')?.type).toBe('preview_pending_action_route_approval_opt_in_apply_contract')
    expect(getAgentRunActionDescriptor('apply_pending_action_route_approval_opt_in')?.type).toBe('apply_pending_action_route_approval_opt_in')
    expect(getAgentRunActionDescriptor('generate_chapter')).toBeNull()
  })

  it('extracts nested run ids from trace audit action results', () => {
    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'inspect_agent_trace_audit',
        status: 'success',
        data: { run: { id: 'run-audit-1' } },
      },
    })).toBe('run-audit-1')
  })

  it('extracts run ids from longform batch inspection action results', () => {
    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'inspect_longform_chapter_batch',
        status: 'success',
        data: { agent_run_id: 'run-batch-1' },
      },
    })).toBe('run-batch-1')
  })

  it('extracts run ids from longform preflight action results', () => {
    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'execute_longform_chapter_batch_preflight',
        status: 'success',
        data: { agent_run_id: 'run-preflight-1' },
      },
    })).toBe('run-preflight-1')
  })

  it('extracts run ids from longform prepare action results', () => {
    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'prepare_longform_chapter_batch_execution',
        status: 'success',
        data: { agent_run_id: 'run-prepare-1' },
      },
    })).toBe('run-prepare-1')
  })

  it('extracts run ids from longform execute action results', () => {
    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'execute_longform_chapter_batch',
        status: 'success',
        data: { agent_run_id: 'run-execute-1' },
      },
    })).toBe('run-execute-1')
  })

  it('extracts run ids from longform review action results', () => {
    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'review_longform_chapter_batch_execution',
        status: 'success',
        data: { agent_run_id: 'run-review-1' },
      },
    })).toBe('run-review-1')
  })

  it('extracts run ids from longform route action results', () => {
    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'route_longform_chapter_batch_after_review',
        status: 'success',
        data: { agent_run_id: 'run-route-1' },
      },
    })).toBe('run-route-1')
  })

  it('builds fallback views for recovery preview action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'plan_recovery_tools',
      status: 'success',
      data: {
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
      },
    })

    expect(view?.label).toBe('恢复预览已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '来源运行', value: 'source-r' })
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

  it('builds fallback views with declared delegate profile targets', () => {
    const view = buildAgentRunActionResultView({
      type: 'plan_recovery_tools',
      status: 'success',
      data: {
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
      },
    })

    expect(view?.detail_items).toContainEqual({ label: 'Agent 身份', value: '编排主控' })
    expect(view?.detail_items).toContainEqual({ label: '委派', value: '可委派' })
    expect(view?.detail_items).toContainEqual({ label: '可委派目标', value: '4 个声明' })
  })

  it('does not build fallback views for unknown action results', () => {
    expect(buildAgentRunActionResultView({
      type: 'generate_chapter',
      status: 'success',
      data: { agent_run_id: 'run-hidden' },
    })).toBeNull()
  })

  it('builds fallback views for recovery execution action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'ui_recovery_execute',
      status: 'running',
      data: { agent_run_id: 'run-running' },
    })

    expect(view?.label).toBe('恢复执行中')
    expect(view?.variant).toBe('neutral')
    expect(view?.detail_items).toContainEqual({ label: '运行 ID', value: 'run-running' })
  })

  it('builds fallback views for trace audit action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'inspect_agent_trace_audit',
      status: 'success',
      data: {
        run: { id: 'run-audit-1', status: 'failed' },
        audit: { status: 'failed', step_count: 3, trace_count: 2 },
        failure: { reason_code: 'tool_failed' },
        recommended_actions: [{ tool_name: 'plan_recovery_tools' }],
      },
    })

    expect(view?.label).toBe('Trace 审计已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '运行状态', value: '失败' })
    expect(view?.detail_items).toContainEqual({ label: '工具步骤', value: '3 个' })
    expect(view?.detail_items).toContainEqual({ label: 'Trace', value: '2 条' })
    expect(view?.detail_items).toContainEqual({ label: '失败原因', value: 'tool_failed' })
    expect(view?.detail_items).toContainEqual({ label: '建议动作', value: '1 个' })
  })

  it('builds route opt-in contract preview fallback views without leaking approval hashes', () => {
    const view = buildAgentRunActionResultView({
      type: 'preview_pending_action_route_approval_opt_in_apply_contract',
      status: 'success',
      data: {
        status: 'requires_confirmation',
        approval_contract_hash: 'approval:secret',
        approval_contract: { approval: { approval_contract_hash: 'approval:secret' } },
        recommended_next_tools: ['apply_pending_action_route_approval_opt_in'],
      },
    })

    expect(view?.label).toBe('路由升级契约待确认')
    expect(view?.variant).toBe('neutral')
    expect(view?.detail_items).toContainEqual({ label: '契约状态', value: '等待确认' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
    expect(JSON.stringify(view)).not.toContain('approval:secret')
  })

  it('builds route opt-in apply fallback views without leaking approval hashes', () => {
    const view = buildAgentRunActionResultView({
      type: 'apply_pending_action_route_approval_opt_in',
      status: 'success',
      data: {
        status: 'success',
        reason: 'route_opt_in_apply_completed',
        write_performed: true,
        approval_verification: {
          drift: { expected_approval_contract_hash: 'approval:secret' },
        },
        recommended_next_tools: ['inspect_agent_dialog_control_plane_projection'],
      },
    })

    expect(view?.label).toBe('路由升级已应用')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '应用状态', value: '成功' })
    expect(view?.detail_items).toContainEqual({ label: '写入结果', value: '已写入' })
    expect(view?.detail_items).toContainEqual({ label: '原因', value: 'route_opt_in_apply_completed' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
    expect(JSON.stringify(view)).not.toContain('approval:secret')
  })

  it('builds fallback views for longform batch inspection action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'inspect_longform_chapter_batch',
      status: 'success',
      data: {
        status: 'completed',
        summary: { total: 3, returned: 2, selected: true },
        queue: { depth: 2, active: 1, terminal: 1 },
        selected_task: {
          status: 'pending',
          chapter_range: { start: 21, end: 23 },
          execution_readiness: { status: 'materialized_only' },
        },
      },
    })

    expect(view?.label).toBe('长篇批次检查已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '队列深度', value: '2 个' })
    expect(view?.detail_items).toContainEqual({ label: '活跃任务', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '命中任务', value: '是' })
    expect(view?.detail_items).toContainEqual({ label: '章节范围', value: '第21-23章' })
    expect(view?.detail_items).toContainEqual({ label: '执行状态', value: '已物化，等待执行工具' })
  })

  it('builds not-found fallback views for longform batch inspection action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'inspect_longform_chapter_batch',
      status: 'success',
      data: {
        status: 'not_found',
        summary: { total: 0, returned: 0, selected: false },
        selected_task: null,
      },
    })

    expect(view?.label).toBe('长篇批次未找到')
    expect(view?.variant).toBe('neutral')
    expect(view?.detail_items).toContainEqual({ label: '命中任务', value: '否' })
  })

  it('builds ready fallback views for longform preflight action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'execute_longform_chapter_batch_preflight',
      status: 'success',
      data: {
        status: 'ready',
        canonical_execution_plan: { chapters_to_run: [21], stopped_before_node: 'chapter_generation' },
        checkpoint: {
          status: 'ready',
          selected_chapter_indexes: [21],
          ready_chapter_indexes: [21],
          blocked_chapter_indexes: [],
        },
        recommended_next_tools: ['inspect_longform_chapter_batch'],
      },
    })

    expect(view?.label).toBe('长篇批次预检已就绪')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '预检章节', value: '第21章' })
    expect(view?.detail_items).toContainEqual({ label: '就绪章节', value: '1 章' })
    expect(view?.detail_items).toContainEqual({ label: '阻塞章节', value: '0 章' })
    expect(view?.detail_items).toContainEqual({ label: '停止节点', value: '正文生成前' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
  })

  it('builds blocked fallback views for longform preflight action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'execute_longform_chapter_batch_preflight',
      status: 'success',
      data: {
        status: 'blocked',
        reason: 'missing_previous_chapter',
        canonical_execution_plan: { chapters_to_run: [23], stopped_before_node: 'chapter_generation' },
        checkpoint: {
          status: 'blocked',
          selected_chapter_indexes: [23],
          ready_chapter_indexes: [],
          blocked_chapter_indexes: [23],
        },
        recommended_next_tools: ['inspect_longform_chapter_batch', 'plan_recovery_tools'],
      },
    })

    expect(view?.label).toBe('长篇批次预检已阻塞')
    expect(view?.variant).toBe('error')
    expect(view?.detail_items).toContainEqual({ label: '预检章节', value: '第23章' })
    expect(view?.detail_items).toContainEqual({ label: '就绪章节', value: '0 章' })
    expect(view?.detail_items).toContainEqual({ label: '阻塞章节', value: '1 章' })
    expect(view?.detail_items).toContainEqual({ label: '阻塞原因', value: 'missing_previous_chapter' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '2 个工具' })
  })

  it('builds approval-required fallback views for longform prepare action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'prepare_longform_chapter_batch_execution',
      status: 'success',
      data: {
        status: 'approval_required',
        attempt_manifest: {
          chapter_indexes: [21],
          stopped_before_node: 'chapter_generation',
          execution_steps: [{ tool_name: 'generate_chapter' }],
        },
        approval_contract: {
          consume_tool: 'execute_longform_chapter_batch',
          high_risk_side_effects: ['chapter_generation', 'world_model_intake'],
        },
        agent_plan_approval_contract: { status: 'requires_confirmation', write_step_count: 1 },
        recommended_next_tools: ['execute_longform_chapter_batch'],
      },
    })

    expect(view?.label).toBe('长篇批次执行准备待确认')
    expect(view?.variant).toBe('neutral')
    expect(view?.detail_items).toContainEqual({ label: '执行章节', value: '第21章' })
    expect(view?.detail_items).toContainEqual({ label: '审批状态', value: '等待确认' })
    expect(view?.detail_items).toContainEqual({ label: '写入步骤', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '消费工具', value: 'execute_longform_chapter_batch' })
    expect(view?.detail_items).toContainEqual({ label: '高风险副作用', value: '2 项' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
  })

  it('builds blocked fallback views for longform prepare action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'prepare_longform_chapter_batch_execution',
      status: 'success',
      data: {
        status: 'blocked',
        reason: 'missing_ready_preflight_checkpoint',
        task: { chapter_range: { start: 21, end: 21 } },
        recommended_next_tools: ['execute_longform_chapter_batch_preflight'],
      },
    })

    expect(view?.label).toBe('长篇批次执行准备已阻塞')
    expect(view?.variant).toBe('error')
    expect(view?.detail_items).toContainEqual({ label: '执行章节', value: '第21章' })
    expect(view?.detail_items).toContainEqual({ label: '阻塞原因', value: 'missing_ready_preflight_checkpoint' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
  })

  it('builds completed fallback views for longform execute action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'execute_longform_chapter_batch',
      status: 'success',
      data: {
        status: 'completed',
        chapter_index: 21,
        executed_chapter_indexes: [21],
        generation: { status: 'success' },
        evidence: {
          chapter_content_written: true,
          agent_plan_approval_verified: true,
        },
        execution_resource_binding: { status: 'ready' },
        side_effects: { executed: ['generate_chapter', 'background_task_result_execution_checkpoint'] },
        recommended_next_tools: ['review_chapter_quality', 'review_chapter_continuity'],
      },
    })

    expect(view?.label).toBe('长篇批次执行已完成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '执行章节', value: '第21章' })
    expect(view?.detail_items).toContainEqual({ label: '生成状态', value: '成功' })
    expect(view?.detail_items).toContainEqual({ label: '章节写入', value: '已写入' })
    expect(view?.detail_items).toContainEqual({ label: '审批校验', value: '已验证' })
    expect(view?.detail_items).toContainEqual({ label: '资源绑定', value: '就绪' })
    expect(view?.detail_items).toContainEqual({ label: '副作用', value: '2 项' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '2 个工具' })
  })

  it('builds blocked fallback views for longform execute action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'execute_longform_chapter_batch',
      status: 'success',
      data: {
        status: 'blocked',
        reason: 'confirmation_required',
        task: { chapter_range: { start: 21, end: 21 } },
        recommended_next_tools: ['inspect_longform_chapter_batch'],
      },
    })

    expect(view?.label).toBe('长篇批次执行已阻塞')
    expect(view?.variant).toBe('error')
    expect(view?.detail_items).toContainEqual({ label: '执行章节', value: '第21章' })
    expect(view?.detail_items).toContainEqual({ label: '阻塞原因', value: 'confirmation_required' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
  })

  it('builds failed fallback views for longform execute action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'execute_longform_chapter_batch',
      status: 'success',
      data: {
        status: 'failed',
        chapter_index: 21,
        generation: { status: 'failed' },
        error: 'generate_chapter failed',
        side_effects: { executed: ['generate_chapter'], failed: true },
      },
    })

    expect(view?.label).toBe('长篇批次执行失败')
    expect(view?.variant).toBe('error')
    expect(view?.detail_items).toContainEqual({ label: '执行章节', value: '第21章' })
    expect(view?.detail_items).toContainEqual({ label: '生成状态', value: '失败' })
    expect(view?.detail_items).toContainEqual({ label: '错误摘要', value: 'generate_chapter failed' })
    expect(view?.detail_items).toContainEqual({ label: '副作用', value: '1 项' })
  })

  it('builds completed fallback views for longform review action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'review_longform_chapter_batch_execution',
      status: 'success',
      data: {
        status: 'completed',
        chapter_index: 21,
        review_gate: { status: 'passed', blocker_count: 0, warning_count: 1 },
        reviews: {
          quality: { status: 'ready' },
          continuity: { status: 'ready' },
          world_model: { status: 'completed' },
        },
        recommended_next_tools: ['inspect_longform_chapter_batch', 'prepare_longform_chapter_batch_execution'],
      },
    })

    expect(view?.label).toBe('长篇批次审查已通过')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '审查章节', value: '第21章' })
    expect(view?.detail_items).toContainEqual({ label: '审查闸门', value: '已通过' })
    expect(view?.detail_items).toContainEqual({ label: '阻塞项', value: '0 项' })
    expect(view?.detail_items).toContainEqual({ label: '警告项', value: '1 项' })
    expect(view?.detail_items).toContainEqual({ label: '质量审查', value: '就绪' })
    expect(view?.detail_items).toContainEqual({ label: '连续性审查', value: '就绪' })
    expect(view?.detail_items).toContainEqual({ label: '世界模型', value: '成功' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '2 个工具' })
  })

  it('builds blocked fallback views for longform review action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'review_longform_chapter_batch_execution',
      status: 'success',
      data: {
        status: 'blocked',
        chapter_index: 21,
        reason: 'post_generation_review_has_blockers',
        review_gate: { status: 'needs_revision', blocker_count: 1, warning_count: 0 },
        reviews: {
          quality: { status: 'blocked' },
          continuity: { status: 'ready' },
          world_model: { status: 'skipped' },
        },
        recommended_next_tools: ['plan_chapter_revision', 'create_revision_draft', 'inspect_longform_chapter_batch'],
      },
    })

    expect(view?.label).toBe('长篇批次审查已阻塞')
    expect(view?.variant).toBe('error')
    expect(view?.detail_items).toContainEqual({ label: '审查闸门', value: '需要修订' })
    expect(view?.detail_items).toContainEqual({ label: '阻塞项', value: '1 项' })
    expect(view?.detail_items).toContainEqual({ label: '阻塞原因', value: 'post_generation_review_has_blockers' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '3 个工具' })
  })

  it('builds skipped fallback views for longform review action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'review_longform_chapter_batch_execution',
      status: 'success',
      data: {
        status: 'skipped',
        reason: 'post_generation_review_already_recorded',
        chapter_index: 21,
        review_gate: { status: 'passed', blocker_count: 0, warning_count: 0 },
        recommended_next_tools: ['inspect_longform_chapter_batch'],
      },
    })

    expect(view?.label).toBe('长篇批次审查已记录')
    expect(view?.variant).toBe('neutral')
    expect(view?.detail_items).toContainEqual({ label: '审查章节', value: '第21章' })
    expect(view?.detail_items).toContainEqual({ label: '跳过原因', value: 'post_generation_review_already_recorded' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
  })

  it('builds continue fallback views for longform route action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'route_longform_chapter_batch_after_review',
      status: 'success',
      data: {
        status: 'completed',
        chapter_index: 21,
        route_decision: {
          decision: 'continue_to_next_batch',
          next_chapter_index: 22,
          next_batch_size: 2,
        },
        next_batch_plan: { batch: { chapter_indexes: [22, 23] } },
        recommended_next_tools: ['enqueue_longform_chapter_batch', 'inspect_longform_chapter_batch'],
      },
    })

    expect(view?.label).toBe('长篇批次已路由到下一批')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '路由章节', value: '第21章' })
    expect(view?.detail_items).toContainEqual({ label: '路由决策', value: '继续下一批' })
    expect(view?.detail_items).toContainEqual({ label: '下一章', value: '第22章' })
    expect(view?.detail_items).toContainEqual({ label: '下一批', value: '第22-23章' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '2 个工具' })
  })

  it('builds revision fallback views for longform route action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'route_longform_chapter_batch_after_review',
      status: 'success',
      data: {
        status: 'completed',
        chapter_index: 21,
        route_decision: {
          decision: 'stop_for_revision',
          should_generate_next_chapter: false,
        },
        recovery_plan: {
          status: 'revision_required',
          revision_plan: { revision_actions: [{ action: 'retitle_chapter' }, { action: 'fix_continuity' }] },
        },
        recommended_next_tools: ['plan_chapter_revision', 'create_revision_draft', 'inspect_longform_chapter_batch'],
      },
    })

    expect(view?.label).toBe('长篇批次已路由到修订')
    expect(view?.variant).toBe('neutral')
    expect(view?.detail_items).toContainEqual({ label: '路由章节', value: '第21章' })
    expect(view?.detail_items).toContainEqual({ label: '路由决策', value: '进入修订' })
    expect(view?.detail_items).toContainEqual({ label: '修订动作', value: '2 项' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '3 个工具' })
  })

  it('builds blocked fallback views for longform route action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'route_longform_chapter_batch_after_review',
      status: 'success',
      data: {
        status: 'blocked',
        reason: 'missing_post_generation_review_result',
        task: { chapter_range: { start: 21, end: 21 } },
        recommended_next_tools: ['review_longform_chapter_batch_execution', 'inspect_longform_chapter_batch'],
      },
    })

    expect(view?.label).toBe('长篇批次路由已阻塞')
    expect(view?.variant).toBe('error')
    expect(view?.detail_items).toContainEqual({ label: '路由章节', value: '第21章' })
    expect(view?.detail_items).toContainEqual({ label: '阻塞原因', value: 'missing_post_generation_review_result' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '2 个工具' })
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
    expect(message.meta?.agent_run_id).toBe('run-executed')
    expect(JSON.stringify(message)).not.toContain('plan-hash-1')
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
