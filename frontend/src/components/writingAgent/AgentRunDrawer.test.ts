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
