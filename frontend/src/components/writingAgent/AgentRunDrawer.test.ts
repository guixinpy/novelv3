// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it } from 'vitest'
import AgentRunDrawer from './AgentRunDrawer.vue'

describe('AgentRunDrawer', () => {
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('renders writing agent run detail and steps', () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-1',
          project_id: 'project-1',
          goal: '恢复上一轮阻塞',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-1',
              run_id: 'run-1',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'describe_agent_tools',
              status: 'success',
              input: {},
              output: {},
            },
            {
              id: 'step-2',
              run_id: 'run-1',
              project_id: 'project-1',
              step_index: 2,
              tool_name: 'plan_recovery_tools',
              status: 'success',
              input: {},
              output: {},
            },
          ],
        },
      },
    })

    expect(document.body.textContent).toContain('恢复上一轮阻塞')
    expect(document.body.textContent).toContain('success')
    expect(document.body.textContent).toContain('run-1')
    expect(document.body.textContent).toContain('describe_agent_tools')
    expect(document.body.textContent).toContain('plan_recovery_tools')

    const refresh = document.body.querySelector('[data-testid="refresh-agent-run"]') as HTMLButtonElement
    expect(refresh).not.toBeNull()
    refresh.click()
    expect(wrapper.emitted('refresh')).toEqual([[]])
  })

  it('renders execution plan progress from planned tools and current steps', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-progress',
          project_id: 'project-1',
          goal: '执行章节生成工具链',
          status: 'running',
          entrypoint: 'ui_planner_continuation_execute',
          input: {
            tools: [
              { tool_name: 'summarize_longform_context' },
              { tool_name: 'preflight_writing' },
              { tool_name: 'prepare_generate_chapter_execution' },
            ],
          },
          output: null,
          error: null,
          steps: [
            {
              id: 'step-summary',
              run_id: 'run-progress',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'summarize_longform_context',
              status: 'success',
              input: {},
              output: {},
            },
            {
              id: 'step-preflight',
              run_id: 'run-progress',
              project_id: 'project-1',
              step_index: 2,
              tool_name: 'preflight_writing',
              status: 'running',
              input: {},
              output: {},
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('执行计划')
    expect(text).toContain('计划工具')
    expect(text).toContain('3 个')
    expect(text).toContain('已执行')
    expect(text).toContain('2 / 3')
    expect(text).toContain('已完成')
    expect(text).toContain('1 个')
    expect(text).toContain('进行中')
    expect(text).toContain('1 个')
    expect(text).toContain('下一步')
    expect(text).toContain('prepare_generate_chapter_execution')
  })

  it('renders per-tool execution status for planned tools', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-progress-list',
          project_id: 'project-1',
          goal: '执行章节生成工具链',
          status: 'running',
          entrypoint: 'ui_planner_continuation_execute',
          input: {
            tools: [
              { tool_name: 'summarize_longform_context' },
              { tool_name: 'preflight_writing' },
              { tool_name: 'prepare_generate_chapter_execution' },
            ],
          },
          output: null,
          error: null,
          steps: [
            {
              id: 'step-summary',
              run_id: 'run-progress-list',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'summarize_longform_context',
              status: 'success',
              input: {},
              output: {},
            },
            {
              id: 'step-preflight',
              run_id: 'run-progress-list',
              project_id: 'project-1',
              step_index: 2,
              tool_name: 'preflight_writing',
              status: 'running',
              input: {},
              output: {},
            },
          ],
        },
      },
    })

    const rows = Array.from(document.body.querySelectorAll('[data-testid="execution-plan-tool"]'))
    expect(rows).toHaveLength(3)
    expect(rows[0].textContent).toContain('summarize_longform_context')
    expect(rows[0].textContent).toContain('已完成')
    expect(rows[1].textContent).toContain('preflight_writing')
    expect(rows[1].textContent).toContain('进行中')
    expect(rows[2].textContent).toContain('prepare_generate_chapter_execution')
    expect(rows[2].textContent).toContain('待执行')
  })

  it('renders agent profile scoped tool discovery summary', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-profile',
          project_id: 'project-1',
          goal: '继续写下一章',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          agent_profile: 'drafting_worker',
          agent_profile_definition: {
            version: 'phase212.agent_profile_definition.v1',
            profile: 'drafting_worker',
            display_name: '创作执行者',
            role: 'worker',
            tier: 'worker',
            delegation_allowed: false,
            source: 'planner_trace',
          },
          agent_tool_discovery: {
            version: 'phase210.agent_tool_discovery_projection.v1',
            scope_applied: true,
            scope_source: 'agent_profile',
            requested_profile: 'drafting_worker',
            effective_profile: 'drafting_worker',
            visible_tool_count: 12,
            filtered_by_profile_count: 7,
            filter_stages: ['profile'],
          },
          steps: [],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Agent 身份')
    expect(text).toContain('创作执行者')
    expect(text).toContain('编排层级')
    expect(text).toContain('worker')
    expect(text).toContain('委派')
    expect(text).toContain('不可委派')
    expect(text).toContain('工具面')
    expect(text).toContain('已按身份收窄')
    expect(text).toContain('可见工具')
    expect(text).toContain('12')
    expect(text).toContain('已过滤')
    expect(text).toContain('7')
  })

  it('renders declared delegate profile targets for orchestrator runs', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-orchestrator',
          project_id: 'project-1',
          goal: '编排下一轮写作',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          agent_profile: 'orchestrator',
          agent_profile_definition: {
            version: 'phase212.agent_profile_definition.v1',
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
          steps: [],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Agent 身份')
    expect(text).toContain('编排主控')
    expect(text).toContain('委派')
    expect(text).toContain('可委派')
    expect(text).toContain('可委派目标')
    expect(text).toContain('4 个声明')
  })

  it('renders profile policy audit summary', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-audit',
          project_id: 'project-1',
          goal: '检查 profile 策略',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          agent_profile: 'orchestrator',
          agent_profile_policy_audit: {
            version: 'phase215.agent_profile_policy_audit.v1',
            status: 'passed',
            summary: { issues: 0, delegate_edges: 4 },
            issues: [
              {
                code: 'delegate_target_missing_definition',
                profile: 'orchestrator',
                target: 'ghost_worker',
              },
            ],
          },
          steps: [],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('策略审计')
    expect(text).toContain('通过')
    expect(text).not.toContain('delegate_target_missing_definition')
    expect(text).not.toContain('ghost_worker')
  })

  it('renders command contract summary', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-command-contracts',
          project_id: 'project-1',
          goal: '检查命令契约',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          agent_command_contracts: {
            source: 'planner_trace.agent_health_projection.command_contracts',
            summary: {
              total_commands: 8,
              public_commands: 5,
              agent_control_commands: 2,
              available_commands: 5,
              gap_count: 0,
            },
          },
          agent_control_plane_readiness: {
            source: 'planner_trace.agent_health_projection.control_plane_readiness',
            status: 'ready',
            version: 'phase46.agent_control_plane_readiness.v1',
            summary: {
              total_gap_count: 0,
              tool_gap_count: 0,
              command_gap_count: 0,
            },
            recommended_next_tools: ['inspect_agent_health_projection'],
          },
          agent_worker_route_registry: {
            source: 'planner_trace.agent_health_projection.agent_worker_route_registry',
            status: 'passed',
            version: 'phase235.agent_worker_route_registry_audit.v1',
            summary: {
              routes: 35,
              ready_routes: 35,
              unrouted_allowed_tools: 0,
              issues: 0,
            },
          },
          agent_dogfood_evidence: {
            source: 'planner_trace.agent_health_projection.dogfood_evidence',
            status: 'ready',
            version: 'phase236.agent_dogfood_evidence.v1',
            summary: {
              evidence_count: 2,
              ready_evidence_count: 2,
              missing_source_count: 0,
              required_capability_count: 5,
              covered_capability_count: 5,
              missing_capability_count: 0,
              generated_chapter_count: 4,
              review_step_count: 5,
              open_finding_count: 2,
            },
            recommended_next_tools: ['inspect_agent_dogfood_evidence'],
          },
          steps: [],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('命令契约')
    expect(text).toContain('已投影')
    expect(text).toContain('控制命令')
    expect(text).toContain('2')
    expect(text).toContain('契约缺口')
    expect(text).toContain('0')
    expect(text).toContain('控制平面')
    expect(text).toContain('可继续编排')
    expect(text).toContain('控制面缺口')
    expect(text).toContain('工具缺口')
    expect(text).toContain('命令缺口')
    expect(text).toContain('建议检查')
    expect(text).toContain('Worker 路由')
    expect(text).toContain('通过')
    expect(text).toContain('未路由工具')
    expect(text).toContain('Dogfood 证据')
    expect(text).toContain('能力覆盖')
    expect(text).toContain('5 / 5')
    expect(text).toContain('生成章节')
    expect(text).toContain('4')
    expect(text).toContain('缺失来源')
    expect(text).toContain('1')
    expect(text).not.toContain('planner_trace.agent_health_projection.control_plane_readiness')
    expect(text).not.toContain('planner_trace.agent_health_projection.agent_worker_route_registry')
    expect(text).not.toContain('planner_trace.agent_health_projection.dogfood_evidence')
    expect(text).not.toContain('inspect_agent_health_projection')
    expect(text).not.toContain('inspect_agent_dogfood_evidence')
  })

  it('renders planner trace and reference pattern projection for auditable dialog runs', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-planner',
          project_id: 'project-1',
          goal: '审稿第12章',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {
            planner: {
              status: 'completed',
              planner_version: 'phase53.context_gate.v1',
              intent_class: 'review_chapter',
              chapter_index: 12,
              tools: [
                { tool_name: 'describe_agent_tools' },
                { tool_name: 'review_chapter_quality' },
                { tool_name: 'review_chapter_continuity' },
                { tool_name: 'plan_chapter_revision' },
              ],
              trace: {
                selected_tools: [
                  'describe_agent_tools',
                  'review_chapter_quality',
                  'review_chapter_continuity',
                  'plan_chapter_revision',
                ],
                risk_flags: ['review_requires_revision'],
                missing_dependencies: [
                  { code: 'chapter_quality_review_missing', tool_name: 'review_chapter_quality' },
                ],
                reference_pattern_version: 'phase107.reference_pattern_projection.v1',
                reference_patterns: [
                  {
                    source: 'hermes-agent',
                    source_lines: ['499-508'],
                    applied_patterns: ['tool_lifecycle_hooks'],
                    decision: 'Keep dialog planning explicit.',
                  },
                  {
                    source: 'openhuman',
                    source_lines: ['31-41'],
                    applied_patterns: ['compact_subagent_result_contract'],
                    decision: 'Preserve compact worker outputs.',
                  },
                  {
                    source: 'openclaw',
                    source_lines: ['44-49'],
                    applied_patterns: ['schema_and_audit_discipline'],
                    decision: 'Prefer deterministic schemas.',
                  },
                ],
              },
            },
          },
          output: null,
          error: null,
          steps: [],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Agent 规划投影')
    expect(text).toContain('审稿章节')
    expect(text).toContain('第12章')
    expect(text).toContain('phase53.context_gate.v1')
    expect(text).toContain('工具链')
    expect(text).toContain('4 个工具')
    expect(text).toContain('风险')
    expect(text).toContain('review_requires_revision')
    expect(text).toContain('缺依赖')
    expect(text).toContain('chapter_quality_review_missing')
    expect(text).toContain('参考模式')
    expect(text).toContain('hermes-agent')
    expect(text).toContain('openhuman')
    expect(text).toContain('openclaw')
    expect(text).toContain('tool_lifecycle_hooks')
    expect(text).toContain('compact_subagent_result_contract')
    expect(text).toContain('schema_and_audit_discipline')
    expect(text).not.toContain('references/agent-projects')
  })

  it('emits a planner continuation payload only for non-confirmation planner previews', async () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
              output: {
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
              },
            },
          ],
        },
      },
    })

    const button = document.body.querySelector('[data-testid="execute-planner-plan"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    expect(button.textContent).toContain('确认执行规划工具链')

    await button.click()

    expect(wrapper.emitted('executePlannerPlan')).toEqual([[
      {
        sourceRunId: 'run-plan-preview',
        sourcePlanId: 'plan:review-12',
        goal: '执行规划工具链：审稿章节',
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
        planner: {
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
        },
      },
    ]])
  })

  it('emits a confirmed planner continuation payload when approval contract hash is present', async () => {
    const approvalContract = {
      status: 'requires_confirmation',
      approval: { approval_contract_hash: 'approval:secret' },
      write_steps: [{ tool_name: 'generate_chapter' }],
    }
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
              output: {
                status: 'completed',
                intent_class: 'continue_next_chapter',
                approval_contract: approvalContract,
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
              },
            },
          ],
        },
      },
    })

    const button = document.body.querySelector('[data-testid="execute-planner-plan"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    expect(document.body.textContent).not.toContain('approval:secret')

    await button.click()

    expect(wrapper.emitted('executePlannerPlan')).toEqual([[
      {
        sourceRunId: 'run-plan-write-preview',
        sourcePlanId: 'plan:chapter-2',
        goal: '执行规划工具链：续写章节',
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
        planner: {
          status: 'completed',
          intent_class: 'continue_next_chapter',
          approval_contract: approvalContract,
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
        },
        approvalContractHash: 'approval:secret',
        approvalContract,
      },
    ]])
  })

  it('does not offer direct planner continuation when approval hash is missing', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Agent 规划投影')
    expect(text).toContain('需要审批')
    expect(document.body.querySelector('[data-testid="execute-planner-plan"]')).toBeNull()
  })

  it('renders loading and error states', () => {
    const loading = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: true,
        error: '',
        run: null,
      },
    })

    expect(document.body.textContent).toContain('正在加载 Agent 运行详情')

    loading.unmount()
    document.body.innerHTML = ''
    const failed = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '加载失败',
        run: null,
      },
    })

    expect(document.body.textContent).toContain('加载失败')
    failed.unmount()
  })

  it('renders recovery execution policy and guardrails', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('运行类型')
    expect(text).toContain('恢复预览')
    expect(text).toContain('恢复执行策略')
    expect(text).toContain('需要用户补充输入')
    expect(text).toContain('需要确认')
    expect(text).toContain('需要计划哈希')
    expect(text).toContain('不允许自动执行')
    expect(text).toContain('保护策略')
    expect(text).toContain('恢复工具需要用户补充输入')
    expect(text).toContain('prepare_generate_chapter_execution')
    expect(document.body.querySelector('[data-testid="execute-recovery"]')).toBeNull()
  })

  it('renders recommended followup provenance write tools as confirmation-only suggestions', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('推荐后继策略')
    expect(text).toContain('自动诊断工具')
    expect(text).toContain('inspect_agent_memory_route')
    expect(text).toContain('需确认修复')
    expect(text).toContain('repair_longform_maintenance')
    expect(document.body.querySelector('[data-testid="execute-recovery"]')).toBeNull()
  })

  it('renders recommended followup worker dispatch summary', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Worker 分派')
    expect(text).toContain('3 个 worker')
    expect(text).toContain('3 个任务')
    expect(text).toContain('路由审计')
    expect(text).toContain('通过')
    expect(text).toContain('未路由工具')
    expect(text).toContain('审稿执行者')
    expect(text).toContain('检索取证者')
    expect(text).toContain('记忆维护者')
    expect(text).not.toContain('worker_dispatch')
  })

  it('renders retrieval evidence and post-chapter memory capture loop summaries', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-memory-loop',
          project_id: 'project-1',
          goal: '续写第3章并沉淀写后记忆',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-memory-activation',
              run_id: 'run-memory-loop',
              project_id: 'project-1',
              step_index: 0,
              tool_name: 'inspect_agent_memory_activation_plan',
              status: 'success',
              input: { chapter_index: 3 },
              output: {
                status: 'ready',
                coverage: {
                  activated_counts: {
                    longform: 2,
                    foreshadowing: 1,
                    knowledge_base: 1,
                    style: 1,
                  },
                },
                memory_provenance: {
                  status: 'available',
                },
              },
            },
            {
              id: 'step-retrieval',
              run_id: 'run-memory-loop',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'search_agent_retrieval_context',
              status: 'success',
              input: { query: '雾港追踪 第3章' },
              output: {
                status: 'completed',
                summary: { total: 3, returned: 2 },
                items: [
                  {
                    source_type: 'knowledge_base_candidate',
                    source_ref: 'knowledge_base_candidate:candidate-1',
                    title: '低细节续写可行',
                    score: 0.91,
                    snippet: 'Agent 先读取知识库后可从低细节目标续写。',
                  },
                ],
                recommended_next_tools: ['summarize_longform_context'],
                memory_provenance: {
                  status: 'available',
                  recovery: { next_tools: [] },
                },
              },
            },
            {
              id: 'step-post-memory',
              run_id: 'run-memory-loop',
              project_id: 'project-1',
              step_index: 5,
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
                  { memory_type: 'writing_pattern', title: '第3章写作沉淀：雾港追踪' },
                  { memory_type: 'self_optimization_lesson', title: '第3章审稿经验：雾港追踪' },
                ],
                recommended_next_tools: ['prepare_record_agent_knowledge_base_candidate'],
                memory_provenance: {
                  status: 'available',
                  recovery: {
                    status: 'action_required',
                    next_tools: ['prepare_record_agent_knowledge_base_candidate'],
                  },
                },
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Agent 记忆闭环')
    expect(text).toContain('写前激活')
    expect(text).toContain('长篇记忆 2')
    expect(text).toContain('知识库经验 1')
    expect(text).toContain('检索证据')
    expect(text).toContain('返回 2 / 共 3')
    expect(text).toContain('低细节续写可行')
    expect(text).toContain('知识库候选')
    expect(text).toContain('写后记忆')
    expect(text).toContain('第3章')
    expect(text).toContain('可写入候选')
    expect(text).toContain('候选 2')
    expect(text).toContain('审稿证据 2')
    expect(text).toContain('prepare_record_agent_knowledge_base_candidate')
    expect(text).not.toContain('memory_provenance')
  })

  it('renders retrieval context projection without source refs or provenance internals', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-retrieval-context-projection',
          project_id: 'project-1',
          goal: '检索第5章前的灯塔旧回声证据',
          status: 'success',
          entrypoint: 'ui_memory_tree_workspace_retrieval_context',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-retrieval-context-projection',
              run_id: 'run-retrieval-context-projection',
              project_id: 'project-1',
              step_index: 0,
              tool_name: 'search_agent_retrieval_context',
              status: 'success',
              input: { query: '灯塔旧回声', limit: 8, max_chapter_index: 5 },
              output: {
                status: 'completed',
                version: 'phase243.agent_retrieval_context.v1',
                project_id: 'project-secret-id',
                query: '灯塔旧回声',
                filters: {
                  source_type: 'knowledge_base_candidate',
                  max_chapter_index: 5,
                  limit: 8,
                  candidate_limit: 200,
                },
                summary: { total: 4, returned: 2 },
                items: [
                  {
                    source_type: 'knowledge_base_candidate',
                    source_ref: 'knowledge_base_candidate:candidate-secret-1',
                    source_id: 'retrieval-secret-1',
                    title: '低细节续写可行',
                    snippet: 'Agent 先读取知识库后可从低细节目标续写。',
                    score: 0.91,
                    chapter_index: 5,
                  },
                  {
                    source_type: 'longform_memory',
                    source_ref: 'longform_memory:memory-secret-2',
                    source_id: 'retrieval-secret-2',
                    title: '灯塔地下室回声',
                    content: '顾衍在第4章确认灯塔地下室回声仍在。',
                    score: 0.78,
                    chapter_index: 4,
                  },
                ],
                retrieval: {
                  internal_debug_ref: 'retrieval_internal_secret',
                  query_vector_cache_key: 'retrieval-vector-secret',
                },
                recommended_next_tools: ['summarize_longform_context'],
                memory_provenance: {
                  version: 'phase243.agent_retrieval_context_provenance.v1',
                  status: 'available',
                  sources: [
                    {
                      source_type: 'knowledge_base_candidate',
                      source_ref: 'knowledge_base_candidate:candidate-secret-1',
                      title: '低细节续写可行',
                      chapter_index: 5,
                      score: 0.91,
                    },
                  ],
                  windows: {
                    retrieval_items: { total: 4, returned: 2, limit: 8, has_more: true },
                  },
                  recovery: { status: 'none', reason: 'retrieval_context_available', next_tools: [] },
                  trace: {
                    source: 'search_agent_retrieval_context',
                    version: 'phase243.agent_retrieval_context_provenance.v1',
                    mutability: 'read',
                  },
                },
                trace: {
                  source: 'search_agent_retrieval_context',
                  version: 'phase243.agent_retrieval_context.v1',
                  mutability: 'read',
                  write_performed: false,
                },
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('检索证据摘要')
    expect(text).toContain('已完成')
    expect(text).toContain('灯塔旧回声')
    expect(text).toContain('返回 2 / 共 4')
    expect(text).toContain('限制 8')
    expect(text).toContain('候选 200')
    expect(text).toContain('第5章前')
    expect(text).toContain('来源覆盖')
    expect(text).toContain('可用')
    expect(text).toContain('低细节续写可行')
    expect(text).toContain('知识库候选')
    expect(text).toContain('第5章')
    expect(text).toContain('分数 0.91')
    expect(text).toContain('Agent 先读取知识库后可从低细节目标续写')
    expect(text).toContain('灯塔地下室回声')
    expect(text).toContain('长篇记忆')
    expect(text).toContain('第4章')
    expect(text).toContain('顾衍在第4章确认灯塔地下室回声仍在')
    expect(text).toContain('summarize_longform_context')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('candidate-secret-1')
    expect(text).not.toContain('memory-secret-2')
    expect(text).not.toContain('retrieval-secret-1')
    expect(text).not.toContain('retrieval-secret-2')
    expect(text).not.toContain('source_ref')
    expect(text).not.toContain('source_type')
    expect(text).not.toContain('memory_provenance')
    expect(text).not.toContain('retrieval_items')
    expect(text).not.toContain('phase243.agent_retrieval_context')
    expect(text).not.toContain('retrieval_internal_secret')
    expect(text).not.toContain('retrieval-vector-secret')
  })

  it('renders memory activation plan projection without prompt or provenance internals', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-memory-activation-projection',
          project_id: 'project-1',
          goal: '检查第5章写前记忆激活计划',
          status: 'success',
          entrypoint: 'ui_memory_tree_workspace_memory_activation',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-memory-activation-projection',
              run_id: 'run-memory-activation-projection',
              project_id: 'project-1',
              step_index: 0,
              tool_name: 'inspect_agent_memory_activation_plan',
              status: 'success',
              input: { chapter_index: 5, query: '灯塔旧回声' },
              output: {
                status: 'degraded',
                version: 'phase241.memory_activation.v1',
                project_id: 'project-secret-id',
                chapter_index: 5,
                query: '灯塔旧回声',
                activation: {
                  longform: [
                    {
                      kind: 'longform_memory',
                      memory_id: 'memory-secret-1',
                      memory_type: 'chapter',
                      scope_key: 'chapter:2',
                      title: '灯塔回声',
                      summary: '顾衍确认旧回声与灯塔地下室有关。',
                      chapter_range: { start: 2, end: 2 },
                      source_ref: 'longform_memory:memory-secret-1',
                    },
                  ],
                  foreshadowing: [
                    {
                      kind: 'foreshadowing',
                      title: '空白信来源',
                      summary: '空白信来自黑潮门内部。',
                      introduced_chapter: 1,
                      source_ref: 'storyline:story-secret:foreshadowing:0',
                    },
                  ],
                  memory_tree: [
                    {
                      kind: 'memory_tree_node',
                      node_id: 'chapter:2',
                      level: 'chapter',
                      chapter_index: 2,
                      title: '灯塔旧回声',
                      summary: '旧回声与地下室有关。',
                      relevance: {
                        score: 0.91,
                        matched_terms: ['灯塔', '旧回声'],
                        matched_fields: ['summary'],
                        match_reasons: ['semantic_token_overlap'],
                      },
                      source_ref: 'memory_tree:chapter:2',
                    },
                  ],
                  world_model: [
                    {
                      kind: 'world_model',
                      proposal_item_id: 'world-secret-1',
                      chapter_index: 2,
                      subject_ref: 'char.hero',
                      predicate: 'knows_secret',
                      status: 'pending',
                      summary: '顾衍知道旧灯塔密室。',
                      source_ref: 'world_proposal_item:world-secret-1',
                    },
                  ],
                  knowledge_base: [
                    {
                      kind: 'knowledge_base_candidate',
                      candidate_id: 'candidate-secret-1',
                      memory_type: 'writing_pattern',
                      title: '章末钩子',
                      summary: '每章结尾保留一个可追踪的实物线索。',
                      confidence: 0.86,
                      status: 'active',
                      source_refs: ['chapter_content:2'],
                      source_ref: 'knowledge_base_candidate:candidate-secret-1',
                    },
                  ],
                  style: [
                    {
                      kind: 'style_anchor',
                      title: 'style_config.tone',
                      summary: '冷峻短句。',
                      source_ref: 'project:project-secret-id:style_config:tone',
                    },
                  ],
                },
                coverage: {
                  activated_counts: {
                    longform: 1,
                    foreshadowing: 1,
                    memory_tree: 1,
                    world_model: 1,
                    knowledge_base: 1,
                    style: 1,
                  },
                  memory_coverage_debt: {
                    status: 'degraded',
                    issue_count: 2,
                    missing_memory_count: 1,
                    stale_retrieval_count: 1,
                  },
                },
                risks: [
                  {
                    code: 'memory_coverage_debt',
                    severity: 'warning',
                    message: '长篇记忆或检索索引存在缺口，生成前应修复或明确降级使用。',
                    issue_count: 2,
                  },
                ],
                recommended_next_tools: ['prepare_repair_longform_maintenance', 'inspect_agent_memory_route'],
                prompt_block: '【Writing Agent 长记忆激活】目标：第5章\n- prompt-only raw context',
                memory_provenance: {
                  version: 'phase241.memory_activation_provenance.v1',
                  status: 'available',
                  sources: [
                    {
                      source_type: 'longform_memory',
                      source_ref: 'longform_memory:memory-secret-1',
                      title: '灯塔回声',
                    },
                    {
                      source_type: 'memory_tree_node',
                      source_ref: 'memory_tree:chapter:2',
                      title: '灯塔旧回声',
                    },
                  ],
                  windows: { longform: { total: 1, returned: 1, limit: 8, has_more: false } },
                  trace: {
                    source: 'build_memory_activation_plan',
                    version: 'phase241.memory_activation_provenance.v1',
                    mutability: 'read',
                  },
                },
                trace: {
                  source: 'build_memory_activation_plan',
                  version: 'phase241.memory_activation.v1',
                  mutability: 'read',
                  future_leak_guard: 'end_chapter_index_before_target',
                },
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('记忆激活计划')
    expect(text).toContain('降级')
    expect(text).toContain('第5章')
    expect(text).toContain('灯塔旧回声')
    expect(text).toContain('长篇记忆 1')
    expect(text).toContain('伏笔 1')
    expect(text).toContain('Memory Tree 1')
    expect(text).toContain('世界模型 1')
    expect(text).toContain('知识库经验 1')
    expect(text).toContain('风格 1')
    expect(text).toContain('来源覆盖')
    expect(text).toContain('可用')
    expect(text).toContain('覆盖问题 2')
    expect(text).toContain('缺失记忆 1')
    expect(text).toContain('检索陈旧 1')
    expect(text).toContain('灯塔回声')
    expect(text).toContain('空白信来源')
    expect(text).toContain('章末钩子')
    expect(text).toContain('冷峻短句')
    expect(text).toContain('memory_coverage_debt')
    expect(text).toContain('长篇记忆或检索索引存在缺口')
    expect(text).toContain('prepare_repair_longform_maintenance')
    expect(text).toContain('inspect_agent_memory_route')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('memory-secret-1')
    expect(text).not.toContain('candidate-secret-1')
    expect(text).not.toContain('world-secret-1')
    expect(text).not.toContain('chapter:2')
    expect(text).not.toContain('char.hero')
    expect(text).not.toContain('style_config.tone')
    expect(text).not.toContain('source_ref')
    expect(text).not.toContain('source_refs')
    expect(text).not.toContain('source_type')
    expect(text).not.toContain('prompt-only raw context')
    expect(text).not.toContain('phase241.memory_activation')
    expect(text).not.toContain('build_memory_activation_plan')
    expect(text).not.toContain('future_leak_guard')
    expect(text).not.toContain('end_chapter_index_before_target')
  })

  it('renders longform context summary projection without prompt or provenance internals', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-longform-context-summary',
          project_id: 'project-1',
          goal: '汇总第6章长篇上下文',
          status: 'success',
          entrypoint: 'ui_memory_tree_workspace_context_summary',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-longform-context-summary',
              run_id: 'run-longform-context-summary',
              project_id: 'project-1',
              step_index: 0,
              tool_name: 'summarize_longform_context',
              status: 'success',
              input: { chapter_index: 6, include_prompt_context: true },
              output: {
                status: 'completed',
                project_id: 'project-secret-id',
                chapter_index: 6,
                project: {
                  id: 'project-secret-id',
                  name: '雾港项目',
                  genre: '悬疑科幻',
                  target_chapter_count: 600,
                  target_word_count: 1800000,
                  current_word_count: 48000,
                  status: 'drafting',
                },
                progress: {
                  generated_chapter_count: 5,
                  latest_generated_chapter_index: 5,
                  generated_word_count: 48000,
                },
                context_summary: {
                  goal: '灯塔旧回声',
                  active_state: {
                    target_outline: {
                      chapter_index: 6,
                      title: '潮下车站',
                      summary: '林深追查旧灯塔回声。',
                      characters: ['林深', '苏晚晴'],
                      purpose: '揭示潮下车站入口。',
                    },
                    previous_chapter: {
                      chapter_index: 5,
                      title: '黑潮门回声',
                      word_count: 9200,
                    },
                  },
                  recent_chapters: [
                    {
                      id: 'memory-secret-5',
                      memory_type: 'chapter',
                      scope_key: 'chapter:5',
                      title: '黑潮门回声',
                      summary: '第5章里旧灯塔回声指向潮下车站。',
                      chapter_range: { start: 5, end: 5 },
                    },
                  ],
                  critical_context: [],
                  remaining_work: [
                    { code: 'missing_retrieval', message: '检索索引需要刷新。' },
                  ],
                },
                sections: [
                  {
                    key: 'recent_chapters',
                    title: '近期章节',
                    item_count: 2,
                    items: [
                      {
                        id: 'memory-secret-5',
                        memory_type: 'chapter',
                        scope_key: 'chapter:5',
                        title: '黑潮门回声',
                        summary: '第5章里旧灯塔回声指向潮下车站。',
                        chapter_range: { start: 5, end: 5 },
                        metadata: { source_id: 'chapter-content-5' },
                      },
                      {
                        id: 'memory-secret-4',
                        memory_type: 'chapter',
                        scope_key: 'chapter:4',
                        title: '雾港追踪',
                        summary: '苏晚晴锁定旧灯塔。',
                        chapter_range: { start: 4, end: 4 },
                      },
                    ],
                  },
                  {
                    key: 'manual_overflow',
                    title: '人工溢出上下文',
                    item_count: 6,
                    items: [
                      {
                        id: 'memory-overflow-1',
                        memory_type: 'arc',
                        scope_key: 'arc:1',
                        title: '雾港主线',
                        summary: '黑潮门正在回收旧信。',
                      },
                    ],
                  },
                ],
                source_sections: [
                  {
                    key: 'recent_chapters',
                    title: '近期章节',
                    item_count: 2,
                    source_type: 'longform_context_package',
                  },
                  {
                    key: 'manual_overflow',
                    title: '人工溢出上下文',
                    item_count: 6,
                    source_type: 'longform_context_package',
                  },
                ],
                source_section_keys: ['recent_chapters', 'manual_overflow'],
                memory_provenance: {
                  version: 'phase223.longform_memory_provenance.v1',
                  status: 'truncated',
                  sources: [
                    {
                      source_ref: 'longform_context_package:recent_chapters',
                      source_type: 'recent_chapters',
                      title: '近期章节',
                      item_count: 2,
                      returned_count: 2,
                      limit: 5,
                      has_more: false,
                    },
                    {
                      source_ref: 'longform_context_package:manual_overflow',
                      source_type: 'manual_overflow',
                      title: '人工溢出上下文',
                      item_count: 6,
                      returned_count: 1,
                      limit: 5,
                      has_more: true,
                    },
                  ],
                  windows: {
                    sections: {
                      recent_chapters: { total: 2, returned: 2, limit: 5, has_more: false },
                      manual_overflow: { total: 6, returned: 1, limit: 5, has_more: true },
                    },
                  },
                  recovery: {
                    status: 'optional',
                    reason: 'longform_context_window_limited',
                    next_tools: ['summarize_longform_context'],
                    tools: [
                      {
                        tool_name: 'summarize_longform_context',
                        params: {
                          chapter_index: 6,
                          query: '缩小上下文窗口后重新汇总第6章写作上下文。',
                          max_chars: 2400,
                        },
                      },
                    ],
                  },
                  trace: {
                    source: 'summarize_longform_context',
                    version: 'phase223.longform_memory_provenance.v1',
                    mutability: 'read',
                  },
                  prompt_context: {
                    chars: 3600,
                    max_chars: 1200,
                    included: true,
                    truncated: true,
                  },
                  boundaries: {
                    world_truth: {
                      status: 'separated',
                      canonical_source: 'Athena/world_model',
                      longform_context_role: 'retrieved_memory_rollups_and_generation_context',
                    },
                  },
                },
                diagnostics: [
                  {
                    code: 'section_items_limited',
                    severity: 'info',
                    message: '上下文 section 条目超过摘要上限，已截断。',
                    section_key: 'manual_overflow',
                    item_count: 6,
                    returned_count: 1,
                  },
                  {
                    code: 'prompt_context_truncated',
                    severity: 'info',
                    message: '完整上下文超过本次摘要预算。',
                    prompt_context_chars: 3600,
                    max_chars: 1200,
                  },
                ],
                decision: {
                  status: 'ready',
                  reason: 'longform_context_ready',
                  message: '长篇上下文可用于后续生成。',
                },
                should_generate_next_chapter: true,
                recommended_actions: ['preflight_writing'],
                prompt_context_chars: 3600,
                limits: { max_chars: 1200, include_prompt_context: true, section_item_limit: 5 },
                prompt_context: '【完整提示上下文】raw prompt context should stay hidden',
                trace: {
                  summary_version: 'phase52.longform_context_summary.v1',
                  source: 'build_longform_context_package',
                  source_section_count: 2,
                },
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('长篇上下文摘要')
    expect(text).toContain('已完成')
    expect(text).toContain('第6章')
    expect(text).toContain('灯塔旧回声')
    expect(text).toContain('可用于生成')
    expect(text).toContain('已生成 5')
    expect(text).toContain('最新章节 第5章')
    expect(text).toContain('字数 48000')
    expect(text).toContain('上下文字符 3600')
    expect(text).toContain('预算 1200')
    expect(text).toContain('来源覆盖')
    expect(text).toContain('截断')
    expect(text).toContain('近期章节 2')
    expect(text).toContain('人工溢出上下文 6')
    expect(text).toContain('黑潮门回声')
    expect(text).toContain('雾港追踪')
    expect(text).toContain('潮下车站')
    expect(text).toContain('preflight_writing')
    expect(text).toContain('section_items_limited')
    expect(text).toContain('prompt_context_truncated')
    expect(text).toContain('上下文 section 条目超过摘要上限')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('memory-secret-5')
    expect(text).not.toContain('memory-secret-4')
    expect(text).not.toContain('memory-overflow-1')
    expect(text).not.toContain('chapter:5')
    expect(text).not.toContain('chapter:4')
    expect(text).not.toContain('arc:1')
    expect(text).not.toContain('source_ref')
    expect(text).not.toContain('source_type')
    expect(text).not.toContain('source_sections')
    expect(text).not.toContain('source_section_keys')
    expect(text).not.toContain('longform_context_package:recent_chapters')
    expect(text).not.toContain('longform_context_package:manual_overflow')
    expect(text).not.toContain('phase223.longform_memory_provenance.v1')
    expect(text).not.toContain('phase52.longform_context_summary.v1')
    expect(text).not.toContain('build_longform_context_package')
    expect(text).not.toContain('Athena/world_model')
    expect(text).not.toContain('retrieved_memory_rollups_and_generation_context')
    expect(text).not.toContain('raw prompt context should stay hidden')
    expect(text).not.toContain('chapter-content-5')
  })

  it('emits a prepare candidate continuation from post-chapter memory capture candidates', async () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
                      params: {
                        memory_type: 'writing_pattern',
                        title: '第3章写作沉淀：雾港追踪',
                        summary: '第3章结尾形成雾港追踪线索，后续章节应延续。',
                        source_refs: ['chapter_content:chapter-content-3'],
                        confidence: 0.72,
                        status: 'candidate',
                        tags: ['post-chapter-capture', 'chapter:3'],
                      },
                    },
                  },
                ],
                recommended_next_tools: ['prepare_record_agent_knowledge_base_candidate'],
              },
            },
          ],
        },
      },
    })

    const button = document.body.querySelector('[data-testid="post-memory-candidate-prepare"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    expect(button.textContent).toContain('准备候选')
    expect(button.textContent).toContain('第3章写作沉淀')
    expect(document.body.textContent).not.toContain('chapter_content:chapter-content-3')
    expect(document.body.textContent).not.toContain('chapter-content-3')

    await button.click()

    expect(wrapper.emitted('executePlannerPlan')).toEqual([[
      {
        sourceRunId: 'run-post-memory-capture',
        sourcePlanId: 'post-memory-candidate-prepare:0',
        goal: '准备写后记忆候选审批：第3章写作沉淀：雾港追踪',
        tools: [
          {
            tool_name: 'prepare_record_agent_knowledge_base_candidate',
            params: {
              memory_type: 'writing_pattern',
              title: '第3章写作沉淀：雾港追踪',
              summary: '第3章结尾形成雾港追踪线索，后续章节应延续。',
              source_refs: ['chapter_content:chapter-content-3'],
              confidence: 0.72,
              status: 'candidate',
              tags: ['post-chapter-capture', 'chapter:3'],
            },
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
              params: {
                memory_type: 'writing_pattern',
                title: '第3章写作沉淀：雾港追踪',
                summary: '第3章结尾形成雾港追踪线索，后续章节应延续。',
                source_refs: ['chapter_content:chapter-content-3'],
                confidence: 0.72,
                status: 'candidate',
                tags: ['post-chapter-capture', 'chapter:3'],
              },
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
      },
    ]])
  })

  it('renders memory tree projection nodes from inspect output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Memory Tree 投影')
    expect(text).toContain('可用')
    expect(text).toContain('4 层')
    expect(text).toContain('返回 3 个')
    expect(text).toContain('卷 1 / 章节 12 / 场景 18 / 节拍 42')
    expect(text).toContain('查询')
    expect(text).toContain('灯塔旧回声')
    expect(text).toContain('语义搜索 + 祖先')
    expect(text).toContain('推荐展开 1')

    const nodes = Array.from(document.body.querySelectorAll('[data-testid="memory-tree-node"]'))
    expect(nodes).toHaveLength(3)
    expect(nodes[0].textContent).toContain('卷')
    expect(nodes[0].textContent).toContain('Volume 1')
    expect(nodes[1].textContent).toContain('章节')
    expect(nodes[1].textContent).toContain('第2章')
    expect(nodes[1].textContent).toContain('灯塔旧回声')
    expect(nodes[1].textContent).toContain('主角在灯塔发现旧回声线索。')
    expect(nodes[1].textContent).toContain('相关度 1.20')
    expect(nodes[2].textContent).toContain('场景')
    expect(nodes[2].textContent).toContain('未命名节点')
    expect(nodes[2].textContent).toContain('补充场景摘要。')
    expect(text).not.toContain('chapter-content-2')
    expect(text).not.toContain('memory-2')
    expect(text).not.toContain('scene:memory-3')
    expect(text).not.toContain('memory-3')
    expect(text).not.toContain('source_refs')
  })

  it('emits a read-only memory tree drilldown planner continuation from recommended drilldowns', async () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const button = document.body.querySelector('[data-testid="memory-tree-drilldown"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    expect(button.textContent).toContain('展开推荐节点')
    expect(button.textContent).toContain('灯塔旧回声')
    expect(document.body.textContent).not.toContain('chapter:2')

    await button.click()

    expect(wrapper.emitted('executePlannerPlan')).toEqual([[
      {
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
      },
    ]])
  })

  it('emits a read-only memory tree expansion from a returned node with children', async () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const button = document.body.querySelector('[data-testid="memory-tree-node-expand"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    expect(button.textContent).toContain('展开节点')
    expect(button.textContent).toContain('第2章')
    expect(document.body.textContent).not.toContain('scene:memory-3')

    await button.click()

    expect(wrapper.emitted('executePlannerPlan')).toEqual([[
      {
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
      },
    ]])
  })

  it('renders memory tree navigation history without exposing internal node ids', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        memoryTreeHistory: [
          {
            key: 'run-memory-tree-result:memory-tree-node-expand:0',
            label: '节点展开：第2章',
          },
        ],
        run: {
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('浏览历史')
    expect(text).toContain('节点展开：第2章')
    expect(text).not.toContain('scene:memory-3')
  })

  it('emits a read-only memory tree search planner continuation from query input', async () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const input = document.body.querySelector('[data-testid="memory-tree-search-input"]') as HTMLInputElement
    expect(input).not.toBeNull()
    input.value = '雨巷伏笔'
    input.dispatchEvent(new Event('input', { bubbles: true }))
    await wrapper.vm.$nextTick()
    const button = document.body.querySelector('[data-testid="memory-tree-search-submit"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    await button.click()

    expect(wrapper.emitted('executePlannerPlan')).toEqual([[
      {
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
      },
    ]])
  })

  it('emits confirmed recommended followup execution payload when preview has executable tools', async () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const button = document.body.querySelector('[data-testid="execute-recommended-followups"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    expect(button.textContent).toContain('确认执行后继')

    await button.click()

    expect(wrapper.emitted('executeRecommendedFollowups')).toEqual([
      [{ sourceRunId: 'source-run-2', planHash: 'followup-plan-hash-1' }],
    ])
  })

  it('shows post-approval continuation tools in recommended followup policy', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('推荐后继策略')
    expect(text).toContain('写后续跑')
    expect(text).toContain('2 个工具')
    expect(text).toContain('summarize_longform_context')
    expect(text).toContain('preflight_writing')
    expect(text).toContain('第3章')
  })

  it('emits confirmed recovery execution payload when preview is executable', async () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const button = document.body.querySelector('[data-testid="execute-recovery"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    expect(button.textContent).toContain('确认执行恢复')

    await button.click()

    expect(wrapper.emitted('executeRecovery')).toEqual([
      [{ sourceRunId: 'source-run-1', planHash: 'plan-hash-1' }],
    ])
  })

  it('renders route upgrade guarded apply only for eligible contract preview runs without leaking contract internals', async () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        pendingActionId: 'action-1',
        run: {
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
                approval_contract: { approval: { approval_contract_hash: 'approval:secret' } },
                recommended_next_tools: ['apply_pending_action_route_approval_opt_in'],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('路由升级审批')
    expect(text).toContain('等待确认')
    expect(text).toContain('需要确认')
    expect(text).not.toContain('approval:secret')
    expect(text).not.toContain('approval_contract')

    const button = document.body.querySelector('[data-testid="apply-route-upgrade"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    await button.click()

    expect(wrapper.emitted('applyRouteUpgrade')).toEqual([[
      {
        sourceRunId: 'run-contract',
        pendingActionId: 'action-1',
        approvalContractHash: 'approval:secret',
        approvalContract: { approval: { approval_contract_hash: 'approval:secret' } },
      },
    ]])
  })

  it('renders prepared chapter generation approval from recommended followup execution', async () => {
    const approvalContract = {
      status: 'requires_confirmation',
      approval: { approval_contract_hash: 'approval:chapter-3' },
    }
    const agentPlan = {
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
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
                agent_plan: agentPlan,
                agent_plan_approval_contract: approvalContract,
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('待审批写入')
    expect(text).toContain('第3章')
    expect(text).toContain('execute_generate_chapter_with_approval')
    expect(text).not.toContain('approval:chapter-3')
    expect(text).not.toContain('agent_plan_approval_contract')

    const button = document.body.querySelector('[data-testid="execute-prepared-approval"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    await button.click()

    expect(wrapper.emitted('executePlannerPlan')).toEqual([[
      {
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
              approval_contract: approvalContract,
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
          ...agentPlan,
          approval_contract: approvalContract,
        },
        approvalContractHash: 'approval:chapter-3',
        approvalContract,
      },
    ]])
  })

  it('renders prepared knowledge base candidate approval with candidate title', async () => {
    const approvalContract = {
      status: 'requires_confirmation',
      approval: { approval_contract_hash: 'approval:candidate-secret' },
    }
    const candidateParams = {
      memory_type: 'writing_pattern',
      title: '第3章写作沉淀：雾港追踪',
      summary: '第3章结尾形成雾港追踪线索，后续章节应延续。',
      source_refs: ['chapter_content:chapter-content-3'],
      confidence: 0.72,
      status: 'candidate',
      tags: ['post-chapter-capture', 'chapter:3'],
    }
    const agentPlan = {
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
          params: candidateParams,
          mutability: 'write',
          requires_confirmation: true,
          reason: '记录长期写作知识库候选项。',
        },
      ],
    }
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
              input: candidateParams,
              output: {
                status: 'approval_required',
                prepare_version: 'phase189.knowledge_base_candidate_prepare.v1',
                target_type: 'agent_knowledge_base_candidate',
                agent_plan: agentPlan,
                agent_plan_approval_contract: approvalContract,
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('待审批写入')
    expect(text).toContain('第3章写作沉淀：雾港追踪')
    expect(text).toContain('execute_record_agent_knowledge_base_candidate_with_approval')
    expect(text).not.toContain('chapter_content:chapter-content-3')
    expect(text).not.toContain('chapter-content-3')
    expect(text).not.toContain('approval:candidate-secret')

    const button = document.body.querySelector('[data-testid="execute-prepared-approval"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    await button.click()

    expect(wrapper.emitted('executePlannerPlan')).toEqual([[
      {
        sourceRunId: 'run-candidate-prepare',
        sourcePlanId: 'knowledge-base-candidate:project-1:abc123',
        goal: '执行已审批工具：写入知识库候选',
        tools: [
          {
            tool_name: 'execute_record_agent_knowledge_base_candidate_with_approval',
            params: {
              ...candidateParams,
              confirm_execute: true,
              approval_contract_hash: 'approval:candidate-secret',
              approval_contract: approvalContract,
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
          ...agentPlan,
          approval_contract: approvalContract,
        },
        approvalContractHash: 'approval:candidate-secret',
        approvalContract,
      },
    ]])
  })

  it('renders knowledge base candidate execution success without internal ids', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('知识库候选写入')
    expect(text).toContain('第3章写作沉淀：雾港追踪')
    expect(text).toContain('写法模式')
    expect(text).toContain('候选 1')
    expect(text).toContain('inspect_agent_knowledge_base_route')
    expect(text).not.toContain('candidate-secret-id')
    expect(text).not.toContain('chapter_content:chapter-content-3')
    expect(text).not.toContain('chapter-content-3')
    expect(text).not.toContain('approval:candidate-secret')
    expect(text).not.toContain('agent_plan_approval_verification')
  })

  it('emits a read-only knowledge base route continuation after candidate execution', async () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const button = document.body.querySelector('[data-testid="knowledge-candidate-route"]') as HTMLButtonElement
    expect(button).not.toBeNull()
    expect(button.textContent).toContain('检查知识库')
    expect(button.textContent).toContain('第3章写作沉淀：雾港追踪')
    expect(document.body.textContent).not.toContain('candidate-secret-id')
    expect(document.body.textContent).not.toContain('chapter-content-3')
    expect(document.body.textContent).not.toContain('approval:candidate-secret')

    await button.click()

    expect(wrapper.emitted('executePlannerPlan')).toEqual([[
      {
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
      },
    ]])
  })

  it('renders knowledge base route projection without internal source ids', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
                  reason: 'knowledge_base_available',
                  can_inform_generation: true,
                  recommended_tools: [
                    'summarize_longform_context',
                    'preflight_writing',
                    'review_chapter_quality',
                  ],
                },
                author_preferences: {
                  status: 'configured',
                  facets: [
                    {
                      key: 'tone_preferences',
                      value: ['冷峻', '悬疑'],
                      source: 'Project.style_config',
                    },
                  ],
                  source_ref: 'Project.style_config',
                },
                learned_rules: {
                  total: 3,
                  returned: 2,
                  limit: 2,
                  has_more: true,
                  items: [
                    {
                      id: 'rule-secret-id',
                      condition: '用户反馈章节像大纲',
                      action: '增加场景动作和角色即时反应',
                      source_ref: 'PromptRule:rule-secret-id',
                    },
                  ],
                  source_ref: 'PromptRule(rule_type=learned)',
                },
                knowledge_candidates: {
                  total: 2,
                  returned: 1,
                  limit: 2,
                  has_more: true,
                  items: [
                    {
                      id: 'candidate-secret-id',
                      title: '雾港追踪写法',
                      memory_type: 'writing_pattern',
                      summary: '使用冷峻短句和章末行动压力。',
                      source_refs: ['chapter_content:chapter-content-3'],
                    },
                  ],
                  source_ref: 'Project.style_config.knowledge_base_candidates',
                },
                reference_patterns: {
                  available: true,
                  returned: 2,
                  items: [
                    {
                      input_preview: '章节生成输入',
                      output_preview: '冷峻段落输出',
                      source_ref: 'FewShotExampleLibrary',
                    },
                  ],
                  source_ref: 'FewShotExampleLibrary',
                },
                diagnostics: [
                  {
                    code: 'world_truth_boundary',
                    severity: 'info',
                    message: '知识库是作者偏好、项目策略和写法经验，不是 Athena 世界真相。',
                  },
                ],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('知识库路由')
    expect(text).toContain('可用于生成')
    expect(text).toContain('第3章')
    expect(text).toContain('雾港追踪写法')
    expect(text).toContain('作者偏好 1')
    expect(text).toContain('学习规则 2 / 3')
    expect(text).toContain('知识库候选 1 / 2')
    expect(text).toContain('写法参考 2')
    expect(text).toContain('summarize_longform_context')
    expect(text).toContain('preflight_writing')
    expect(text).toContain('雾港追踪写法')
    expect(text).toContain('使用冷峻短句和章末行动压力。')
    expect(text).toContain('知识库是作者偏好、项目策略和写法经验')
    expect(text).not.toContain('rule-secret-id')
    expect(text).not.toContain('candidate-secret-id')
    expect(text).not.toContain('chapter_content:chapter-content-3')
    expect(text).not.toContain('chapter-content-3')
    expect(text).not.toContain('PromptRule:')
    expect(text).not.toContain('Project.style_config')
    expect(text).not.toContain('FewShotExampleLibrary')
    expect(text).not.toContain('source_ref')
    expect(text).not.toContain('source_refs')
  })

  it('renders memory route projection without provenance internals', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-memory-route',
          project_id: 'project-1',
          goal: '检查长篇记忆路由',
          status: 'success',
          entrypoint: 'ui_memory_tree_workspace_memory_route',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-memory-route',
              run_id: 'run-memory-route',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_memory_route',
              status: 'success',
              input: { chapter_index: 13, query: '灯塔旧回声', include_context_summary: false },
              output: {
                status: 'completed',
                project_id: 'project-secret-id',
                chapter_index: 13,
                query: '灯塔旧回声',
                route: {
                  status: 'ready',
                  reason: 'longform_memory_ready',
                  can_use_longform_context: true,
                  retrieval_document_count: 0,
                  recommended_tools: [
                    'inspect_agent_memory_tree',
                    'summarize_longform_context',
                    'preflight_writing',
                  ],
                },
                recommended_next_tools: [
                  'inspect_agent_memory_tree',
                  'summarize_longform_context',
                  'preflight_writing',
                ],
                longform_memory: {
                  project_id: 'project-secret-id',
                  chapter_count: 12,
                  current_word_count: 24000,
                  total_memories: 14,
                  counts_by_type: { chapter: 12, arc: 1, global: 1 },
                  latest_updated_at: '2026-06-01T00:00:00Z',
                },
                longform_maintenance: {
                  project_id: 'project-secret-id',
                  ready_for_writing: true,
                  issue_count: 0,
                  recommendations: [],
                },
                retrieval: {
                  project_id: 'project-secret-id',
                  total_documents: 0,
                  total_chunks: 0,
                  total_terms: 0,
                  total_embeddings: 0,
                  documents_by_source_type: {},
                },
                memory_provenance: {
                  version: 'phase224.agent_memory_route_provenance.v1',
                  status: 'degraded',
                  sources: [
                    { source_ref: 'LongformMemory', source_type: 'longform_memory', item_count: 14 },
                    { source_ref: 'RetrievalDocument', source_type: 'retrieval_index', item_count: 0 },
                  ],
                  windows: {
                    longform_memory: { total: 14, returned: 14, limit: 20 },
                    retrieval: { total: 0, returned: 0, limit: 20 },
                  },
                  recovery: {
                    status: 'optional',
                    reason: 'retrieval_index_empty',
                    next_tools: ['inspect_agent_memory_route', 'prepare_repair_longform_maintenance'],
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
                    write_tools: [{ tool_name: 'prepare_repair_longform_maintenance', params: {} }],
                    write_policy: 'requires_confirmation',
                  },
                  trace: {
                    source: 'inspect_agent_memory_route',
                    version: 'phase224.agent_memory_route_provenance.v1',
                    mutability: 'read',
                  },
                  coverage: {
                    chapter_count: 12,
                    longform_memory_count: 14,
                    retrieval_document_count: 0,
                    ready_for_writing: true,
                  },
                  boundaries: {
                    world_truth: {
                      status: 'separated',
                      canonical_source: 'Athena/world_model',
                      memory_route_role: 'longform_memory_retrieval_and_maintenance_diagnostics',
                    },
                  },
                },
                diagnostics: [
                  {
                    code: 'retrieval_index_empty',
                    severity: 'warning',
                    message: '项目已有正文，但检索索引为空，跨章节召回质量会下降。',
                  },
                ],
                trace: {
                  source: 'inspect_agent_memory_route',
                  version: 'phase72.agent_memory_route.v1',
                  mutability: 'read',
                },
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('记忆路由')
    expect(text).toContain('可用')
    expect(text).toContain('第13章')
    expect(text).toContain('灯塔旧回声')
    expect(text).toContain('可用于长篇上下文')
    expect(text).toContain('章节 12')
    expect(text).toContain('记忆 14')
    expect(text).toContain('字数 24000')
    expect(text).toContain('检索文档 0')
    expect(text).toContain('检索分片 0')
    expect(text).toContain('维护可写')
    expect(text).toContain('问题 0')
    expect(text).toContain('inspect_agent_memory_tree')
    expect(text).toContain('summarize_longform_context')
    expect(text).toContain('preflight_writing')
    expect(text).toContain('retrieval_index_empty')
    expect(text).toContain('项目已有正文，但检索索引为空')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('LongformMemory')
    expect(text).not.toContain('RetrievalDocument')
    expect(text).not.toContain('source_ref')
    expect(text).not.toContain('source_type')
    expect(text).not.toContain('phase224.agent_memory_route_provenance.v1')
    expect(text).not.toContain('phase72.agent_memory_route.v1')
    expect(text).not.toContain('Athena/world_model')
    expect(text).not.toContain('longform_memory_retrieval_and_maintenance_diagnostics')
  })

  it('renders world model route projection without internal ids', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-world-model-route',
          project_id: 'project-1',
          goal: '检查 Athena 世界模型路由',
          status: 'success',
          entrypoint: 'ui_memory_tree_workspace_world_model',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-world-model-route',
              run_id: 'run-world-model-route',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_world_model_route',
              status: 'success',
              input: { chapter_index: 2, subject_ref: 'char.hero', limit: 5 },
              output: {
                status: 'completed',
                project_id: 'project-secret-id',
                chapter_index: 2,
                subject_ref: 'char.hero',
                profile: {
                  id: 'profile-secret-id',
                  version: 3,
                  contract_version: 'world.contract.v1',
                },
                route: {
                  status: 'blocked',
                  reason: 'pending_world_model_proposals',
                  can_use_world_model: true,
                  pending_proposal_count: 2,
                },
                fact_summary: {
                  total_confirmed_facts: 3,
                  returned_facts: 1,
                  limit: 5,
                },
                facts: [
                  {
                    id: 'fact-secret-id',
                    claim_id: 'claim.secret.hero.identity',
                    chapter_index: 1,
                    subject_ref: 'char.hero',
                    predicate: 'identity',
                    object_ref_or_value: '灯塔区调查员',
                    claim_layer: 'truth',
                    claim_status: 'confirmed',
                    confidence: 0.95,
                    evidence_refs: ['chapter:1', 'world_profile:secret'],
                  },
                ],
                proposal_pressure: {
                  status: 'blocked',
                  total_items: 2,
                  risk_counts: { high: 1, medium: 1, low: 0 },
                  review_mode_counts: { individual: 1, batch: 1 },
                  clusters: [
                    {
                      cluster_id: 'cluster-secret-id',
                      risk_level: 'high',
                      review_mode: 'individual',
                      candidate_count: 2,
                      item_ids: ['item-secret-id'],
                      bundle_ids: ['bundle-secret-id'],
                      subject_refs: ['char.hero'],
                      predicate: 'identity',
                      chapter_range: { start: 1, end: 2 },
                      reason: '同一角色身份存在待审冲突',
                    },
                  ],
                },
                recommended_actions: ['review_world_model_proposals'],
                diagnostics: [
                  {
                    code: 'pending_world_model_proposals',
                    severity: 'warning',
                    message: '世界模型存在待处理事项，Agent 应先处理后再继续生成或修订。',
                    pending_proposal_count: 2,
                  },
                ],
                trace: {
                  source: 'inspect_agent_world_model_route',
                  version: 'phase74.agent_world_model_route.v1',
                  mutability: 'read',
                },
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('世界模型路由')
    expect(text).toContain('已阻塞')
    expect(text).toContain('可用于生成')
    expect(text).toContain('第2章')
    expect(text).toContain('char.hero')
    expect(text).toContain('确认事实 1 / 3')
    expect(text).toContain('待审提案 2')
    expect(text).toContain('高风险 1')
    expect(text).toContain('中风险 1')
    expect(text).toContain('review_world_model_proposals')
    expect(text).toContain('identity')
    expect(text).toContain('灯塔区调查员')
    expect(text).toContain('置信 0.95')
    expect(text).toContain('同一角色身份存在待审冲突')
    expect(text).toContain('世界模型存在待处理事项')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('profile-secret-id')
    expect(text).not.toContain('fact-secret-id')
    expect(text).not.toContain('claim.secret.hero.identity')
    expect(text).not.toContain('chapter:1')
    expect(text).not.toContain('world_profile:secret')
    expect(text).not.toContain('cluster-secret-id')
    expect(text).not.toContain('item-secret-id')
    expect(text).not.toContain('bundle-secret-id')
    expect(text).not.toContain('phase74.agent_world_model_route.v1')
    expect(text).not.toContain('source')
  })

  it('renders trace audit projection without internal ids', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'drawer-trace-audit-run',
          project_id: 'project-1',
          goal: '审计第3章执行链路',
          status: 'success',
          entrypoint: 'ui_memory_tree_workspace_trace_audit',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-trace-audit-wrapper',
              run_id: 'drawer-trace-audit-run',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_trace_audit',
              status: 'success',
              input: { chapter_index: 3, limit: 5 },
              output: {
                status: 'completed',
                audit: {
                  status: 'blocked',
                  reason: 'agent_run_blocked',
                  step_count: 2,
                  trace_count: 1,
                  dialog_route_event_count: 1,
                  approval_event_count: 1,
                  event_chain_count: 5,
                  context_block_count: 2,
                  control_plane_status: 'needs_attention',
                  control_plane_gap_count: 2,
                },
                run: {
                  id: 'audited-run-secret-id',
                  goal: '生成第3章',
                  status: 'blocked',
                  entrypoint: 'dialog_auto_plan',
                  background_task_id: 'task-secret-id',
                },
                steps: [
                  {
                    id: 'step-secret-id-1',
                    step_index: 1,
                    tool_name: 'plan_writing_agent_run',
                    status: 'success',
                    trace_id: 'trace-secret-id',
                  },
                  {
                    id: 'step-secret-id-2',
                    step_index: 2,
                    tool_name: 'generate_chapter',
                    status: 'blocked',
                    trace_id: 'trace-secret-id',
                    target_id: 'chapter-content-secret-id',
                    chapter_index: 3,
                  },
                ],
                traces: [
                  {
                    id: 'trace-secret-id',
                    trace_type: 'chapter_generation',
                    status: 'failed',
                    model: 'deepseek-chat',
                    prompt_tokens: 100,
                    completion_tokens: 20,
                    latency_ms: 321,
                    context_block_count: 2,
                    context_char_count: 6000,
                    error_message: 'provider timeout',
                  },
                ],
                event_chain: [
                  {
                    event_type: 'dialog_route_decision',
                    trace_id: 'route-trace-secret-id',
                    selected_route_label: '生成下一章节',
                    reason_label: '未发现恢复或后继，回落到章节生成',
                  },
                  {
                    event_type: 'approval_decision',
                    message_id: 'message-secret-id',
                    action_type: 'generate_chapter',
                    decision_label: '已确认',
                  },
                  {
                    event_type: 'run_dispatched',
                    run_id: 'audited-run-secret-id',
                    status: 'blocked',
                    entrypoint: 'dialog_auto_plan',
                    background_task_id: 'task-secret-id',
                  },
                  {
                    event_type: 'tool_step',
                    step_id: 'step-secret-id-2',
                    step_index: 2,
                    tool_name: 'generate_chapter',
                    status: 'blocked',
                    trace_id: 'trace-secret-id',
                  },
                  {
                    event_type: 'trace_attached',
                    trace_id: 'trace-secret-id',
                    trace_type: 'chapter_generation',
                    status: 'failed',
                    context_block_count: 2,
                  },
                ],
                context: {
                  total_blocks: 2,
                  blocks: [
                    {
                      trace_id: 'trace-secret-id',
                      key: 'longform-secret-key',
                      kind: 'memory',
                      title: '长篇记忆',
                      char_count: 3200,
                      source_count: 3,
                      truncated: true,
                    },
                  ],
                },
                failure: {
                  status: 'blocked',
                  tool_name: 'generate_chapter',
                  step_index: 2,
                  reason_code: 'missing_preflight',
                  message: '缺少 preflight gate',
                },
                recommended_actions: [
                  {
                    tool_name: 'plan_recovery_tools',
                    reason_code: 'missing_preflight',
                    source_step_index: 2,
                  },
                ],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Trace 审计')
    expect(text).toContain('阻塞')
    expect(text).toContain('生成第3章')
    expect(text).toContain('步骤 2')
    expect(text).toContain('Trace 1')
    expect(text).toContain('事件 5')
    expect(text).toContain('上下文块 2')
    expect(text).toContain('控制面缺口 2')
    expect(text).toContain('generate_chapter')
    expect(text).toContain('missing_preflight')
    expect(text).toContain('缺少 preflight gate')
    expect(text).toContain('plan_recovery_tools')
    expect(text).toContain('生成下一章节')
    expect(text).toContain('已确认')
    expect(text).toContain('长篇记忆')
    expect(text).toContain('3200 字')
    expect(text).not.toContain('audited-run-secret-id')
    expect(text).not.toContain('step-secret-id')
    expect(text).not.toContain('trace-secret-id')
    expect(text).not.toContain('message-secret-id')
    expect(text).not.toContain('task-secret-id')
    expect(text).not.toContain('chapter-content-secret-id')
    expect(text).not.toContain('longform-secret-key')
  })

  it('does not render route upgrade apply when contract preview is not confirmable', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    expect(document.body.querySelector('[data-testid="apply-route-upgrade"]')).toBeNull()
  })

  it('does not render route upgrade apply for stale or unrelated contract runs', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        pendingActionId: 'action-current',
        run: {
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
                approval_contract: { approval: { approval_contract_hash: 'approval:secret' } },
                recommended_next_tools: ['apply_pending_action_route_approval_opt_in'],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).not.toContain('approval:secret')
    expect(document.body.querySelector('[data-testid="apply-route-upgrade"]')).toBeNull()
  })

  it('labels confirmed recovery execution runs with source metadata', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-executed',
          project_id: 'project-1',
          goal: '执行恢复计划',
          status: 'success',
          entrypoint: 'ui_recovery_execute',
          input: {
            execute_recovery: true,
            recovery_run_id: 'source-run-1',
            recovery_plan_hash: 'plan-hash-1',
          },
          output: null,
          error: null,
          steps: [],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('运行类型')
    expect(text).toContain('恢复执行')
    expect(text).toContain('来源运行')
    expect(text).toContain('source-run-1')
    expect(text).toContain('计划哈希')
    expect(text).toContain('plan-hash-1')
  })
})
