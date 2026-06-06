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

export const memoryTreeProjectionRun: WritingAgentRunDetail = {
  id: 'run-memory-tree',
  project_id: 'project-1',
  goal: '浏览记忆树中的灯塔旧回声',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-memory-tree',
      run_id: 'run-memory-tree',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'inspect_agent_memory_tree',
      status: 'success',
      input: { query: '灯塔旧回声', include_ancestors: true },
      output: {
        status: 'ready',
        levels: ['volume', 'chapter', 'scene', 'beat'],
        filters: {
          level: 'chapter',
          query: '灯塔旧回声',
          include_ancestors: true,
        },
        summary: {
          volume_nodes: 1,
          chapter_nodes: 12,
          scene_nodes: 18,
          beat_nodes: 42,
        },
        navigation: {
          mode: 'semantic_search_with_ancestors',
          matched_node_ids: ['chapter:2'],
          ancestor_node_ids: ['volume:1'],
          recommended_drilldowns: [
            {
              node_id: 'chapter:2',
              expand_node_id: 'chapter:2',
              reason: 'highest_relevance',
              score: 1.2,
            },
          ],
        },
        nodes: [
          {
            id: 'volume:1',
            level: 'volume',
            parent_id: null,
            chapter_index: null,
            title: 'Volume 1',
            summary: '雾港开篇卷。',
            source_refs: [{ source_type: 'outline', source_id: 'outline-1' }],
            children: ['chapter:2'],
          },
          {
            id: 'chapter:2',
            level: 'chapter',
            parent_id: 'volume:1',
            chapter_index: 2,
            title: '灯塔旧回声',
            summary: '主角在灯塔发现旧回声线索。',
            source_refs: [
              { source_type: 'chapter_content', source_id: 'chapter-content-2' },
              { source_type: 'longform_memory', source_id: 'memory-2' },
            ],
            children: [],
            relevance: {
              score: 1.2,
              matched_terms: ['灯', '塔', '旧', '回', '声'],
            },
          },
          {
            id: 'scene:memory-3',
            level: 'scene',
            parent_id: 'chapter:2',
            chapter_index: 2,
            summary: '补充场景摘要。',
            source_refs: [{ source_type: 'longform_memory', source_id: 'memory-3' }],
            children: [],
          },
        ],
        trace: {
          source_tables: ['chapter_contents', 'longform_memories'],
        },
      },
    },
  ],
}

export const memoryTreeDrilldownRun: WritingAgentRunDetail = {
  id: 'run-memory-tree',
  project_id: 'project-1',
  goal: '浏览记忆树中的灯塔旧回声',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-memory-tree',
      run_id: 'run-memory-tree',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'inspect_agent_memory_tree',
      status: 'success',
      input: { query: '灯塔旧回声', include_ancestors: true },
      output: {
        status: 'ready',
        filters: {
          query: '灯塔旧回声',
          include_ancestors: true,
        },
        navigation: {
          mode: 'semantic_search_with_ancestors',
          recommended_drilldowns: [
            {
              node_id: 'chapter:2',
              expand_node_id: 'chapter:2',
              reason: 'highest_relevance',
              score: 1.2,
            },
          ],
        },
        nodes: [
          {
            id: 'chapter:2',
            level: 'chapter',
            chapter_index: 2,
            title: '灯塔旧回声',
            summary: '主角在灯塔发现旧回声线索。',
            children: ['scene:memory-3'],
          },
        ],
      },
    },
  ],
}

export const memoryTreeDrilldownExpectedPayload: PlannerPlanExecutePayload = {
  sourceRunId: 'run-memory-tree',
  sourcePlanId: 'memory-tree-drilldown:0',
  goal: '展开 Memory Tree：灯塔旧回声',
  tools: [
    {
      tool_name: 'inspect_agent_memory_tree',
      params: {
        expand_node_id: 'chapter:2',
        include_ancestors: true,
        max_depth: 1,
      },
      planner: {
        step_id: 'memory-tree-drilldown:0',
        plan_id: 'memory-tree-drilldown:0',
        mutability: 'read',
        requires_confirmation: false,
      },
    },
  ],
  planner: {
    status: 'completed',
    intent_class: 'inspect_memory_tree',
    approval_contract: { status: 'not_required', write_steps: [] },
    trace: {
      plan_id: 'memory-tree-drilldown:0',
      selected_tools: ['inspect_agent_memory_tree'],
    },
    tools: [
      {
        tool_name: 'inspect_agent_memory_tree',
        params: {
          expand_node_id: 'chapter:2',
          include_ancestors: true,
          max_depth: 1,
        },
        planner: {
          step_id: 'memory-tree-drilldown:0',
          plan_id: 'memory-tree-drilldown:0',
          mutability: 'read',
          requires_confirmation: false,
        },
      },
    ],
  },
}

export const memoryTreeNodeExpandRun: WritingAgentRunDetail = {
  id: 'run-memory-tree-node-expand',
  project_id: 'project-1',
  goal: '浏览记忆树节点',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-memory-tree',
      run_id: 'run-memory-tree-node-expand',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'inspect_agent_memory_tree',
      status: 'success',
      input: {},
      output: {
        status: 'ready',
        filters: {},
        navigation: { mode: 'filtered' },
        nodes: [
          {
            id: 'scene:memory-3',
            level: 'scene',
            parent_id: 'chapter:2',
            chapter_index: 2,
            summary: '补充场景摘要。',
            children: ['beat:memory-4'],
          },
        ],
      },
    },
  ],
}

export const memoryTreeNodeExpandExpectedPayload: PlannerPlanExecutePayload = {
  sourceRunId: 'run-memory-tree-node-expand',
  sourcePlanId: 'memory-tree-node-expand:0',
  goal: '展开 Memory Tree：第2章',
  tools: [
    {
      tool_name: 'inspect_agent_memory_tree',
      params: {
        expand_node_id: 'scene:memory-3',
        include_ancestors: true,
        max_depth: 1,
      },
      planner: {
        step_id: 'memory-tree-node-expand:0',
        plan_id: 'memory-tree-node-expand:0',
        mutability: 'read',
        requires_confirmation: false,
      },
    },
  ],
  planner: {
    status: 'completed',
    intent_class: 'inspect_memory_tree',
    approval_contract: { status: 'not_required', write_steps: [] },
    trace: {
      plan_id: 'memory-tree-node-expand:0',
      selected_tools: ['inspect_agent_memory_tree'],
    },
    tools: [
      {
        tool_name: 'inspect_agent_memory_tree',
        params: {
          expand_node_id: 'scene:memory-3',
          include_ancestors: true,
          max_depth: 1,
        },
        planner: {
          step_id: 'memory-tree-node-expand:0',
          plan_id: 'memory-tree-node-expand:0',
          mutability: 'read',
          requires_confirmation: false,
        },
      },
    ],
  },
}

export const memoryTreeResultHistory = [
  {
    key: 'run-memory-tree-result:memory-tree-node-expand:0',
    label: '节点展开：第2章',
  },
]

export const memoryTreeResultRun: WritingAgentRunDetail = {
  id: 'run-memory-tree-result',
  project_id: 'project-1',
  goal: '展开 Memory Tree：第2章',
  status: 'success',
  entrypoint: 'ui_planner_continuation_execute',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-memory-tree',
      run_id: 'run-memory-tree-result',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'inspect_agent_memory_tree',
      status: 'success',
      input: {
        expand_node_id: 'scene:memory-3',
        include_ancestors: true,
        max_depth: 1,
      },
      output: {
        status: 'ready',
        filters: {},
        navigation: { mode: 'expanded_subtree' },
        nodes: [
          {
            id: 'scene:memory-3',
            level: 'scene',
            chapter_index: 2,
            summary: '补充场景摘要。',
            children: ['beat:memory-4'],
          },
        ],
      },
    },
  ],
}

export const memoryTreeSearchRun: WritingAgentRunDetail = {
  id: 'run-memory-tree-search',
  project_id: 'project-1',
  goal: '浏览记忆树',
  status: 'success',
  entrypoint: 'dialog_auto_plan',
  input: {},
  output: null,
  error: null,
  steps: [
    {
      id: 'step-memory-tree',
      run_id: 'run-memory-tree-search',
      project_id: 'project-1',
      step_index: 1,
      tool_name: 'inspect_agent_memory_tree',
      status: 'success',
      input: {},
      output: {
        status: 'ready',
        filters: {},
        navigation: { mode: 'filtered' },
        nodes: [
          {
            id: 'volume:1',
            level: 'volume',
            title: 'Volume 1',
            summary: '雾港开篇卷。',
          },
        ],
      },
    },
  ],
}

export const memoryTreeSearchExpectedPayload: PlannerPlanExecutePayload = {
  sourceRunId: 'run-memory-tree-search',
  sourcePlanId: 'memory-tree-search:manual',
  goal: '搜索 Memory Tree：雨巷伏笔',
  tools: [
    {
      tool_name: 'inspect_agent_memory_tree',
      params: {
        query: '雨巷伏笔',
        include_ancestors: true,
      },
      planner: {
        step_id: 'memory-tree-search:manual',
        plan_id: 'memory-tree-search:manual',
        mutability: 'read',
        requires_confirmation: false,
      },
    },
  ],
  planner: {
    status: 'completed',
    intent_class: 'inspect_memory_tree',
    approval_contract: { status: 'not_required', write_steps: [] },
    trace: {
      plan_id: 'memory-tree-search:manual',
      selected_tools: ['inspect_agent_memory_tree'],
    },
    tools: [
      {
        tool_name: 'inspect_agent_memory_tree',
        params: {
          query: '雨巷伏笔',
          include_ancestors: true,
        },
        planner: {
          step_id: 'memory-tree-search:manual',
          plan_id: 'memory-tree-search:manual',
          mutability: 'read',
          requires_confirmation: false,
        },
      },
    ],
  },
}
