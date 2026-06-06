import type { WritingAgentRunDetail } from '../../../api/types'

type PlannerPlanExecutePayload = {
  sourceRunId: string
  sourcePlanId: string
  goal: string
  tools: Array<Record<string, unknown>>
  planner: Record<string, unknown>
  approvalContractHash?: string
  approvalContract?: Record<string, unknown>
}

const chapterApprovalContract = {
  status: 'requires_confirmation',
  approval: { approval_contract_hash: 'approval:chapter-3' },
}

const chapterAgentPlan = {
  project_id: 'project-1',
  intent_class: 'direct_generate_chapter',
  trace: {
    plan_id: 'direct-generate:project-1:chapter:3',
    planner_version: 'phase114.generate_chapter_execution_prepare.v1',
  },
  steps: [
    {
      step_index: 1,
      step_id: 'direct-generate:project-1:chapter:3',
      tool_name: 'generate_chapter',
      params: { chapter_index: 3 },
      mutability: 'guarded_write',
      requires_confirmation: true,
      reason: '直接生成指定章节正文。',
    },
  ],
}

export const guardedRecoveryRun: WritingAgentRunDetail = {
  id: 'run-recovery',
  project_id: 'project-1',
  goal: '恢复上一轮阻塞',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-recovery',
      run_id: 'run-recovery',
      project_id: 'project-1',
      step_index: 2,
      tool_name: 'plan_recovery_tools',
      status: 'success',
      input: {},
      output: {
        execution_policy: {
          mode: 'preview',
          status: 'requires_user_input',
          requires_confirmation: true,
          requires_plan_hash: true,
          safe_auto_execute: false,
        },
        guardrails: {
          status: 'blocked',
          blockers: [
            {
              code: 'requires_user_input',
              tool_name: 'prepare_generate_chapter_execution',
              message: '恢复工具需要用户补充输入，不能自动执行。',
            },
          ],
        },
        tools: [{ tool_name: 'prepare_generate_chapter_execution' }],
      },
    },
  ],
}

export const recommendedFollowupProvenanceRun: WritingAgentRunDetail = {
  id: 'run-followup',
  project_id: 'project-1',
  goal: '预览检索覆盖恢复后继',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-followup',
      run_id: 'run-followup',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'plan_recommended_followups',
      status: 'success',
      input: {},
      output: {
        status: 'completed',
        recommended_followups: {
          status: 'recommended',
          source_fields: [
            'memory_provenance.recovery.tools',
            'memory_provenance.recovery.write_tools',
          ],
          provenance_write_tools: [
            { tool_name: 'repair_longform_maintenance', params: {} },
          ],
        },
        tools: [
          {
            tool_name: 'inspect_agent_memory_route',
            params: {
              chapter_index: 13,
              query: '检索索引为空，诊断第13章长篇记忆与检索覆盖。',
              include_context_summary: false,
            },
          },
        ],
      },
    },
  ],
}

export const recommendedFollowupWorkerDispatchRun: WritingAgentRunDetail = {
  id: 'run-followup-workers',
  project_id: 'project-1',
  goal: '预览推荐后继 worker 分派',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-followup-workers',
      run_id: 'run-followup-workers',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'plan_recommended_followups',
      status: 'success',
      input: {},
      output: {
        status: 'completed',
        recommended_followups: { status: 'recommended' },
        tools: [
          {
            tool_name: 'review_chapter_quality',
            planner: { agent_profile: 'reviewer_worker' },
          },
          {
            tool_name: 'search_agent_retrieval_context',
            planner: { agent_profile: 'retrieval_worker' },
          },
          {
            tool_name: 'plan_post_chapter_memory_capture',
            planner: { agent_profile: 'memory_worker' },
          },
        ],
        worker_dispatch: {
          status: 'ready',
          summary: {
            workers: 3,
            planned_tasks: 3,
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
          worker_dispatches: [
            {
              worker: { name: 'reviewer_worker' },
              summary: { planned_tasks: 1, blocked_tasks: 0, issues: 0 },
            },
            {
              worker: { name: 'retrieval_worker' },
              summary: { planned_tasks: 1, blocked_tasks: 0, issues: 0 },
            },
            {
              worker: { name: 'memory_worker' },
              summary: { planned_tasks: 1, blocked_tasks: 0, issues: 0 },
            },
          ],
        },
      },
    },
  ],
}

export const executableRecommendedFollowupRun: WritingAgentRunDetail = {
  id: 'run-followup',
  project_id: 'project-1',
  goal: '预览推荐后继',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-followup',
      run_id: 'run-followup',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'plan_recommended_followups',
      status: 'success',
      input: {},
      output: {
        status: 'completed',
        source_run_id: 'source-run-2',
        plan_hash: 'followup-plan-hash-1',
        recommended_followups: {
          status: 'recommended',
        },
        tools: [
          { tool_name: 'review_chapter_quality', params: { chapter_index: 2 } },
          { tool_name: 'review_chapter_continuity', params: { chapter_index: 2 } },
        ],
        execution_policy: {
          mode: 'preview',
          status: 'preview_only',
          requires_followup_run: true,
          requires_confirmation: true,
          requires_plan_hash: true,
        },
      },
    },
  ],
}

export const postApprovalContinuationRun: WritingAgentRunDetail = {
  id: 'run-followup-continuation',
  project_id: 'project-1',
  goal: '预览知识沉淀后的继续写作链路',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-followup-continuation',
      run_id: 'run-followup-continuation',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'plan_recommended_followups',
      status: 'success',
      input: {},
      output: {
        status: 'completed',
        source_run_id: 'source-run-memory-write',
        plan_hash: 'followup-plan-hash-continuation',
        recommended_followups: {
          status: 'recommended',
          post_approval_continuation_tools: [
            { tool_name: 'summarize_longform_context', params: { chapter_index: 3 } },
            { tool_name: 'preflight_writing', params: { chapter_index: 3 } },
          ],
        },
        tools: [
          { tool_name: 'summarize_longform_context', params: { chapter_index: 3 } },
          { tool_name: 'preflight_writing', params: { chapter_index: 3 } },
        ],
        execution_policy: {
          mode: 'preview',
          status: 'preview_only',
          requires_followup_run: true,
          requires_confirmation: true,
          requires_plan_hash: true,
        },
      },
    },
  ],
}

export const executableRecoveryRun: WritingAgentRunDetail = {
  id: 'run-recovery',
  project_id: 'project-1',
  goal: '恢复上一轮阻塞',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-recovery',
      run_id: 'run-recovery',
      project_id: 'project-1',
      step_index: 2,
      tool_name: 'plan_recovery_tools',
      status: 'success',
      input: {},
      output: {
        can_execute: true,
        source_run_id: 'source-run-1',
        plan_hash: 'plan-hash-1',
        execution_policy: {
          mode: 'preview',
          status: 'ready',
          requires_confirmation: true,
          requires_plan_hash: true,
          safe_auto_execute: false,
        },
        guardrails: {
          status: 'ready',
          blockers: [],
        },
        tools: [{ tool_name: 'prepare_generate_chapter_execution' }],
      },
    },
  ],
}

export const recommendedFollowupChapterPrepareRun: WritingAgentRunDetail = {
  id: 'run-followup-exec',
  project_id: 'project-1',
  goal: '执行推荐后继工具链',
  status: 'success',
  entrypoint: 'ui_recommended_followup_execute',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-prepare',
      run_id: 'run-followup-exec',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'prepare_generate_chapter_execution',
      status: 'success',
      input: {},
      output: {
        status: 'approval_required',
        prepare_version: 'phase114.generate_chapter_execution_prepare.v1',
        chapter_index: 3,
        agent_plan: chapterAgentPlan,
        agent_plan_approval_contract: chapterApprovalContract,
        agent_plan_approval_contract_hash: 'approval:chapter-3',
        required_confirmation: {
          confirm_execute: true,
          approval_contract_hash: 'approval:chapter-3',
        },
        recommended_next_tools: ['execute_generate_chapter_with_approval'],
        side_effects: { executed: [], skipped: ['generate_chapter'] },
      },
    },
  ],
}

export const recommendedFollowupChapterExpectedExecutePayload: PlannerPlanExecutePayload = {
  sourceRunId: 'run-followup-exec',
  sourcePlanId: 'direct-generate:project-1:chapter:3',
  goal: '执行已审批工具：生成正文',
  tools: [
    {
      tool_name: 'execute_generate_chapter_with_approval',
      params: {
        chapter_index: 3,
        confirm_execute: true,
        approval_contract_hash: 'approval:chapter-3',
        approval_contract: chapterApprovalContract,
      },
      planner: {
        plan_id: 'direct-generate:project-1:chapter:3',
        planner_version: 'phase114.generate_chapter_execution_prepare.v1',
        mutability: 'write',
        requires_confirmation: true,
        reason: '确认执行已准备的写入工具。',
      },
    },
  ],
  planner: {
    ...chapterAgentPlan,
    approval_contract: chapterApprovalContract,
  },
  approvalContractHash: 'approval:chapter-3',
  approvalContract: chapterApprovalContract,
}
