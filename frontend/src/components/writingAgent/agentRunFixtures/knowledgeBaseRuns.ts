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

const knowledgeBaseCandidateParams = {
  memory_type: 'writing_pattern',
  title: '第3章写作沉淀：雾港追踪',
  summary: '第3章结尾形成雾港追踪线索，后续章节应延续。',
  source_refs: ['chapter_content:chapter-content-3'],
  confidence: 0.72,
  status: 'candidate',
  tags: ['post-chapter-capture', 'chapter:3'],
}

const knowledgeBaseCandidateApprovalContract = {
  status: 'requires_confirmation',
  approval: { approval_contract_hash: 'approval:candidate-secret' },
}

const knowledgeBaseCandidateAgentPlan = {
  project_id: 'project-1',
  intent_class: 'record_agent_knowledge_base_candidate',
  trace: {
    plan_id: 'knowledge-base-candidate:project-1:abc123',
    planner_version: 'phase189.knowledge_base_candidate_prepare.v1',
  },
  steps: [
    {
      step_index: 1,
      step_id: 'knowledge-base-candidate:project-1:abc123',
      tool_name: 'record_agent_knowledge_base_candidate',
      approval_executor_tool_name: 'execute_record_agent_knowledge_base_candidate_with_approval',
      params: knowledgeBaseCandidateParams,
      mutability: 'write',
      requires_confirmation: true,
      reason: '记录长期写作知识库候选项。',
    },
  ],
}

export const postChapterMemoryProjectionRun: WritingAgentRunDetail = {
  id: 'run-post-memory-projection',
  project_id: 'project-1',
  goal: '规划第3章写后记忆沉淀',
  status: 'success',
  entrypoint: 'ui_memory_tree_workspace_post_chapter_capture',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-post-memory-projection',
      run_id: 'run-post-memory-projection',
      project_id: 'project-1',
      step_index: 0,
      tool_name: 'plan_post_chapter_memory_capture',
      status: 'success',
      input: { chapter_index: 3 },
      output: {
        status: 'completed',
        chapter_index: 3,
        capture_status: 'ready',
        summary: {
          chapter_available: true,
          review_step_count: 2,
          candidate_count: 2,
        },
        candidates: [
          {
            memory_type: 'writing_pattern',
            title: '第3章写作沉淀：雾港追踪',
            summary: '第3章结尾形成雾港追踪线索，后续章节应延续。',
            confidence: 0.72,
            evidence: {
              chapter_index: 3,
            },
          },
          {
            memory_type: 'self_optimization_lesson',
            title: '第3章审稿经验：雾港追踪',
            summary: 'medium pacing_issue: 中段节奏松散。后续生成应优先避免这些重复问题。',
            confidence: 0.78,
            evidence: {
              chapter_index: 3,
            },
          },
        ],
        recommended_next_tools: ['prepare_record_agent_knowledge_base_candidate'],
        memory_provenance: {
          version: 'phase242.post_chapter_memory_capture.v1',
          status: 'available',
        },
      },
    },
  ],
}

export const postChapterMemoryCaptureRun: WritingAgentRunDetail = {
  id: 'run-post-memory-capture',
  project_id: 'project-1',
  goal: '规划第3章写后记忆沉淀',
  status: 'success',
  entrypoint: 'ui_memory_tree_workspace_post_chapter_capture',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-post-memory',
      run_id: 'run-post-memory-capture',
      project_id: 'project-1',
      step_index: 0,
      tool_name: 'plan_post_chapter_memory_capture',
      status: 'success',
      input: { chapter_index: 3 },
      output: {
        status: 'completed',
        chapter_index: 3,
        capture_status: 'ready',
        summary: {
          chapter_available: true,
          review_step_count: 1,
          candidate_count: 1,
        },
        candidates: [
          {
            memory_type: 'writing_pattern',
            title: '第3章写作沉淀：雾港追踪',
            evidence: { chapter_content_id: 'chapter-content-3' },
            next_tool_call: {
              tool_name: 'prepare_record_agent_knowledge_base_candidate',
              params: knowledgeBaseCandidateParams,
            },
          },
        ],
        recommended_next_tools: ['prepare_record_agent_knowledge_base_candidate'],
      },
    },
  ],
}

export const postChapterMemoryCandidateExpectedPreparePayload: PlannerPlanExecutePayload = {
  sourceRunId: 'run-post-memory-capture',
  sourcePlanId: 'post-memory-candidate-prepare:0',
  goal: '准备写后记忆候选审批：第3章写作沉淀：雾港追踪',
  tools: [
    {
      tool_name: 'prepare_record_agent_knowledge_base_candidate',
      params: knowledgeBaseCandidateParams,
      planner: {
        step_id: 'post-memory-candidate-prepare:0',
        plan_id: 'post-memory-candidate-prepare:0',
        mutability: 'read',
        requires_confirmation: false,
        reason: '准备写后记忆候选审批，不直接写入知识库。',
      },
    },
  ],
  planner: {
    status: 'completed',
    intent_class: 'prepare_knowledge_base_candidate',
    approval_contract: { status: 'not_required', write_steps: [] },
    trace: {
      plan_id: 'post-memory-candidate-prepare:0',
      selected_tools: ['prepare_record_agent_knowledge_base_candidate'],
    },
    tools: [
      {
        tool_name: 'prepare_record_agent_knowledge_base_candidate',
        params: knowledgeBaseCandidateParams,
        planner: {
          step_id: 'post-memory-candidate-prepare:0',
          plan_id: 'post-memory-candidate-prepare:0',
          mutability: 'read',
          requires_confirmation: false,
          reason: '准备写后记忆候选审批，不直接写入知识库。',
        },
      },
    ],
  },
}

export const knowledgeBaseCandidatePrepareRun: WritingAgentRunDetail = {
  id: 'run-candidate-prepare',
  project_id: 'project-1',
  goal: '准备写后记忆候选审批',
  status: 'success',
  entrypoint: 'ui_planner_continuation_execute',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-candidate-prepare',
      run_id: 'run-candidate-prepare',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'prepare_record_agent_knowledge_base_candidate',
      status: 'success',
      input: knowledgeBaseCandidateParams,
      output: {
        status: 'approval_required',
        prepare_version: 'phase189.knowledge_base_candidate_prepare.v1',
        target_type: 'agent_knowledge_base_candidate',
        agent_plan: knowledgeBaseCandidateAgentPlan,
        agent_plan_approval_contract: knowledgeBaseCandidateApprovalContract,
        agent_plan_approval_contract_hash: 'approval:candidate-secret',
        required_confirmation: {
          confirm_execute: true,
          approval_contract_hash: 'approval:candidate-secret',
        },
        recommended_next_tools: ['execute_record_agent_knowledge_base_candidate_with_approval'],
        side_effects: { executed: [], skipped: ['record_agent_knowledge_base_candidate'] },
      },
    },
  ],
}

export const knowledgeBaseCandidateExpectedExecutePayload: PlannerPlanExecutePayload = {
  sourceRunId: 'run-candidate-prepare',
  sourcePlanId: 'knowledge-base-candidate:project-1:abc123',
  goal: '执行已审批工具：写入知识库候选',
  tools: [
    {
      tool_name: 'execute_record_agent_knowledge_base_candidate_with_approval',
      params: {
        ...knowledgeBaseCandidateParams,
        confirm_execute: true,
        approval_contract_hash: 'approval:candidate-secret',
        approval_contract: knowledgeBaseCandidateApprovalContract,
      },
      planner: {
        plan_id: 'knowledge-base-candidate:project-1:abc123',
        planner_version: 'phase189.knowledge_base_candidate_prepare.v1',
        mutability: 'write',
        requires_confirmation: true,
        reason: '确认执行已准备的写入工具。',
      },
    },
  ],
  planner: {
    ...knowledgeBaseCandidateAgentPlan,
    approval_contract: knowledgeBaseCandidateApprovalContract,
  },
  approvalContractHash: 'approval:candidate-secret',
  approvalContract: knowledgeBaseCandidateApprovalContract,
}

export const knowledgeBaseCandidateExecuteRun: WritingAgentRunDetail = {
  id: 'run-candidate-execute',
  project_id: 'project-1',
  goal: '执行已审批知识库候选写入',
  status: 'success',
  entrypoint: 'ui_planner_continuation_execute',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-candidate-execute',
      run_id: 'run-candidate-execute',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'execute_record_agent_knowledge_base_candidate_with_approval',
      status: 'success',
      input: {
        title: '第3章写作沉淀：雾港追踪',
        approval_contract_hash: 'approval:candidate-secret',
      },
      output: {
        status: 'success',
        execute_version: 'phase189.knowledge_base_candidate_with_approval_execute.v1',
        target_type: 'agent_knowledge_base_candidate',
        candidate_count: 1,
        candidate: {
          id: 'candidate-secret-id',
          title: '第3章写作沉淀：雾港追踪',
          memory_type: 'writing_pattern',
          source_refs: ['chapter_content:chapter-content-3'],
        },
        side_effects: { executed: ['record_agent_knowledge_base_candidate'], skipped: [] },
        recommended_next_tools: ['inspect_agent_knowledge_base_route'],
        agent_plan_approval_verification: {
          status: 'ready',
          approval_contract_hash: 'approval:candidate-secret',
        },
      },
    },
  ],
}

export const knowledgeBaseCandidateExecuteRouteRun: WritingAgentRunDetail = {
  id: 'run-candidate-execute-route',
  project_id: 'project-1',
  goal: '执行已审批知识库候选写入',
  status: 'success',
  entrypoint: 'ui_planner_continuation_execute',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-candidate-execute',
      run_id: 'run-candidate-execute-route',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'execute_record_agent_knowledge_base_candidate_with_approval',
      status: 'success',
      input: {
        title: '第3章写作沉淀：雾港追踪',
        approval_contract_hash: 'approval:candidate-secret',
      },
      output: {
        status: 'success',
        candidate_count: 1,
        candidate: {
          id: 'candidate-secret-id',
          title: '第3章写作沉淀：雾港追踪',
          memory_type: 'writing_pattern',
          chapter_index: 3,
          source_refs: ['chapter_content:chapter-content-3'],
        },
        recommended_next_tools: ['inspect_agent_knowledge_base_route'],
        agent_plan_approval_verification: {
          status: 'ready',
          approval_contract_hash: 'approval:candidate-secret',
        },
      },
    },
  ],
}

export const knowledgeBaseCandidateRouteExpectedPayload: PlannerPlanExecutePayload = {
  sourceRunId: 'run-candidate-execute-route',
  sourcePlanId: 'knowledge-candidate-route:0',
  goal: '检查知识库写入结果：第3章写作沉淀：雾港追踪',
  tools: [
    {
      tool_name: 'inspect_agent_knowledge_base_route',
      params: {
        chapter_index: 3,
        query: '第3章写作沉淀：雾港追踪',
        limit: 8,
      },
      planner: {
        step_id: 'knowledge-candidate-route:0',
        plan_id: 'knowledge-candidate-route:0',
        mutability: 'read',
        requires_confirmation: false,
      },
    },
  ],
  planner: {
    status: 'completed',
    intent_class: 'inspect_knowledge_base_route',
    approval_contract: { status: 'not_required', write_steps: [] },
    trace: {
      plan_id: 'knowledge-candidate-route:0',
      selected_tools: ['inspect_agent_knowledge_base_route'],
    },
    tools: [
      {
        tool_name: 'inspect_agent_knowledge_base_route',
        params: {
          chapter_index: 3,
          query: '第3章写作沉淀：雾港追踪',
          limit: 8,
        },
        planner: {
          step_id: 'knowledge-candidate-route:0',
          plan_id: 'knowledge-candidate-route:0',
          mutability: 'read',
          requires_confirmation: false,
        },
      },
    ],
  },
}

export const knowledgeBaseRouteRun: WritingAgentRunDetail = {
  id: 'run-knowledge-base-route',
  project_id: 'project-1',
  goal: '检查知识库路由',
  status: 'success',
  entrypoint: 'ui_memory_tree_workspace_knowledge_base',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-knowledge-base-route',
      run_id: 'run-knowledge-base-route',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'inspect_agent_knowledge_base_route',
      status: 'success',
      input: { chapter_index: 3, query: '雾港追踪写法', limit: 2 },
      output: {
        status: 'completed',
        chapter_index: 3,
        query: '雾港追踪写法',
        route: {
          status: 'ready',
          can_inform_generation: true,
          recommended_tools: [
            'summarize_longform_context',
            'preflight_writing',
          ],
        },
        author_preferences: {
          facets: [{ key: 'tone_preferences', value: ['冷峻', '悬疑'] }],
        },
        learned_rules: {
          total: 3,
          returned: 2,
          items: [
            {
              condition: '用户反馈章节像大纲',
              action: '增加场景动作和角色即时反应',
            },
          ],
        },
        knowledge_candidates: {
          total: 2,
          returned: 1,
          items: [
            {
              title: '雾港追踪写法',
              memory_type: 'writing_pattern',
              summary: '使用冷峻短句和章末行动压力。',
            },
          ],
        },
        reference_patterns: {
          returned: 2,
        },
        diagnostics: [
          {
            message: '知识库是作者偏好、项目策略和写法经验，不是 Athena 世界真相。',
          },
        ],
      },
    },
  ],
}
