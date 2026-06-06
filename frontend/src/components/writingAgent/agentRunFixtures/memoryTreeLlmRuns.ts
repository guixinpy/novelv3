import type { WritingAgentRunDetail } from '../../../api/types'

export type PlannerPlanExecutePayload = {
  sourceRunId: string
  sourcePlanId: string
  goal: string
  tools: Array<Record<string, unknown>>
  planner: Record<string, unknown>
  approvalContractHash?: string
  approvalContract?: Record<string, unknown>
}

export const memoryTreeLlmCandidateRun: WritingAgentRunDetail = {
  id: 'run-memory-tree-candidates',
  project_id: 'project-1',
  goal: '查看第2章记忆树 LLM 摘要候选',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-memory-tree-candidates',
      run_id: 'run-memory-tree-candidates',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'inspect_agent_memory_tree_llm_candidates',
      status: 'success',
      input: { chapter_index: 2, limit: 3 },
      output: {
        status: 'ready',
        filters: { chapter_index: 2, limit: 3 },
        summary: {
          candidate_traces: 2,
          ready_candidates: 2,
          materialized_candidates: 0,
          pending_candidates: 2,
        },
        candidates: [
          {
            trace_id: 'trace-secret-1',
            trace_status: 'success',
            chapter_index: 2,
            model: 'deepseek-chat',
            prompt_tokens: 101,
            completion_tokens: 66,
            summary_target: {
              level: 'chapter',
              scope_key: 'chapter:2',
              chapter_index: 2,
            },
            candidate: {
              summary: '顾衍保留灯塔旧回声线索，蓝焰证词仍待复核。',
              salient_terms: ['灯塔旧回声', '蓝焰证词'],
              open_questions: ['蓝焰证词是否可靠？'],
              source_coverage: ['chapter_content', 'outline'],
            },
            source_count: 3,
            source_chars: 848,
            quality_precheck_status: 'degraded',
            materialization: {
              status: 'pending',
              memory_type: 'memory_tree_chapter_summary',
              scope_key: 'chapter:2',
              chapter_index: 2,
              summary_hash_match: null,
              source: 'longform_memories',
            },
          },
          {
            trace_id: 'trace-secret-2',
            trace_status: 'success',
            chapter_index: 2,
            model: 'deepseek-chat',
            prompt_tokens: 88,
            completion_tokens: 55,
            summary_target: {
              level: 'chapter',
              scope_key: 'chapter:2',
              chapter_index: 2,
            },
            candidate: {
              summary: '空白信来源与灯塔暗道记录形成第二条摘要候选。',
              salient_terms: ['空白信来源', '灯塔暗道'],
              open_questions: ['灯塔暗道记录是否完整？'],
              source_coverage: ['chapter_content', 'storyline'],
            },
            source_count: 2,
            source_chars: 612,
            quality_precheck_status: 'ready',
            materialization: {
              status: 'pending',
              memory_type: 'memory_tree_chapter_summary',
              scope_key: 'chapter:2',
              chapter_index: 2,
              summary_hash_match: null,
              source: 'longform_memories',
            },
          },
        ],
        recommended_next_tool_calls: [
          {
            tool_name: 'prepare_record_agent_memory_tree_llm_candidate_summary',
            params: {
              candidate_trace_id: 'trace-secret-1',
              quality_chapter_index: 2,
              quality_query: '灯塔旧回声',
            },
            requires_confirmation: false,
          },
          {
            tool_name: 'prepare_record_agent_memory_tree_llm_candidate_summary',
            params: {
              candidate_trace_id: 'trace-secret-2',
              quality_chapter_index: 2,
              quality_query: '空白信来源',
            },
            requires_confirmation: false,
          },
        ],
      },
    },
  ],
}

export const memoryTreeLlmCandidateExpectedPreparePayload: PlannerPlanExecutePayload = {
  sourceRunId: 'run-memory-tree-candidates',
  sourcePlanId: 'memory-tree-llm-candidate-prepare:1',
  goal: '准备 Memory Tree 候选摘要审批：第2章 空白信来源',
  tools: [
    {
      tool_name: 'prepare_record_agent_memory_tree_llm_candidate_summary',
      params: {
        candidate_trace_id: 'trace-secret-2',
        quality_chapter_index: 2,
        quality_query: '空白信来源',
      },
      planner: {
        step_id: 'memory-tree-llm-candidate-prepare:1',
        plan_id: 'memory-tree-llm-candidate-prepare:1',
        mutability: 'read',
        requires_confirmation: false,
        reason: '准备 Memory Tree LLM 候选摘要审批，不直接写入 LongformMemory。',
      },
    },
  ],
  planner: {
    status: 'completed',
    intent_class: 'prepare_memory_tree_llm_candidate_summary',
    approval_contract: { status: 'not_required', write_steps: [] },
    trace: {
      plan_id: 'memory-tree-llm-candidate-prepare:1',
      selected_tools: ['prepare_record_agent_memory_tree_llm_candidate_summary'],
    },
    tools: [
      {
        tool_name: 'prepare_record_agent_memory_tree_llm_candidate_summary',
        params: {
          candidate_trace_id: 'trace-secret-2',
          quality_chapter_index: 2,
          quality_query: '空白信来源',
        },
        planner: {
          step_id: 'memory-tree-llm-candidate-prepare:1',
          plan_id: 'memory-tree-llm-candidate-prepare:1',
          mutability: 'read',
          requires_confirmation: false,
          reason: '准备 Memory Tree LLM 候选摘要审批，不直接写入 LongformMemory。',
        },
      },
    ],
  },
}

export const memoryTreeLlmMaterializedCandidateRun: WritingAgentRunDetail = {
  id: 'run-memory-tree-candidates-materialized',
  project_id: 'project-1',
  goal: '查看已物化候选',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-memory-tree-candidates-materialized',
      run_id: 'run-memory-tree-candidates-materialized',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'inspect_agent_memory_tree_llm_candidates',
      status: 'success',
      input: { chapter_index: 2, limit: 1 },
      output: {
        status: 'ready',
        filters: { chapter_index: 2, limit: 1 },
        summary: {
          candidate_traces: 1,
          ready_candidates: 1,
          materialized_candidates: 1,
          pending_candidates: 0,
        },
        candidates: [
          {
            trace_id: 'trace-materialized-secret',
            trace_status: 'success',
            chapter_index: 2,
            model: 'deepseek-chat',
            summary_target: {
              level: 'chapter',
              scope_key: 'chapter:2',
              chapter_index: 2,
            },
            candidate: {
              summary: '蓝焰证词已经写入 Memory Tree 章级摘要。',
              salient_terms: ['蓝焰证词'],
              open_questions: [],
              source_coverage: ['chapter_content'],
            },
            source_count: 1,
            source_chars: 120,
            quality_precheck_status: 'ready',
            materialization: {
              status: 'materialized',
              memory_type: 'memory_tree_chapter_summary',
              scope_key: 'chapter:2',
              chapter_index: 2,
              summary_hash_match: true,
              source: 'longform_memories',
            },
          },
        ],
        recommended_next_tool_calls: [],
      },
    },
  ],
}

const firstContract = {
  approval: { approval_contract_hash: 'approval-secret-1' },
  resource_binding: { target_id: 'trace-secret-1' },
}

const secondContract = {
  approval: { approval_contract_hash: 'approval-secret-2' },
  resource_binding: { target_id: 'trace-secret-2' },
}

const firstAgentPlan = {
  project_id: 'project-1',
  intent_class: 'record_agent_memory_tree_llm_candidate_summary',
  trace: {
    plan_id: 'memory-tree-batch-plan-1',
    planner_version: 'phase251.memory_tree_llm_candidate_summaries_batch_prepare.v1',
  },
  steps: [
    {
      tool_name: 'record_agent_memory_tree_llm_candidate_summary',
      params: { candidate_trace_id: 'trace-secret-1', chapter_index: 2 },
    },
  ],
}

const secondAgentPlan = {
  project_id: 'project-1',
  intent_class: 'record_agent_memory_tree_llm_candidate_summary',
  trace: {
    plan_id: 'memory-tree-batch-plan-2',
    planner_version: 'phase251.memory_tree_llm_candidate_summaries_batch_prepare.v1',
  },
  steps: [
    {
      tool_name: 'record_agent_memory_tree_llm_candidate_summary',
      params: { candidate_trace_id: 'trace-secret-2', chapter_index: 2 },
    },
  ],
}

const firstExecuteParams = {
  candidate_trace_id: 'trace-secret-1',
  quality_chapter_index: 2,
  quality_query: '灯塔旧回声',
  confirm_execute: true,
  approval_contract_hash: 'approval-secret-1',
  approval_contract: firstContract,
}

const secondExecuteParams = {
  candidate_trace_id: 'trace-secret-2',
  quality_chapter_index: 2,
  quality_query: '空白信来源',
  confirm_execute: true,
  approval_contract_hash: 'approval-secret-2',
  approval_contract: secondContract,
}

export const memoryTreeLlmBatchPrepareRun: WritingAgentRunDetail = {
  id: 'run-memory-tree-batch',
  project_id: 'project-1',
  goal: '批量准备 Memory Tree 候选摘要',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-memory-tree-batch',
      run_id: 'run-memory-tree-batch',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'prepare_record_agent_memory_tree_llm_candidate_summaries_batch',
      status: 'success',
      input: { candidate_trace_ids: ['trace-secret-1', 'trace-secret-2'] },
      output: {
        status: 'approval_required',
        prepare_version: 'phase251.memory_tree_llm_candidate_summaries_batch_prepare.v1',
        summary: {
          candidate_traces: 2,
          prepared_candidates: 2,
          skipped_candidates: 0,
        },
        candidate_preparations: [
          {
            summary_plan: {
              candidate_trace_id: 'trace-secret-1',
              chapter_index: 2,
              quality_chapter_index: 2,
              quality_query: '灯塔旧回声',
            },
            agent_plan: firstAgentPlan,
            agent_plan_approval_contract: firstContract,
            agent_plan_approval_contract_hash: 'approval-secret-1',
            recommended_next_tool_call: {
              tool_name: 'execute_record_agent_memory_tree_llm_candidate_summary_with_approval',
              params: firstExecuteParams,
              requires_confirmation: true,
            },
          },
          {
            summary_plan: {
              candidate_trace_id: 'trace-secret-2',
              chapter_index: 2,
              quality_chapter_index: 2,
              quality_query: '空白信来源',
            },
            agent_plan: secondAgentPlan,
            agent_plan_approval_contract: secondContract,
            agent_plan_approval_contract_hash: 'approval-secret-2',
            recommended_next_tool_call: {
              tool_name: 'execute_record_agent_memory_tree_llm_candidate_summary_with_approval',
              params: secondExecuteParams,
              requires_confirmation: true,
            },
          },
        ],
      },
    },
  ],
}

export const memoryTreeLlmBatchPrepareExpectedExecutePayload: PlannerPlanExecutePayload = {
  sourceRunId: 'run-memory-tree-batch',
  sourcePlanId: 'memory-tree-batch-plan-2',
  goal: '执行 Memory Tree 候选摘要写入：第2章 空白信来源',
  tools: [
    {
      tool_name: 'execute_record_agent_memory_tree_llm_candidate_summary_with_approval',
      params: secondExecuteParams,
      planner: {
        plan_id: 'memory-tree-batch-plan-2',
        planner_version: 'phase251.memory_tree_llm_candidate_summaries_batch_prepare.v1',
        mutability: 'write',
        requires_confirmation: true,
        reason: '确认执行已准备的 Memory Tree LLM 候选摘要写入。',
      },
    },
  ],
  planner: {
    ...secondAgentPlan,
    approval_contract: secondContract,
  },
  approvalContractHash: 'approval-secret-2',
  approvalContract: secondContract,
}

export const memoryTreeLlmBatchExecuteRun: WritingAgentRunDetail = {
  id: 'run-memory-tree-batch-execute',
  project_id: 'project-1',
  goal: '批量执行 Memory Tree 候选摘要写入',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-memory-tree-batch-execute',
      run_id: 'run-memory-tree-batch-execute',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval',
      status: 'success',
      input: { confirm_execute: true },
      output: {
        status: 'success',
        summary: {
          candidate_executions: 2,
          succeeded_candidates: 2,
          blocked_candidates: 0,
        },
        candidate_results: [
          {
            candidate_index: 1,
            status: 'success',
            materialization: {
              summary: { created_nodes: 1, updated_nodes: 0 },
              nodes: [
                {
                  chapter_index: 1,
                  title: '雨巷空白信',
                },
              ],
            },
            post_materialization_quality: {
              status: 'degraded',
            },
          },
          {
            candidate_index: 2,
            status: 'success',
            materialization: {
              summary: { created_nodes: 1, updated_nodes: 0 },
              nodes: [
                {
                  chapter_index: 2,
                  title: '灯塔旧回声',
                },
              ],
            },
            post_materialization_quality: {
              status: 'ready',
            },
          },
        ],
      },
    },
  ],
}
