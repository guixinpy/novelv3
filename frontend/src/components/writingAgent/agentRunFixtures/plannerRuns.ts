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

const writePlannerApprovalContract = {
  status: 'requires_confirmation',
  approval: { approval_contract_hash: 'approval:secret' },
  write_steps: [{ tool_name: 'generate_chapter' }],
}

const routeUpgradeApprovalContract = {
  approval: { approval_contract_hash: 'approval:secret' },
}

const readPlannerOutput = {
  status: 'completed',
  planner_version: 'phase53.context_gate.v1',
  intent_class: 'review_chapter',
  chapter_index: 12,
  approval_contract: { status: 'not_required', write_steps: [] },
  trace: { plan_id: 'plan:review-12', selected_tools: ['review_chapter_quality'] },
  tools: [
    {
      tool_name: 'review_chapter_quality',
      params: { chapter_index: 12 },
      planner: {
        step_id: 'step:review-quality',
        plan_id: 'plan:review-12',
        mutability: 'read',
        requires_confirmation: false,
      },
    },
  ],
}

const writePlannerOutput = {
  status: 'completed',
  intent_class: 'continue_next_chapter',
  approval_contract: writePlannerApprovalContract,
  trace: { plan_id: 'plan:chapter-2' },
  tools: [
    {
      tool_name: 'generate_chapter',
      params: { chapter_index: 2 },
      planner: {
        step_id: 'step:generate-chapter-2',
        plan_id: 'plan:chapter-2',
        mutability: 'write',
        requires_confirmation: true,
      },
    },
  ],
}

export const readPlannerPreviewRun: WritingAgentRunDetail = {
  id: 'run-plan-preview',
  project_id: 'project-1',
  goal: '规划审稿第12章',
  status: 'success',
  entrypoint: 'manual_debug_run',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-plan',
      run_id: 'run-plan-preview',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'plan_writing_agent_run',
      status: 'success',
      input: {},
      output: readPlannerOutput,
    },
  ],
}

export const readPlannerExpectedExecutePayload: PlannerPlanExecutePayload = {
  sourceRunId: 'run-plan-preview',
  sourcePlanId: 'plan:review-12',
  goal: '执行规划工具链：审稿章节',
  tools: readPlannerOutput.tools,
  planner: readPlannerOutput,
}

export const writePlannerPreviewRun: WritingAgentRunDetail = {
  id: 'run-plan-write-preview',
  project_id: 'project-1',
  goal: '规划生成第2章',
  status: 'success',
  entrypoint: 'manual_debug_run',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-plan',
      run_id: 'run-plan-write-preview',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'plan_writing_agent_run',
      status: 'success',
      input: {},
      output: writePlannerOutput,
    },
  ],
}

export const writePlannerExpectedExecutePayload: PlannerPlanExecutePayload = {
  sourceRunId: 'run-plan-write-preview',
  sourcePlanId: 'plan:chapter-2',
  goal: '执行规划工具链：续写章节',
  tools: writePlannerOutput.tools,
  planner: writePlannerOutput,
  approvalContractHash: 'approval:secret',
  approvalContract: writePlannerApprovalContract,
}

export const writePlannerMissingHashRun: WritingAgentRunDetail = {
  id: 'run-plan-write-preview',
  project_id: 'project-1',
  goal: '规划生成设定',
  status: 'success',
  entrypoint: 'manual_debug_run',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-plan',
      run_id: 'run-plan-write-preview',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'plan_writing_agent_run',
      status: 'success',
      input: {},
      output: {
        status: 'completed',
        intent_class: 'setup_project',
        approval_contract: {
          status: 'requires_confirmation',
          approval: {},
          write_steps: [{ tool_name: 'generate_setup' }],
        },
        trace: { plan_id: 'plan:setup' },
        tools: [{ tool_name: 'generate_setup', params: {} }],
      },
    },
  ],
}

export const routeUpgradeEligibleContractRun: WritingAgentRunDetail = {
  id: 'run-contract',
  project_id: 'project-1',
  goal: '生成待确认操作的路由升级审批契约',
  status: 'success',
  entrypoint: 'pending_action_safety_action',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-contract',
      run_id: 'run-contract',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'preview_pending_action_route_approval_opt_in_apply_contract',
      status: 'success',
      input: {},
      output: {
        status: 'requires_confirmation',
        required_confirmation: true,
        pending_action_id: 'action-1',
        approval_contract_hash: 'approval:secret',
        approval_contract: routeUpgradeApprovalContract,
        recommended_next_tools: ['apply_pending_action_route_approval_opt_in'],
      },
    },
  ],
}

export const routeUpgradeExpectedApplyPayload = {
  sourceRunId: 'run-contract',
  pendingActionId: 'action-1',
  approvalContractHash: 'approval:secret',
  approvalContract: routeUpgradeApprovalContract,
}

export const routeUpgradeNotRequiredRun: WritingAgentRunDetail = {
  id: 'run-contract',
  project_id: 'project-1',
  goal: '无需升级',
  status: 'success',
  entrypoint: 'pending_action_safety_action',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-contract',
      run_id: 'run-contract',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'preview_pending_action_route_approval_opt_in_apply_contract',
      status: 'success',
      input: {},
      output: {
        status: 'not_required',
        required_confirmation: false,
        pending_action_id: 'action-1',
        recommended_next_tools: [],
      },
    },
  ],
}

export const routeUpgradeStaleContractRun: WritingAgentRunDetail = {
  id: 'run-contract',
  project_id: 'project-1',
  goal: '生成待确认操作的路由升级审批契约',
  status: 'success',
  entrypoint: 'manual_debug_run',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-contract',
      run_id: 'run-contract',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'preview_pending_action_route_approval_opt_in_apply_contract',
      status: 'success',
      input: {},
      output: {
        status: 'requires_confirmation',
        required_confirmation: true,
        pending_action_id: 'action-stale',
        approval_contract_hash: 'approval:secret',
        approval_contract: routeUpgradeApprovalContract,
        recommended_next_tools: ['apply_pending_action_route_approval_opt_in'],
      },
    },
  ],
}
