import { describe, expect, it } from 'vitest'
import aggregateTestSource from './agentRunProjection.test.ts?raw'
import {
  buildAgentRunActionResultView,
  getAgentRunActionDescriptor,
  getAgentRunIdFromMessage,
  isAgentRunActionType,
} from './agentRunProjection'
import {
  AGENT_RUN_ACTION_DESCRIPTORS as REGISTRY_AGENT_RUN_ACTION_DESCRIPTORS,
  AGENT_RUN_ACTION_TYPES as REGISTRY_AGENT_RUN_ACTION_TYPES,
} from './agentRunActionRegistry'
import {
  DIAGNOSTIC_AGENT_RUN_ACTION_DESCRIPTORS,
  DIAGNOSTIC_AGENT_RUN_ACTION_TYPES,
} from './agentDiagnosticRunProjection'
import {
  LONGFORM_AGENT_RUN_ACTION_DESCRIPTORS,
  LONGFORM_AGENT_RUN_ACTION_TYPES,
} from './longformAgentRunProjection'
import {
  MEMORY_LOOP_AGENT_RUN_ACTION_DESCRIPTORS,
  MEMORY_LOOP_AGENT_RUN_ACTION_TYPES,
} from './memoryLoopAgentRunProjection'
import {
  buildPlannerContinuationExecutionFeedback,
  PLANNER_AGENT_RUN_ACTION_DESCRIPTORS,
  PLANNER_AGENT_RUN_ACTION_TYPES,
} from './plannerAgentRunProjection'
import {
  ROUTE_OPT_IN_AGENT_RUN_ACTION_TYPES,
} from './routeOptInAgentRunProjection'
import {
  RECOVERY_AGENT_RUN_ACTION_TYPES,
} from './recoveryAgentRunProjection'
import {
  WRITING_TOOL_AGENT_RUN_ACTION_DESCRIPTORS,
  WRITING_TOOL_AGENT_RUN_ACTION_TYPES,
} from './writingToolAgentRunProjection'

describe('agentRunProjection', () => {
  it('keeps recovery detail specs in the recovery projection test module', () => {
    const forbiddenSpecs = [
      ['builds fallback views for recovery', ' preview action results'].join(''),
      ['builds recovery execution feedback', ' without leaking plan hash'].join(''),
      ['builds failed recovery execution feedback', ' with an error summary'].join(''),
      ['builds route opt-in contract preview', ' fallback views without leaking approval hashes'].join(''),
      ['builds route opt-in apply', ' fallback views without leaking approval hashes'].join(''),
    ]
    for (const spec of forbiddenSpecs) {
      expect(aggregateTestSource).not.toContain(spec)
    }
  })

  it('exposes a dedicated aggregate registry for agent run action descriptors', () => {
    expect(REGISTRY_AGENT_RUN_ACTION_TYPES).toEqual([
      ...PLANNER_AGENT_RUN_ACTION_TYPES,
      ...RECOVERY_AGENT_RUN_ACTION_TYPES,
      ...DIAGNOSTIC_AGENT_RUN_ACTION_TYPES,
      ...WRITING_TOOL_AGENT_RUN_ACTION_TYPES,
      ...MEMORY_LOOP_AGENT_RUN_ACTION_TYPES,
      ...ROUTE_OPT_IN_AGENT_RUN_ACTION_TYPES,
      ...LONGFORM_AGENT_RUN_ACTION_TYPES,
    ])
    for (const type of REGISTRY_AGENT_RUN_ACTION_TYPES) {
      expect(REGISTRY_AGENT_RUN_ACTION_DESCRIPTORS[type]?.type).toBe(type)
      expect(typeof REGISTRY_AGENT_RUN_ACTION_DESCRIPTORS[type]?.buildView).toBe('function')
    }
  })

  it('exposes memory loop action descriptors from a dedicated module', () => {
    expect(MEMORY_LOOP_AGENT_RUN_ACTION_TYPES).toEqual([
      'inspect_agent_memory_activation_plan',
      'search_agent_retrieval_context',
      'plan_post_chapter_memory_capture',
    ])
    for (const type of MEMORY_LOOP_AGENT_RUN_ACTION_TYPES) {
      expect(MEMORY_LOOP_AGENT_RUN_ACTION_DESCRIPTORS[type]?.type).toBe(type)
      expect(typeof MEMORY_LOOP_AGENT_RUN_ACTION_DESCRIPTORS[type]?.buildView).toBe('function')
    }
  })

  it('exposes planner continuation action descriptors from a dedicated module', () => {
    expect(PLANNER_AGENT_RUN_ACTION_TYPES).toEqual([
      'ui_planner_continuation_execute',
    ])
    for (const type of PLANNER_AGENT_RUN_ACTION_TYPES) {
      expect(PLANNER_AGENT_RUN_ACTION_DESCRIPTORS[type]?.type).toBe(type)
      expect(typeof PLANNER_AGENT_RUN_ACTION_DESCRIPTORS[type]?.buildView).toBe('function')
    }
  })

  it('builds planner continuation feedback with generated chapter followup suggestions', () => {
    const feedback = buildPlannerContinuationExecutionFeedback({
      id: 'run-generate-approved',
      project_id: 'project-1',
      goal: '执行已审批工具：生成正文',
      status: 'success',
      entrypoint: 'ui_planner_continuation_execute',
      input: {},
      output: null,
      error: null,
      steps: [
        {
          id: 'step-generate',
          run_id: 'run-generate-approved',
          project_id: 'project-1',
          step_index: 1,
          tool_name: 'execute_generate_chapter_with_approval',
          status: 'success',
          input: {},
          output: {
            status: 'success',
            chapter_index: 3,
            recommended_next_tools: [
              'plan_post_chapter_memory_capture',
              'review_chapter_quality',
            ],
          },
        },
      ],
    })

    expect(feedback.action_result_view.detail_items).toContainEqual({
      label: '执行工具',
      value: 'execute_generate_chapter_with_approval',
    })
    expect(feedback.action_result_view.detail_items).toContainEqual({
      label: '后继建议',
      value: '2 项',
    })
  })

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

  it('exposes diagnostic action descriptors from a dedicated module', () => {
    expect(DIAGNOSTIC_AGENT_RUN_ACTION_TYPES).toEqual([
      'inspect_agent_trace_audit',
      'inspect_agent_job_projection',
      'inspect_agent_health_projection',
      'inspect_agent_command_contracts',
      'inspect_agent_control_plane_readiness',
      'inspect_agent_memory_route',
      'inspect_agent_knowledge_base_route',
    ])
    for (const type of DIAGNOSTIC_AGENT_RUN_ACTION_TYPES) {
      expect(DIAGNOSTIC_AGENT_RUN_ACTION_DESCRIPTORS[type]?.type).toBe(type)
      expect(typeof DIAGNOSTIC_AGENT_RUN_ACTION_DESCRIPTORS[type]?.buildView).toBe('function')
    }
  })

  it('exposes writing tool action descriptors from a dedicated module', () => {
    expect(WRITING_TOOL_AGENT_RUN_ACTION_TYPES).toEqual([
      'review_chapter_quality',
      'review_chapter_continuity',
      'analyze_chapter_world_model',
      'review_world_model_proposals',
      'plan_world_model_proposal_resolution',
      'preview_world_model_proposal_resolution',
      'apply_world_model_proposal_resolution',
      'plan_chapter_revision',
      'create_revision_draft',
      'apply_planner_revision_patch',
      'expand_chapter_to_target',
      'compress_chapter_to_target',
    ])
    for (const type of WRITING_TOOL_AGENT_RUN_ACTION_TYPES) {
      expect(WRITING_TOOL_AGENT_RUN_ACTION_DESCRIPTORS[type]?.type).toBe(type)
      expect(typeof WRITING_TOOL_AGENT_RUN_ACTION_DESCRIPTORS[type]?.buildView).toBe('function')
    }
  })

  it('extracts run ids only from supported agent run action messages', () => {
    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'ui_planner_continuation_execute',
        status: 'success',
        data: { agent_run_id: 'run-planner-executed' },
      },
    })).toBe('run-planner-executed')

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
    expect(isAgentRunActionType('ui_planner_continuation_execute')).toBe(true)
    expect(isAgentRunActionType('plan_recovery_tools')).toBe(true)
    expect(isAgentRunActionType('plan_recommended_followups')).toBe(true)
    expect(isAgentRunActionType('ui_recovery_execute')).toBe(true)
    expect(isAgentRunActionType('inspect_agent_trace_audit')).toBe(true)
    expect(isAgentRunActionType('inspect_agent_job_projection')).toBe(true)
    expect(isAgentRunActionType('inspect_agent_health_projection')).toBe(true)
    expect(isAgentRunActionType('inspect_agent_command_contracts')).toBe(true)
    expect(isAgentRunActionType('inspect_agent_control_plane_readiness')).toBe(true)
    expect(isAgentRunActionType('inspect_agent_memory_route')).toBe(true)
    expect(isAgentRunActionType('inspect_agent_knowledge_base_route')).toBe(true)
    expect(isAgentRunActionType('review_chapter_quality')).toBe(true)
    expect(isAgentRunActionType('review_chapter_continuity')).toBe(true)
    expect(isAgentRunActionType('analyze_chapter_world_model')).toBe(true)
    expect(isAgentRunActionType('review_world_model_proposals')).toBe(true)
    expect(isAgentRunActionType('plan_world_model_proposal_resolution')).toBe(true)
    expect(isAgentRunActionType('preview_world_model_proposal_resolution')).toBe(true)
    expect(isAgentRunActionType('apply_world_model_proposal_resolution')).toBe(true)
    expect(isAgentRunActionType('plan_chapter_revision')).toBe(true)
    expect(isAgentRunActionType('create_revision_draft')).toBe(true)
    expect(isAgentRunActionType('apply_planner_revision_patch')).toBe(true)
    expect(isAgentRunActionType('expand_chapter_to_target')).toBe(true)
    expect(isAgentRunActionType('compress_chapter_to_target')).toBe(true)
    expect(isAgentRunActionType('search_agent_retrieval_context')).toBe(true)
    expect(isAgentRunActionType('plan_post_chapter_memory_capture')).toBe(true)
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
    expect(getAgentRunActionDescriptor('ui_planner_continuation_execute')?.type).toBe('ui_planner_continuation_execute')
    expect(getAgentRunActionDescriptor('plan_recovery_tools')?.type).toBe('plan_recovery_tools')
    expect(getAgentRunActionDescriptor('plan_recommended_followups')?.type).toBe('plan_recommended_followups')
    expect(getAgentRunActionDescriptor('ui_recovery_execute')?.type).toBe('ui_recovery_execute')
    expect(getAgentRunActionDescriptor('inspect_agent_trace_audit')?.type).toBe('inspect_agent_trace_audit')
    expect(getAgentRunActionDescriptor('inspect_agent_job_projection')?.type).toBe('inspect_agent_job_projection')
    expect(getAgentRunActionDescriptor('inspect_agent_health_projection')?.type).toBe('inspect_agent_health_projection')
    expect(getAgentRunActionDescriptor('inspect_agent_command_contracts')?.type).toBe('inspect_agent_command_contracts')
    expect(getAgentRunActionDescriptor('inspect_agent_control_plane_readiness')?.type).toBe('inspect_agent_control_plane_readiness')
    expect(getAgentRunActionDescriptor('inspect_agent_memory_route')?.type).toBe('inspect_agent_memory_route')
    expect(getAgentRunActionDescriptor('inspect_agent_knowledge_base_route')?.type).toBe('inspect_agent_knowledge_base_route')
    expect(getAgentRunActionDescriptor('review_chapter_quality')?.type).toBe('review_chapter_quality')
    expect(getAgentRunActionDescriptor('review_chapter_continuity')?.type).toBe('review_chapter_continuity')
    expect(getAgentRunActionDescriptor('analyze_chapter_world_model')?.type).toBe('analyze_chapter_world_model')
    expect(getAgentRunActionDescriptor('review_world_model_proposals')?.type).toBe('review_world_model_proposals')
    expect(getAgentRunActionDescriptor('plan_world_model_proposal_resolution')?.type).toBe('plan_world_model_proposal_resolution')
    expect(getAgentRunActionDescriptor('preview_world_model_proposal_resolution')?.type).toBe('preview_world_model_proposal_resolution')
    expect(getAgentRunActionDescriptor('apply_world_model_proposal_resolution')?.type).toBe('apply_world_model_proposal_resolution')
    expect(getAgentRunActionDescriptor('plan_chapter_revision')?.type).toBe('plan_chapter_revision')
    expect(getAgentRunActionDescriptor('create_revision_draft')?.type).toBe('create_revision_draft')
    expect(getAgentRunActionDescriptor('apply_planner_revision_patch')?.type).toBe('apply_planner_revision_patch')
    expect(getAgentRunActionDescriptor('expand_chapter_to_target')?.type).toBe('expand_chapter_to_target')
    expect(getAgentRunActionDescriptor('compress_chapter_to_target')?.type).toBe('compress_chapter_to_target')
    expect(getAgentRunActionDescriptor('search_agent_retrieval_context')?.type).toBe('search_agent_retrieval_context')
    expect(getAgentRunActionDescriptor('plan_post_chapter_memory_capture')?.type).toBe('plan_post_chapter_memory_capture')
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

  it('extracts nested run ids from job projection action results', () => {
    expect(getAgentRunIdFromMessage({
      action_result: {
        type: 'inspect_agent_job_projection',
        status: 'success',
        data: {
          selected_task: {
            agent_runs: [{ id: 'run-job-1' }],
          },
        },
      },
    })).toBe('run-job-1')
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

  it('does not build fallback views for unknown action results', () => {
    expect(buildAgentRunActionResultView({
      type: 'generate_chapter',
      status: 'success',
      data: { agent_run_id: 'run-hidden' },
    })).toBeNull()
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
        command_contracts: {
          source: 'planner_trace.agent_health_projection.command_contracts',
          summary: {
            agent_control_commands: 2,
            gap_count: 1,
          },
          commands: [{ name: 'legacy_world_model' }],
        },
      },
    })

    expect(view?.label).toBe('Trace 审计已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '运行状态', value: '失败' })
    expect(view?.detail_items).toContainEqual({ label: '工具步骤', value: '3 个' })
    expect(view?.detail_items).toContainEqual({ label: 'Trace', value: '2 条' })
    expect(view?.detail_items).toContainEqual({ label: '失败原因', value: 'tool_failed' })
    expect(view?.detail_items).toContainEqual({ label: '建议动作', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '命令契约', value: '已投影' })
    expect(view?.detail_items).toContainEqual({ label: '控制命令', value: '2 个' })
    expect(view?.detail_items).toContainEqual({ label: '契约缺口', value: '1 个' })
    expect(JSON.stringify(view)).not.toContain('legacy_world_model')
  })

  it('builds fallback views for job projection action results', () => {
    const view = buildAgentRunActionResultView({
      type: 'inspect_agent_job_projection',
      status: 'success',
      data: {
        queue: { depth: 4, active: 1 },
        selected_task: {
          status: 'running',
          progress: { next_chapter_index: 12 },
          agent_runs: [{ id: 'run-job-1' }, { id: 'run-job-2' }],
          control_plane_readiness: {
            status: 'degraded',
            summary: { total_gap_count: 2 },
          },
          command_contracts: {
            source: 'planner_trace.agent_health_projection.command_contracts',
            summary: {
              agent_control_commands: 2,
              gap_count: 1,
            },
            commands: [{ name: 'legacy_generate' }],
          },
        },
        recommended_tools: ['inspect_agent_command_contracts', 'inspect_agent_trace_audit'],
      },
    })

    expect(view?.label).toBe('任务队列投影已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '队列深度', value: '4 个' })
    expect(view?.detail_items).toContainEqual({ label: '活跃任务', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '任务状态', value: '运行中' })
    expect(view?.detail_items).toContainEqual({ label: '下一章', value: '第12章' })
    expect(view?.detail_items).toContainEqual({ label: '关联运行', value: '2 个' })
    expect(view?.detail_items).toContainEqual({ label: '控制平面', value: '需检查' })
    expect(view?.detail_items).toContainEqual({ label: '控制面缺口', value: '2 个' })
    expect(view?.detail_items).toContainEqual({ label: '命令契约', value: '已投影' })
    expect(view?.detail_items).toContainEqual({ label: '契约缺口', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '推荐工具', value: '2 个' })
    expect(JSON.stringify(view)).not.toContain('legacy_generate')
  })

  it('builds fallback views for command contract diagnostics', () => {
    const view = buildAgentRunActionResultView({
      type: 'inspect_agent_command_contracts',
      status: 'success',
      data: {
        summary: {
          total_commands: 8,
          public_commands: 5,
          agent_control_commands: 2,
          available_commands: 5,
          gap_count: 1,
        },
        commands: [{ name: 'legacy_generate' }],
        recommended_next_tools: ['describe_agent_tools'],
      },
    })

    expect(view?.label).toBe('命令契约诊断已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '命令契约', value: '已投影' })
    expect(view?.detail_items).toContainEqual({ label: '控制命令', value: '2 个' })
    expect(view?.detail_items).toContainEqual({ label: '契约缺口', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '推荐工具', value: '1 个' })
    expect(JSON.stringify(view)).not.toContain('legacy_generate')
  })

  it('builds fallback views for control plane readiness diagnostics', () => {
    const view = buildAgentRunActionResultView({
      type: 'inspect_agent_control_plane_readiness',
      status: 'success',
      data: {
        status: 'degraded',
        summary: {
          total_gap_count: 3,
          tool_gap_count: 2,
          command_gap_count: 1,
        },
        diagnostics: [{ code: 'agent_tool_contract_gaps' }],
        recommended_next_tools: ['inspect_agent_tool_contracts', 'inspect_agent_command_contracts'],
      },
    })

    expect(view?.label).toBe('控制平面诊断已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '控制平面', value: '需检查' })
    expect(view?.detail_items).toContainEqual({ label: '控制面缺口', value: '3 个' })
    expect(view?.detail_items).toContainEqual({ label: '工具缺口', value: '2 个' })
    expect(view?.detail_items).toContainEqual({ label: '命令缺口', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '建议检查', value: '2 项' })
    expect(JSON.stringify(view)).not.toContain('agent_tool_contract_gaps')
  })

  it('builds fallback views for agent health projection diagnostics', () => {
    const view = buildAgentRunActionResultView({
      type: 'inspect_agent_health_projection',
      status: 'success',
      data: {
        status: 'needs_attention',
        command_contracts: {
          summary: {
            agent_control_commands: 2,
            gap_count: 1,
          },
          commands: [{ name: 'legacy_status' }],
        },
        control_plane_readiness: {
          status: 'degraded',
          summary: {
            total_gap_count: 3,
            command_gap_count: 1,
          },
          recommended_next_tools: ['inspect_agent_command_contracts'],
        },
        profile_policy: {
          status: 'needs_attention',
          summary: { issues: 2 },
          issues: [{ code: 'delegate_target_missing_definition', target: 'ghost_worker' }],
        },
        agent_worker_route_registry: {
          status: 'passed',
          summary: {
            routes: 35,
            ready_routes: 35,
            unrouted_allowed_tools: 0,
            issues: 0,
          },
        },
        diagnostics: [{ code: 'agent_profile_policy_needs_attention' }],
        recommended_tools: ['describe_agent_tools', 'inspect_agent_trace_audit'],
      },
    })

    expect(view?.label).toBe('Agent 健康投影已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '健康状态', value: '需处理' })
    expect(view?.detail_items).toContainEqual({ label: '控制平面', value: '需检查' })
    expect(view?.detail_items).toContainEqual({ label: '控制面缺口', value: '3 个' })
    expect(view?.detail_items).toContainEqual({ label: '命令契约', value: '已投影' })
    expect(view?.detail_items).toContainEqual({ label: '契约缺口', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: 'Profile 策略', value: '需处理' })
    expect(view?.detail_items).toContainEqual({ label: '策略问题', value: '2 个' })
    expect(view?.detail_items).toContainEqual({ label: '路由审计', value: '通过' })
    expect(view?.detail_items).toContainEqual({ label: '未路由工具', value: '0 个' })
    expect(view?.detail_items).toContainEqual({ label: '诊断项', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '推荐工具', value: '2 个' })
    expect(JSON.stringify(view)).not.toContain('delegate_target_missing_definition')
    expect(JSON.stringify(view)).not.toContain('legacy_status')
  })

  it('builds fallback views for memory route diagnostics', () => {
    const view = buildAgentRunActionResultView({
      type: 'inspect_agent_memory_route',
      status: 'success',
      data: {
        route: {
          status: 'blocked',
          recommended_tools: ['repair_longform_maintenance'],
        },
        longform_memory: {
          chapter_count: 12,
          total_memories: 14,
        },
        retrieval: {
          total_documents: 3,
        },
        memory_provenance: {
          status: 'blocked',
          source_count: 4,
          sources: [{ source_ref: 'LongformMemory' }],
        },
        diagnostics: [{ code: 'longform_memory_needs_maintenance' }],
      },
    })

    expect(view?.label).toBe('记忆路由诊断已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '路由状态', value: '已阻塞' })
    expect(view?.detail_items).toContainEqual({ label: '章节记忆', value: '12 章' })
    expect(view?.detail_items).toContainEqual({ label: '长篇记忆', value: '14 条' })
    expect(view?.detail_items).toContainEqual({ label: '检索文档', value: '3 个' })
    expect(view?.detail_items).toContainEqual({ label: '记忆溯源', value: '已阻塞' })
    expect(view?.detail_items).toContainEqual({ label: '来源数量', value: '4 个' })
    expect(view?.detail_items).toContainEqual({ label: '诊断项', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '推荐工具', value: '1 个' })
    expect(JSON.stringify(view)).not.toContain('LongformMemory')
    expect(JSON.stringify(view)).not.toContain('longform_memory_needs_maintenance')
  })

  it('builds fallback views for knowledge base route diagnostics', () => {
    const view = buildAgentRunActionResultView({
      type: 'inspect_agent_knowledge_base_route',
      status: 'success',
      data: {
        route: {
          status: 'ready',
          recommended_tools: ['summarize_longform_context'],
        },
        author_preferences: {
          status: 'configured',
        },
        learned_rules: {
          total: 12,
          returned: 3,
          items: [{ condition: '规则 11' }],
        },
        knowledge_candidates: {
          total: 2,
          items: [{ title: '章末钩子' }],
        },
        memory_provenance: {
          status: 'available',
          source_count: 5,
          sources: [{ source_ref: 'PromptRule(rule_type=learned)' }],
        },
        diagnostics: [{ code: 'learned_rules_truncated' }],
      },
    })

    expect(view?.label).toBe('知识库路由诊断已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '路由状态', value: '可用' })
    expect(view?.detail_items).toContainEqual({ label: '作者偏好', value: '已配置' })
    expect(view?.detail_items).toContainEqual({ label: '学习规则', value: '12 条' })
    expect(view?.detail_items).toContainEqual({ label: '本次返回', value: '3 条' })
    expect(view?.detail_items).toContainEqual({ label: '知识候选', value: '2 条' })
    expect(view?.detail_items).toContainEqual({ label: '记忆溯源', value: '可用' })
    expect(view?.detail_items).toContainEqual({ label: '来源数量', value: '5 个' })
    expect(view?.detail_items).toContainEqual({ label: '诊断项', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '推荐工具', value: '1 个' })
    expect(JSON.stringify(view)).not.toContain('规则 11')
    expect(JSON.stringify(view)).not.toContain('章末钩子')
    expect(JSON.stringify(view)).not.toContain('PromptRule')
  })

  it('builds fallback views for chapter quality reviews without leaking issue codes', () => {
    const view = buildAgentRunActionResultView({
      type: 'review_chapter_quality',
      status: 'success',
      data: {
        status: 'needs_revision',
        chapter_index: 12,
        score: 72,
        issues: [
          { code: 'generic_title', detail: '标题缺少网文钩子' },
          { code: 'length_under_target', detail: '正文偏短' },
        ],
        recommended_actions: ['plan_chapter_revision'],
      },
    })

    expect(view?.label).toBe('章节质量审查已生成')
    expect(view?.variant).toBe('neutral')
    expect(view?.detail_items).toContainEqual({ label: '章节', value: '第12章' })
    expect(view?.detail_items).toContainEqual({ label: '审查状态', value: '需修订' })
    expect(view?.detail_items).toContainEqual({ label: '评分', value: '72' })
    expect(view?.detail_items).toContainEqual({ label: '问题', value: '2 个' })
    expect(view?.detail_items).toContainEqual({ label: '建议动作', value: '1 个' })
    expect(JSON.stringify(view)).not.toContain('generic_title')
    expect(JSON.stringify(view)).not.toContain('length_under_target')
    expect(JSON.stringify(view)).not.toContain('标题缺少网文钩子')
  })

  it('builds fallback views for chapter continuity reviews without leaking issue codes', () => {
    const view = buildAgentRunActionResultView({
      type: 'review_chapter_continuity',
      status: 'success',
      data: {
        status: 'needs_attention',
        chapter_index: 12,
        lookback: 5,
        issues: [
          { code: 'world_fact_drift', detail: '称谓与前文冲突' },
        ],
        recommended_actions: ['plan_chapter_revision'],
      },
    })

    expect(view?.label).toBe('章节连续性审查已生成')
    expect(view?.variant).toBe('neutral')
    expect(view?.detail_items).toContainEqual({ label: '章节', value: '第12章' })
    expect(view?.detail_items).toContainEqual({ label: '审查状态', value: '需处理' })
    expect(view?.detail_items).toContainEqual({ label: '回看窗口', value: '5 章' })
    expect(view?.detail_items).toContainEqual({ label: '问题', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '建议动作', value: '1 个' })
    expect(JSON.stringify(view)).not.toContain('world_fact_drift')
    expect(JSON.stringify(view)).not.toContain('称谓与前文冲突')
  })

  it('builds fallback views for world model analysis without leaking proposal payloads', () => {
    const view = buildAgentRunActionResultView({
      type: 'analyze_chapter_world_model',
      status: 'success',
      data: {
        status: 'completed',
        chapter_index: 12,
        proposal_bundle: {
          id: 'bundle-secret',
          item_count: 3,
        },
        proposals: [
          { title: '陆辞获得灯塔密钥' },
          { title: '灯塔病毒样本被转移' },
          { title: '苏晚晴恢复旧记忆' },
        ],
        recommended_next_tools: ['review_world_model_proposals'],
      },
    })

    expect(view?.label).toBe('世界模型分析已生成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '章节', value: '第12章' })
    expect(view?.detail_items).toContainEqual({ label: '分析状态', value: '成功' })
    expect(view?.detail_items).toContainEqual({ label: '提案', value: '3 条' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
    expect(JSON.stringify(view)).not.toContain('bundle-secret')
    expect(JSON.stringify(view)).not.toContain('陆辞获得灯塔密钥')
    expect(JSON.stringify(view)).not.toContain('灯塔病毒样本被转移')
  })

  it('builds fallback views for world model proposal reports without leaking clusters', () => {
    const view = buildAgentRunActionResultView({
      type: 'review_world_model_proposals',
      status: 'success',
      data: {
        status: 'blocked',
        profile_version: 3,
        total_items: 8,
        returned_items: 4,
        has_more: true,
        risk_counts: { high: 2, medium: 4, low: 2 },
        review_mode_counts: { individual: 5, batch: 3 },
        clusters: [
          {
            cluster_id: 'cluster-secret',
            item_ids: ['item-secret'],
            subject_refs: ['陆辞'],
            reason: '高风险设定冲突',
          },
        ],
        recommended_actions: ['pause_generation_until_proposals_resolved', 'review_high_risk_proposals'],
      },
    })

    expect(view?.label).toBe('世界模型提案待处理')
    expect(view?.variant).toBe('error')
    expect(view?.detail_items).toContainEqual({ label: '队列状态', value: '已阻塞' })
    expect(view?.detail_items).toContainEqual({ label: '待处理', value: '8 条' })
    expect(view?.detail_items).toContainEqual({ label: '本次返回', value: '4 条' })
    expect(view?.detail_items).toContainEqual({ label: '高风险', value: '2 条' })
    expect(view?.detail_items).toContainEqual({ label: '批量审阅', value: '3 条' })
    expect(view?.detail_items).toContainEqual({ label: '还有更多', value: '是' })
    expect(view?.detail_items).toContainEqual({ label: '建议动作', value: '2 个' })
    expect(JSON.stringify(view)).not.toContain('cluster-secret')
    expect(JSON.stringify(view)).not.toContain('item-secret')
    expect(JSON.stringify(view)).not.toContain('高风险设定冲突')
  })

  it('builds fallback views for world model resolution plans without leaking step payloads', () => {
    const view = buildAgentRunActionResultView({
      type: 'plan_world_model_proposal_resolution',
      status: 'success',
      data: {
        status: 'blocked',
        total_items: 8,
        returned_items: 4,
        risk_counts: { high: 2, medium: 4, low: 2 },
        resolution_steps: [
          { cluster_id: 'cluster-a', item_ids: ['item-a'], reason: '个别审阅' },
          { cluster_id: 'cluster-b', item_ids: ['item-b'], reason: '批量审阅' },
          { cluster_id: 'cluster-c', item_ids: ['item-c'], reason: '个别审阅' },
        ],
        high_priority_step_count: 2,
        batch_step_count: 1,
        requires_human_confirmation: true,
        recommended_next_tools: ['review_world_model_proposals'],
      },
    })

    expect(view?.label).toBe('世界模型决议计划待处理')
    expect(view?.variant).toBe('error')
    expect(view?.detail_items).toContainEqual({ label: '计划状态', value: '已阻塞' })
    expect(view?.detail_items).toContainEqual({ label: '待处理', value: '8 条' })
    expect(view?.detail_items).toContainEqual({ label: '本次返回', value: '4 条' })
    expect(view?.detail_items).toContainEqual({ label: '高风险', value: '2 条' })
    expect(view?.detail_items).toContainEqual({ label: '处理步骤', value: '3 个' })
    expect(view?.detail_items).toContainEqual({ label: '高优先级', value: '2 个' })
    expect(view?.detail_items).toContainEqual({ label: '批量步骤', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '需要确认', value: '是' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
    expect(JSON.stringify(view)).not.toContain('cluster-a')
    expect(JSON.stringify(view)).not.toContain('item-a')
    expect(JSON.stringify(view)).not.toContain('个别审阅')
  })

  it('builds fallback views for world model resolution previews without leaking decisions', () => {
    const view = buildAgentRunActionResultView({
      type: 'preview_world_model_proposal_resolution',
      status: 'success',
      data: {
        status: 'blocked',
        total_actionable_items: 5,
        valid_decision_count: 2,
        invalid_decision_count: 1,
        would_create_review_count: 2,
        would_create_fact_count: 1,
        would_resolve_item_count: 2,
        remaining_actionable_item_count_after_preview: 3,
        requires_confirmation: true,
        valid_decisions: [{ proposal_item_id: 'item-secret' }],
        invalid_decisions: [{ code: 'unsupported_action', message: 'bad action' }],
        recommended_actions: ['fix_invalid_resolution_decisions'],
      },
    })

    expect(view?.label).toBe('世界模型决议预览待处理')
    expect(view?.variant).toBe('error')
    expect(view?.detail_items).toContainEqual({ label: '预览状态', value: '已阻塞' })
    expect(view?.detail_items).toContainEqual({ label: '待处理', value: '5 条' })
    expect(view?.detail_items).toContainEqual({ label: '有效决策', value: '2 个' })
    expect(view?.detail_items).toContainEqual({ label: '无效决策', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '将写入事实', value: '1 条' })
    expect(view?.detail_items).toContainEqual({ label: '预计解决', value: '2 条' })
    expect(view?.detail_items).toContainEqual({ label: '预览后剩余', value: '3 条' })
    expect(view?.detail_items).toContainEqual({ label: '需要确认', value: '是' })
    expect(view?.detail_items).toContainEqual({ label: '建议动作', value: '1 个' })
    expect(JSON.stringify(view)).not.toContain('item-secret')
    expect(JSON.stringify(view)).not.toContain('unsupported_action')
    expect(JSON.stringify(view)).not.toContain('bad action')
  })

  it('builds fallback views for world model resolution apply results without leaking review ids', () => {
    const view = buildAgentRunActionResultView({
      type: 'apply_world_model_proposal_resolution',
      status: 'success',
      data: {
        status: 'blocked',
        before_actionable_items: 5,
        after_actionable_items: 3,
        applied_count: 2,
        invalid_decision_count: 0,
        requires_confirmation: false,
        should_generate_next_chapter: false,
        applied_reviews: [{ review_id: 'review-secret', proposal_item_id: 'item-secret' }],
        recommended_actions: ['continue_world_model_proposal_resolution'],
      },
    })

    expect(view?.label).toBe('世界模型决议应用已阻塞')
    expect(view?.variant).toBe('error')
    expect(view?.detail_items).toContainEqual({ label: '应用状态', value: '已阻塞' })
    expect(view?.detail_items).toContainEqual({ label: '应用前待处理', value: '5 条' })
    expect(view?.detail_items).toContainEqual({ label: '应用后待处理', value: '3 条' })
    expect(view?.detail_items).toContainEqual({ label: '已应用', value: '2 个' })
    expect(view?.detail_items).toContainEqual({ label: '无效决策', value: '0 个' })
    expect(view?.detail_items).toContainEqual({ label: '需要确认', value: '否' })
    expect(view?.detail_items).toContainEqual({ label: '可继续生成', value: '否' })
    expect(view?.detail_items).toContainEqual({ label: '建议动作', value: '1 个' })
    expect(JSON.stringify(view)).not.toContain('review-secret')
    expect(JSON.stringify(view)).not.toContain('item-secret')
  })

  it('builds fallback views for chapter revision plans without leaking findings', () => {
    const view = buildAgentRunActionResultView({
      type: 'plan_chapter_revision',
      status: 'success',
      data: {
        status: 'blocked',
        chapter_index: 12,
        revision_actions: [
          { action: 'fix_character_profile_drift', source_finding: 'character_profile_drift', reason: '漂移' },
          { action: 'respect_ability_boundary', source_finding: 'ability_boundary_drift', reason: '越界' },
        ],
        world_model_proposal_pressure: {
          total_items: 3,
          top_clusters: [{ cluster_id: 'cluster-secret' }],
        },
        recommended_next_tools: ['create_revision_draft', 'review_world_model_proposals'],
      },
    })

    expect(view?.label).toBe('章节修订计划待处理')
    expect(view?.variant).toBe('error')
    expect(view?.detail_items).toContainEqual({ label: '章节', value: '第12章' })
    expect(view?.detail_items).toContainEqual({ label: '计划状态', value: '已阻塞' })
    expect(view?.detail_items).toContainEqual({ label: '修订动作', value: '2 项' })
    expect(view?.detail_items).toContainEqual({ label: '世界模型提案', value: '3 条' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '2 个工具' })
    expect(JSON.stringify(view)).not.toContain('character_profile_drift')
    expect(JSON.stringify(view)).not.toContain('cluster-secret')
    expect(JSON.stringify(view)).not.toContain('漂移')
  })

  it('builds fallback views for revision drafts without leaking revision ids or plans', () => {
    const view = buildAgentRunActionResultView({
      type: 'create_revision_draft',
      status: 'success',
      data: {
        status: 'drafted',
        chapter_index: 12,
        revision_id: 'revision-secret',
        revision_index: 2,
        annotation_count: 2,
        correction_count: 0,
        revision_actions: [
          { action: 'fix_character_profile_drift', reason: '漂移' },
          { action: 'respect_ability_boundary', reason: '越界' },
        ],
        plan: { review: { findings: [{ message: '原始问题' }] } },
        recommended_next_tools: ['apply_planner_revision_patch'],
      },
    })

    expect(view?.label).toBe('章节修订草稿已创建')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '章节', value: '第12章' })
    expect(view?.detail_items).toContainEqual({ label: '草稿状态', value: '已起草' })
    expect(view?.detail_items).toContainEqual({ label: '修订序号', value: '2' })
    expect(view?.detail_items).toContainEqual({ label: '批注', value: '2 个' })
    expect(view?.detail_items).toContainEqual({ label: '修正', value: '0 个' })
    expect(view?.detail_items).toContainEqual({ label: '修订动作', value: '2 项' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
    expect(JSON.stringify(view)).not.toContain('revision-secret')
    expect(JSON.stringify(view)).not.toContain('原始问题')
    expect(JSON.stringify(view)).not.toContain('fix_character_profile_drift')
  })

  it('builds fallback views for revision patch applies without leaking replacement payloads', () => {
    const view = buildAgentRunActionResultView({
      type: 'apply_planner_revision_patch',
      status: 'success',
      data: {
        status: 'completed',
        chapter_index: 12,
        chapter_id: 'chapter-secret',
        revision_id: 'revision-secret',
        revision_index: 2,
        base_version_id: 'base-secret',
        result_version_id: 'result-secret',
        applied_replacement_count: 2,
        applied_replacements: [{ original_text: '旧文本', replacement_text: '新文本' }],
        word_count: 2180,
        should_generate_next_chapter: false,
        recommended_next_tools: ['review_chapter_quality'],
      },
    })

    expect(view?.label).toBe('章节修订补丁已应用')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '章节', value: '第12章' })
    expect(view?.detail_items).toContainEqual({ label: '应用状态', value: '成功' })
    expect(view?.detail_items).toContainEqual({ label: '修订序号', value: '2' })
    expect(view?.detail_items).toContainEqual({ label: '替换', value: '2 处' })
    expect(view?.detail_items).toContainEqual({ label: '当前字数', value: '2180' })
    expect(view?.detail_items).toContainEqual({ label: '可继续生成', value: '否' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
    expect(JSON.stringify(view)).not.toContain('chapter-secret')
    expect(JSON.stringify(view)).not.toContain('revision-secret')
    expect(JSON.stringify(view)).not.toContain('旧文本')
    expect(JSON.stringify(view)).not.toContain('result-secret')
  })

  it('builds fallback views for chapter expansion without leaking trace payloads', () => {
    const view = buildAgentRunActionResultView({
      type: 'expand_chapter_to_target',
      status: 'success',
      data: {
        status: 'completed',
        chapter_index: 12,
        trace_id: 'trace-secret',
        revision_id: 'revision-secret',
        previous_word_count: 1600,
        word_count: 2200,
        target_min_word_count: 2000,
        change_summary: '新增动作场景',
        warnings: ['仍需复审'],
        pending_world_model_proposal_count: 1,
        should_generate_next_chapter: false,
        recommended_next_tools: ['review_chapter_quality'],
      },
    })

    expect(view?.label).toBe('章节扩写已完成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '章节', value: '第12章' })
    expect(view?.detail_items).toContainEqual({ label: '扩写状态', value: '成功' })
    expect(view?.detail_items).toContainEqual({ label: '原字数', value: '1600' })
    expect(view?.detail_items).toContainEqual({ label: '当前字数', value: '2200' })
    expect(view?.detail_items).toContainEqual({ label: '目标下限', value: '2000' })
    expect(view?.detail_items).toContainEqual({ label: '警告', value: '1 个' })
    expect(view?.detail_items).toContainEqual({ label: '世界模型提案', value: '1 条' })
    expect(view?.detail_items).toContainEqual({ label: '可继续生成', value: '否' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
    expect(JSON.stringify(view)).not.toContain('trace-secret')
    expect(JSON.stringify(view)).not.toContain('revision-secret')
    expect(JSON.stringify(view)).not.toContain('新增动作场景')
  })

  it('builds fallback views for chapter compression without leaking failed attempts', () => {
    const view = buildAgentRunActionResultView({
      type: 'compress_chapter_to_target',
      status: 'success',
      data: {
        status: 'completed',
        chapter_index: 12,
        trace_id: 'trace-secret',
        previous_word_count: 3600,
        word_count: 2600,
        target_max_word_count: 2800,
        remaining_forbidden_terms: [],
        postcondition_retry_count: 1,
        failed_attempts: [{ error: '模型输出过长' }],
        pending_world_model_proposal_count: 0,
        should_generate_next_chapter: false,
        recommended_next_tools: ['review_chapter_quality'],
      },
    })

    expect(view?.label).toBe('章节压缩已完成')
    expect(view?.variant).toBe('success')
    expect(view?.detail_items).toContainEqual({ label: '章节', value: '第12章' })
    expect(view?.detail_items).toContainEqual({ label: '压缩状态', value: '成功' })
    expect(view?.detail_items).toContainEqual({ label: '原字数', value: '3600' })
    expect(view?.detail_items).toContainEqual({ label: '当前字数', value: '2600' })
    expect(view?.detail_items).toContainEqual({ label: '目标上限', value: '2800' })
    expect(view?.detail_items).toContainEqual({ label: '禁用词剩余', value: '0 个' })
    expect(view?.detail_items).toContainEqual({ label: '重试', value: '1 次' })
    expect(view?.detail_items).toContainEqual({ label: '失败尝试', value: '1 次' })
    expect(view?.detail_items).toContainEqual({ label: '世界模型提案', value: '0 条' })
    expect(view?.detail_items).toContainEqual({ label: '可继续生成', value: '否' })
    expect(view?.detail_items).toContainEqual({ label: '下一步', value: '1 个工具' })
    expect(JSON.stringify(view)).not.toContain('trace-secret')
    expect(JSON.stringify(view)).not.toContain('模型输出过长')
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

})
