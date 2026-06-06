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

  it('renders reference alignment projection from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-reference-alignment',
          project_id: 'project-1',
          goal: '检查参考项目模式对齐',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-reference-alignment',
              run_id: 'run-reference-alignment',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_reference_alignment',
              status: 'success',
              input: {},
              output: {
                status: 'completed',
                summary: {
                  source_count: 3,
                  pattern_count: 5,
                  decision_count: 9,
                },
                patterns: [
                  {
                    source: 'hermes-agent',
                    applied_patterns: ['tool_lifecycle_hooks', 'toolset_visibility_boundary'],
                  },
                ],
                capability_alignment: [
                  {
                    area: 'Hermes/dialog',
                    status: 'implemented',
                  },
                ],
                recommended_next_tools: ['inspect_agent_tool_contracts'],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('参考项目对齐')
    expect(text).toContain('已完成')
    expect(text).toMatch(/参考项目\s*3/)
    expect(text).toMatch(/模式\s*5/)
    expect(text).toMatch(/决策\s*9/)
    expect(text).toContain('hermes-agent')
    expect(text).toContain('tool_lifecycle_hooks')
    expect(text).toContain('Hermes/dialog')
    expect(text).toContain('已实现')
    expect(text).toContain('inspect_agent_tool_contracts')
  })

  it('renders write gate coverage projection from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-write-gate',
          project_id: 'project-1',
          goal: '检查写入工具审批门禁覆盖',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-write-gate',
              run_id: 'run-write-gate',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_write_gate_coverage',
              status: 'success',
              input: {},
              output: {
                status: 'completed',
                summary: {
                  write_tool_count: 12,
                  agent_plan_gate_enforced_count: 8,
                  direct_confirmation_guard_count: 5,
                },
                recommended_next_targets: [
                  {
                    tool_name: 'generate_setup',
                    category: 'generation',
                    risk_level: 'high',
                    agent_plan_gate_status: 'missing_agent_plan_gate',
                    recommended_action: 'add_direct_agent_plan_approval_gate',
                  },
                ],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('写入门禁覆盖')
    expect(text).toContain('已完成')
    expect(text).toMatch(/写入工具\s*12/)
    expect(text).toMatch(/Agent 审批\s*8/)
    expect(text).toMatch(/确认守卫\s*5/)
    expect(text).toContain('generate_setup')
    expect(text).toContain('高风险')
    expect(text).toContain('缺少 Agent 计划门禁')
    expect(text).toContain('补齐 Agent 计划审批门禁')
  })

  it('renders worker dispatch projection from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-worker-dispatch',
          project_id: 'project-1',
          goal: '检查 worker 分派',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-worker-dispatch',
              run_id: 'run-worker-dispatch',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_worker_dispatch',
              status: 'success',
              input: {},
              output: {
                status: 'blocked',
                summary: {
                  workers: 2,
                  planned_tasks: 2,
                  blocked_tasks: 1,
                  issues: 1,
                },
                route_registry: {
                  status: 'needs_attention',
                  summary: {
                    unrouted_allowed_tools: 1,
                  },
                },
                worker_dispatches: [
                  {
                    status: 'ready',
                    worker: { name: 'reviewer_worker' },
                    summary: { planned_tasks: 1, blocked_tasks: 0, issues: 0 },
                  },
                  {
                    status: 'blocked',
                    worker: { name: 'retrieval_worker' },
                    summary: { planned_tasks: 1, blocked_tasks: 1, issues: 1 },
                  },
                ],
                issues: [
                  {
                    code: 'child_dispatch_not_allowed',
                    tool_name: 'search_agent_retrieval_context',
                      worker: 'retrieval_worker',
                    },
                  ],
                recommended_next_tools: ['inspect_agent_trace_audit'],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Worker 分派审计')
    expect(text).toContain('已阻塞')
    expect(text).toMatch(/Worker\s*2/)
    expect(text).toMatch(/计划任务\s*2/)
    expect(text).toMatch(/阻塞任务\s*1/)
    expect(text).toMatch(/问题\s*1/)
    expect(text).toContain('路由审计')
    expect(text).toContain('需处理')
    expect(text).toMatch(/未路由工具\s*1/)
    expect(text).toContain('审稿执行者')
    expect(text).toContain('检索取证者')
    expect(text).toContain('child_dispatch_not_allowed')
    expect(text).toContain('inspect_agent_trace_audit')
  })

  it('renders agent event projection from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-event-drawer',
          project_id: 'project-1',
          goal: '检查 Agent 事件投影',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-event-projection',
              run_id: 'run-event-drawer',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_event_projection',
              status: 'success',
              input: {},
              output: {
                status: 'completed',
                summary: {
                  total: 6,
                  by_event_type: { tool_error: 1 },
                  by_source_type: { writing_agent_step: 4 },
                },
                events: [
                  {
                    event_type: 'tool_error',
                    source_type: 'writing_agent_step',
                    tool_name: 'review_chapter_quality',
                    status: 'failed',
                    chapter_index: 3,
                    error_preview: 'quality model timeout',
                  },
                ],
                recommended_tools: ['inspect_agent_job_projection'],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Agent 事件投影')
    expect(text).toContain('已完成')
    expect(text).toMatch(/事件总数\s*6/)
    expect(text).toMatch(/工具事件\s*4/)
    expect(text).toMatch(/工具错误\s*1/)
    expect(text).toContain('工具错误')
    expect(text).toContain('工具步骤')
    expect(text).toContain('review_chapter_quality')
    expect(text).toContain('第3章')
    expect(text).toContain('失败')
    expect(text).toContain('quality model timeout')
    expect(text).toContain('inspect_agent_job_projection')
  })

  it('renders agent job projection from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-job-projection',
          project_id: 'project-1',
          goal: '检查后台任务队列',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-job-projection',
              run_id: 'run-job-projection',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_job_projection',
              status: 'success',
              input: {},
              output: {
                status: 'completed',
                summary: {
                  total: 4,
                  returned: 2,
                },
                queue: {
                  depth: 2,
                  active: 1,
                },
                selected_task: {
                  status: 'failed',
                  chapter_index: 3,
                  resume: {
                    can_resume: true,
                    next_chapter_index: 4,
                  },
                  error_preview: 'DeepSeek timeout',
                },
                recommended_tools: ['inspect_agent_trace_audit'],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('任务队列投影')
    expect(text).toContain('已完成')
    expect(text).toMatch(/队列深度\s*2/)
    expect(text).toMatch(/活跃任务\s*1/)
    expect(text).toMatch(/返回任务\s*2 \/ 4/)
    expect(text).toContain('失败')
    expect(text).toContain('第3章')
    expect(text).toMatch(/下一章\s*第4章/)
    expect(text).toContain('可恢复')
    expect(text).toContain('DeepSeek timeout')
    expect(text).toContain('inspect_agent_trace_audit')
  })

  it('renders chapter conflict recovery projection from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-chapter-conflict',
          project_id: 'project-1',
          goal: '规划第3章章节冲突恢复',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-conflict-recovery',
              run_id: 'run-chapter-conflict',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'plan_chapter_conflict_recovery',
              status: 'success',
              input: {},
              output: {
                status: 'completed',
                chapter_index: 3,
                conflict: {
                  chapter_index: 3,
                  status: 'reserved',
                  active_task_count: 1,
                  tasks: [
                    {
                      status: 'running',
                      source_label: '批量生成任务',
                      chapter_range: { start: 2, end: 4 },
                    },
                  ],
                },
                recovery: {
                  status: 'recommended',
                  next_tool: 'inspect_agent_job_projection',
                },
                tools: [
                  { tool_name: 'inspect_agent_job_projection', params: { chapter_index: 3 } },
                ],
                recovery_options: [
                  {
                    action: 'inspect_occupying_task',
                    tool_name: 'inspect_agent_job_projection',
                    safe_auto_execute: true,
                  },
                ],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('章节冲突恢复')
    expect(text).toContain('已完成')
    expect(text).toContain('第3章')
    expect(text).toContain('已占用')
    expect(text).toMatch(/占用任务\s*1/)
    expect(text).toContain('建议处理')
    expect(text).toContain('inspect_agent_job_projection')
    expect(text).toMatch(/计划工具\s*1/)
    expect(text).toMatch(/恢复选项\s*1/)
    expect(text).toContain('批量生成任务')
    expect(text).toContain('第2-4章')
    expect(text).toContain('运行中')
    expect(text).toContain('检查占用任务')
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

  it('renders retrieval context projection from tool output', () => {
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
                    title: '低细节续写可行',
                    snippet: 'Agent 先读取知识库后可从低细节目标续写。',
                    score: 0.91,
                    chapter_index: 5,
                  },
                  {
                    source_type: 'longform_memory',
                    title: '灯塔地下室回声',
                    content: '顾衍在第4章确认灯塔地下室回声仍在。',
                    score: 0.78,
                    chapter_index: 4,
                  },
                ],
                recommended_next_tools: ['summarize_longform_context'],
                memory_provenance: {
                  status: 'available',
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
  })

  it('renders retrieval strategy projection from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-retrieval-strategy-projection',
          project_id: 'project-1',
          goal: '规划第5章检索策略',
          status: 'success',
          entrypoint: 'dialog_intent_agent_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-retrieval-strategy-projection',
              run_id: 'run-retrieval-strategy-projection',
              project_id: 'project-1',
              step_index: 0,
              tool_name: 'inspect_agent_retrieval_strategy',
              status: 'success',
              input: { chapter_index: 5, query: '旧灯塔回声', limit: 6 },
              output: {
                status: 'completed',
                inputs: {
                  query: '旧灯塔回声',
                  limit: 6,
                  candidate_limit: 50,
                },
                strategy: {
                  name: 'query_aware_retrieval',
                  read_mode: 'search_then_summarize',
                  filters: {
                    query: '旧灯塔回声',
                    max_chapter_index: 4,
                    limit: 6,
                    candidate_limit: 50,
                  },
                },
                recommended_next_tools: ['search_agent_retrieval_context', 'summarize_longform_context'],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('检索策略摘要')
    expect(text).toContain('已完成')
    expect(text).toContain('查询感知检索')
    expect(text).toContain('旧灯塔回声')
    expect(text).toContain('第4章前')
    expect(text).toContain('限制 6')
    expect(text).toContain('候选 50')
    expect(text).toContain('search_agent_retrieval_context')
    expect(text).toContain('summarize_longform_context')
  })

  it('renders retrieval strategy quality projection from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-retrieval-strategy-quality-projection',
          project_id: 'project-1',
          goal: '复核第5章检索策略质量',
          status: 'success',
          entrypoint: 'dialog_intent_agent_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-retrieval-strategy-quality-projection',
              run_id: 'run-retrieval-strategy-quality-projection',
              project_id: 'project-1',
              step_index: 0,
              tool_name: 'inspect_agent_retrieval_strategy_quality',
              status: 'success',
              input: { chapter_index: 5, query: '旧灯塔回声', limit: 6 },
              output: {
                status: 'needs_dogfood_review',
                inputs: {
                  query: '旧灯塔回声',
                },
                quality: {
                  status: 'needs_dogfood_review',
                  strategy_name: 'query_aware_retrieval',
                  retrieval_documents: 8,
                  dogfood_evidence_count: 9,
                  dogfood_ready_evidence_count: 9,
                  dogfood_open_findings: 2,
                },
                strategy: {
                  name: 'query_aware_retrieval',
                  filters: {
                    query: '旧灯塔回声',
                    max_chapter_index: 4,
                  },
                },
                recommended_next_tools: [
                  'search_agent_retrieval_context',
                  'summarize_longform_context',
                  'inspect_agent_dogfood_evidence',
                ],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('检索策略质量复核')
    expect(text).toContain('需要自吃复核')
    expect(text).toContain('查询感知检索')
    expect(text).toContain('旧灯塔回声')
    expect(text).toContain('第4章前')
    expect(text).toContain('检索文档 8')
    expect(text).toContain('Dogfood 9 / 9')
    expect(text).toContain('开放问题 2')
    expect(text).toContain('search_agent_retrieval_context')
    expect(text).toContain('summarize_longform_context')
    expect(text).toContain('inspect_agent_dogfood_evidence')
  })

  it('renders retrieval prefetch plan projection from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-retrieval-prefetch-projection',
          project_id: 'project-1',
          goal: '预取第5章检索上下文',
          status: 'success',
          entrypoint: 'dialog_intent_agent_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-retrieval-prefetch-projection',
              run_id: 'run-retrieval-prefetch-projection',
              project_id: 'project-1',
              step_index: 0,
              tool_name: 'inspect_agent_retrieval_prefetch_plan',
              status: 'success',
              input: { chapter_index: 5, query: '旧灯塔回声', limit: 6 },
              output: {
                status: 'ready',
                inputs: { chapter_index: 5, query: '旧灯塔回声' },
                strategy: {
                  name: 'query_aware_retrieval',
                  filters: {
                    query: '旧灯塔回声',
                    max_chapter_index: 4,
                  },
                },
                prefetch_plan: {
                  status: 'ready',
                  mode: 'query_aware_prefetch',
                  target_chapter_index: 5,
                  query: '旧灯塔回声',
                  max_chapter_index: 4,
                  read_tools: ['search_agent_retrieval_context', 'summarize_longform_context'],
                  coverage: {
                    strategy_name: 'query_aware_retrieval',
                    retrieval_documents: 8,
                  },
                },
                recommended_next_tools: ['search_agent_retrieval_context', 'summarize_longform_context'],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('检索预取计划')
    expect(text).toContain('预取就绪')
    expect(text).toContain('查询感知预取')
    expect(text).toContain('查询感知检索')
    expect(text).toContain('旧灯塔回声')
    expect(text).toContain('第5章')
    expect(text).toContain('第4章前')
    expect(text).toContain('只读工具 2')
    expect(text).toContain('检索文档 8')
    expect(text).toContain('search_agent_retrieval_context')
    expect(text).toContain('summarize_longform_context')
  })

  it('renders memory activation plan projection from tool output', () => {
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
                chapter_index: 5,
                query: '灯塔旧回声',
                activation: {
                  longform: [
                    {
                      title: '灯塔回声',
                      summary: '顾衍确认旧回声与灯塔地下室有关。',
                    },
                  ],
                  foreshadowing: [
                    {
                      title: '空白信来源',
                      summary: '空白信来自黑潮门内部。',
                    },
                  ],
                  memory_tree: [
                    {
                      title: '灯塔旧回声',
                      summary: '旧回声与地下室有关。',
                    },
                  ],
                  world_model: [
                    {
                      predicate: 'knows_secret',
                      summary: '顾衍知道旧灯塔密室。',
                    },
                  ],
                  knowledge_base: [
                    {
                      title: '章末钩子',
                      summary: '每章结尾保留一个可追踪的实物线索。',
                    },
                  ],
                  style: [
                    {
                      summary: '冷峻短句。',
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
                memory_provenance: {
                  status: 'available',
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
  })

  it('renders longform context summary projection from tool output', () => {
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
                chapter_index: 6,
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
                  },
                },
                sections: [
                  {
                    key: 'recent_chapters',
                    title: '近期章节',
                    item_count: 2,
                    items: [
                      {
                        title: '黑潮门回声',
                        summary: '第5章里旧灯塔回声指向潮下车站。',
                      },
                      {
                        title: '雾港追踪',
                        summary: '苏晚晴锁定旧灯塔。',
                      },
                    ],
                  },
                  {
                    key: 'manual_overflow',
                    title: '人工溢出上下文',
                    item_count: 6,
                    items: [
                      {
                        title: '雾港主线',
                        summary: '黑潮门正在回收旧信。',
                      },
                    ],
                  },
                ],
                memory_provenance: {
                  status: 'truncated',
                  prompt_context: {
                    chars: 3600,
                    max_chars: 1200,
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
  })

  it('renders post-chapter memory panel from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('写后记忆沉淀规划')
    expect(text).toContain('已完成')
    expect(text).toContain('第3章')
    expect(text).toContain('可写入候选')
    expect(text).toContain('章节可用')
    expect(text).toContain('候选 2')
    expect(text).toContain('审稿证据 2')
    expect(text).toContain('来源覆盖')
    expect(text).toContain('可用')
    expect(text).toContain('第3章写作沉淀：雾港追踪')
    expect(text).toContain('写法模式')
    expect(text).toContain('置信 0.72')
    expect(text).toContain('第3章结尾形成雾港追踪线索')
    expect(text).toContain('第3章审稿经验：雾港追踪')
    expect(text).toContain('自优化经验')
    expect(text).toContain('置信 0.78')
    expect(text).toContain('中段节奏松散')
    expect(text).toContain('prepare_record_agent_knowledge_base_candidate')
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

  it('emits a memory tree LLM candidate prepare continuation from inspected candidates', async () => {
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Memory Tree 候选摘要')
    expect(text).toContain('可用')
    expect(text).toContain('候选 2 / 可准备 2 / 已物化 0')
    expect(text).toContain('第2章')
    expect(text).toContain('灯塔旧回声')
    expect(text).toContain('顾衍保留灯塔旧回声线索')
    expect(text).toContain('来源 3 / 848 字')
    expect(text).toContain('质量预检：降级')
    expect(text).toContain('待物化')
    expect(text).toContain('空白信来源')
    expect(text).toContain('空白信来源与灯塔暗道记录形成第二条摘要候选。')
    expect(text).toContain('来源 2 / 612 字')
    expect(text).toContain('质量预检：通过')
    expect(text).not.toContain('trace-secret-1')
    expect(text).not.toContain('trace-secret-2')
    expect(text).not.toContain('candidate_trace_id')
    expect(text).not.toContain('scope_key')
    expect(text).not.toContain('approval_contract')

    const buttons = Array.from(document.body.querySelectorAll('[data-testid="memory-tree-llm-candidate-prepare"]')) as HTMLButtonElement[]
    expect(buttons).toHaveLength(2)
    expect(buttons[0].textContent).toContain('准备候选摘要')
    expect(buttons[0].textContent).toContain('灯塔旧回声')
    expect(buttons[1].textContent).toContain('准备候选摘要')
    expect(buttons[1].textContent).toContain('空白信来源')

    await buttons[1].click()

    expect(wrapper.emitted('executePlannerPlan')).toEqual([[{
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
    }]])
  })

  it('renders materialized memory tree LLM candidates without duplicate prepare actions', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('候选 1 / 可准备 0 / 已物化 1')
    expect(text).toContain('蓝焰证词已经写入 Memory Tree 章级摘要。')
    expect(text).toContain('已物化')
    expect(text).not.toContain('trace-materialized-secret')
    expect(text).not.toContain('scope_key')
    expect(document.body.querySelectorAll('[data-testid="memory-tree-llm-candidate-prepare"]')).toHaveLength(0)
  })

  it('renders memory tree LLM candidate batch prepare output and emits per-candidate execute payloads', async () => {
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
    const wrapper = mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Memory Tree 批量候选准备')
    expect(text).toContain('等待确认')
    expect(text).toContain('已准备 2 / 候选 2 / 跳过 0')
    expect(text).toContain('逐条确认')
    expect(text).toContain('第2章 灯塔旧回声')
    expect(text).toContain('质量查询：灯塔旧回声')
    expect(text).toContain('第2章 空白信来源')
    expect(text).toContain('质量查询：空白信来源')
    expect(text).toContain('写入 Memory Tree 候选摘要')
    expect(text).not.toContain('trace-secret-1')
    expect(text).not.toContain('trace-secret-2')
    expect(text).not.toContain('approval-secret-1')
    expect(text).not.toContain('approval-secret-2')
    expect(text).not.toContain('candidate_trace_id')
    expect(text).not.toContain('approval_contract')

    const rows = Array.from(document.body.querySelectorAll('[data-testid="memory-tree-llm-candidate-batch"]'))
    expect(rows).toHaveLength(2)
    const buttons = Array.from(document.body.querySelectorAll('[data-testid="memory-tree-llm-candidate-batch-execute"]')) as HTMLButtonElement[]
    expect(buttons).toHaveLength(2)
    expect(buttons[0].textContent).toContain('确认候选摘要')
    expect(buttons[0].textContent).toContain('灯塔旧回声')
    expect(buttons[1].textContent).toContain('确认候选摘要')
    expect(buttons[1].textContent).toContain('空白信来源')

    await buttons[1].click()

    expect(wrapper.emitted('executePlannerPlan')).toEqual([[{
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
    }]])
  })

  it('renders memory tree LLM candidate batch execute output without internal approval details', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
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
              input: {
                confirm_execute: true,
                candidate_executions: [
                  {
                    candidate_trace_id: 'trace-secret-1',
                    approval_contract_hash: 'approval-secret-1',
                    approval_contract: { approval: { approval_contract_hash: 'approval-secret-1' } },
                  },
                ],
              },
              output: {
                status: 'success',
                execute_version: 'phase252.memory_tree_llm_candidate_summaries_batch_with_approval_execute.v1',
                summary: {
                  candidate_executions: 2,
                  succeeded_candidates: 2,
                  blocked_candidates: 0,
                },
                candidate_results: [
                  {
                    candidate_index: 1,
                    candidate_trace_id: 'trace-secret-1',
                    status: 'success',
                    materialization: {
                      summary: { created_nodes: 1, updated_nodes: 0 },
                      nodes: [
                        {
                          id: 'memory-secret-1',
                          chapter_index: 1,
                          title: '雨巷空白信',
                        },
                      ],
                    },
                    agent_plan_approval_verification: {
                      approval_contract_hash: 'approval-secret-1',
                    },
                    execution_resource_binding: {
                      target_id: 'trace-secret-1',
                    },
                    post_materialization_quality: {
                      status: 'degraded',
                      coverage: { summary_backed_chapter_nodes: 1 },
                    },
                  },
                  {
                    candidate_index: 2,
                    candidate_trace_id: 'trace-secret-2',
                    status: 'success',
                    materialization: {
                      summary: { created_nodes: 1, updated_nodes: 0 },
                      nodes: [
                        {
                          id: 'memory-secret-2',
                          chapter_index: 2,
                          title: '灯塔旧回声',
                        },
                      ],
                    },
                    agent_plan_approval_verification: {
                      approval_contract_hash: 'approval-secret-2',
                    },
                    execution_resource_binding: {
                      target_id: 'trace-secret-2',
                    },
                    post_materialization_quality: {
                      status: 'ready',
                      coverage: { summary_backed_chapter_nodes: 2 },
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
    expect(text).toContain('Memory Tree 批量候选写入')
    expect(text).toContain('已完成')
    expect(text).toContain('成功 2 / 阻塞 0 / 候选 2')
    expect(text).toContain('第1章')
    expect(text).toContain('创建 1 / 更新 0')
    expect(text).toContain('质量：降级')
    expect(text).toContain('第2章')
    expect(text).toContain('质量：通过')
    expect(text).not.toContain('trace-secret-1')
    expect(text).not.toContain('trace-secret-2')
    expect(text).not.toContain('approval-secret-1')
    expect(text).not.toContain('approval-secret-2')
    expect(text).not.toContain('agent_plan_approval_verification')
    expect(text).not.toContain('execution_resource_binding')
    expect(text).not.toContain('memory-secret')
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

  it('renders knowledge base route panel from tool output', () => {
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
  })

  it('renders memory route projection from tool output', () => {
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
                  chapter_count: 12,
                  current_word_count: 24000,
                  total_memories: 14,
                },
                longform_maintenance: {
                  ready_for_writing: true,
                  issue_count: 0,
                },
                retrieval: {
                  total_documents: 0,
                  total_chunks: 0,
                },
                memory_provenance: {
                  status: 'degraded',
                  coverage: {
                    chapter_count: 12,
                    longform_memory_count: 14,
                    retrieval_document_count: 0,
                    ready_for_writing: true,
                  },
                },
                diagnostics: [
                  {
                    code: 'retrieval_index_empty',
                    severity: 'warning',
                    message: '项目已有正文，但检索索引为空，跨章节召回质量会下降。',
                  },
                ],
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
  })

  it('renders world model route panel from tool output', () => {
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
                chapter_index: 2,
                subject_ref: 'char.hero',
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
                    chapter_index: 1,
                    subject_ref: 'char.hero',
                    predicate: 'identity',
                    object_ref_or_value: '灯塔区调查员',
                    claim_layer: 'truth',
                    claim_status: 'confirmed',
                    confidence: 0.95,
                  },
                ],
                proposal_pressure: {
                  status: 'blocked',
                  total_items: 2,
                  risk_counts: { high: 1, medium: 1, low: 0 },
                  review_mode_counts: { individual: 1, batch: 1 },
                  clusters: [
                    {
                      risk_level: 'high',
                      review_mode: 'individual',
                      candidate_count: 2,
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
  })

  it('renders world model semantic check panel from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-world-model-semantic-check',
          project_id: 'project-1',
          goal: '语义检查第3章世界模型',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-world-model-semantic-check',
              run_id: 'run-world-model-semantic-check',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_world_model_semantic_check',
              status: 'success',
              input: { chapter_index: 3, subject_ref: 'char.hero', max_facts: 5 },
              output: {
                status: 'completed',
                chapter_index: 3,
                subject_ref: 'char.hero',
                semantic_check: {
                  layer: 'L5 Semantic Checks',
                  checker_name: 'semantic_consistency_llm',
                  status: 'issues_found',
                  issue_count: 1,
                  summary: '章节死亡叙述和确认事实冲突。',
                },
                fact_window: {
                  total_confirmed_facts: 7,
                  returned_facts: 2,
                  limit: 5,
                },
                issues: [
                  {
                    code: 'fact_semantic_conflict',
                    severity: 'warning',
                    message: '章节声称顾衍死亡，但世界模型确认其状态为存活。',
                    subject_ref: 'char.hero',
                    predicate: 'status',
                    evidence_excerpt: '众人确认他已经死亡',
                  },
                ],
                recommended_next_tools: [
                  'prepare_analyze_chapter_world_model_execution',
                  'review_world_model_proposals',
                  'inspect_agent_world_model_route',
                ],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('世界模型语义检查')
    expect(text).toContain('已发现问题')
    expect(text).toContain('第3章')
    expect(text).toContain('char.hero')
    expect(text).toContain('确认事实 2 / 7')
    expect(text).toContain('检查事实上限 5')
    expect(text).toContain('章节死亡叙述和确认事实冲突')
    expect(text).toContain('fact_semantic_conflict')
    expect(text).toContain('警告')
    expect(text).toContain('章节声称顾衍死亡，但世界模型确认其状态为存活')
    expect(text).toContain('众人确认他已经死亡')
    expect(text).toContain('prepare_analyze_chapter_world_model_execution')
    expect(text).toContain('review_world_model_proposals')
    expect(text).toContain('inspect_agent_world_model_route')
  })

  it('renders world model proposal review panel from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-world-proposal-review',
          project_id: 'project-1',
          goal: '检查世界模型提案队列',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-world-proposal-review',
              run_id: 'run-world-proposal-review',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'review_world_model_proposals',
              status: 'success',
              input: { offset: 0, limit: 20 },
              output: {
                status: 'blocked',
                total_items: 3,
                returned_items: 2,
                offset: 0,
                limit: 20,
                has_more: true,
                risk_counts: { high: 1, medium: 1, low: 1 },
                review_mode_counts: { individual: 1, batch: 2 },
                clusters: [
                  {
                    risk_level: 'high',
                    review_mode: 'individual',
                    candidate_count: 1,
                    subject_refs: ['char.hero'],
                    predicate: 'identity',
                    chapter_range: { start: 1, end: 1 },
                    reason: '主角身份存在待审冲突',
                  },
                  {
                    risk_level: 'low',
                    review_mode: 'batch',
                    candidate_count: 2,
                    subject_refs: ['char.partner'],
                    predicate: 'mentioned_in_chapter',
                    chapter_range: { start: 2, end: 3 },
                    reason: '低风险出场事实可批量审阅',
                  },
                ],
                recommended_actions: [
                  'pause_generation_until_proposals_resolved',
                  'review_high_risk_proposals',
                  'batch_review_low_risk_proposals',
                ],
                should_generate_next_chapter: false,
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('世界模型提案队列')
    expect(text).toContain('已阻塞')
    expect(text).toContain('不可继续生成')
    expect(text).toContain('返回 2 / 3')
    expect(text).toContain('待审 3')
    expect(text).toContain('有更多')
    expect(text).toContain('高风险 1')
    expect(text).toContain('中风险 1')
    expect(text).toContain('低风险 1')
    expect(text).toContain('逐项审阅 1')
    expect(text).toContain('批量审阅 2')
    expect(text).toContain('pause_generation_until_proposals_resolved')
    expect(text).toContain('review_high_risk_proposals')
    expect(text).toContain('batch_review_low_risk_proposals')
    expect(text).toContain('char.hero')
    expect(text).toContain('identity')
    expect(text).toContain('高风险 · 逐项审阅 · 1 个候选 · 第1章')
    expect(text).toContain('主角身份存在待审冲突')
    expect(text).toContain('char.partner')
    expect(text).toContain('mentioned_in_chapter')
    expect(text).toContain('低风险 · 批量审阅 · 2 个候选 · 第2-3章')
    expect(text).toContain('低风险出场事实可批量审阅')
  })

  it('renders world model proposal resolution plan panel from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-world-proposal-resolution',
          project_id: 'project-1',
          goal: '规划世界模型提案解决顺序',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-world-proposal-resolution',
              run_id: 'run-world-proposal-resolution',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'plan_world_model_proposal_resolution',
              status: 'success',
              input: { offset: 2, limit: 7 },
              output: {
                status: 'blocked',
                total_items: 3,
                returned_items: 3,
                offset: 2,
                limit: 7,
                has_more: false,
                risk_counts: { high: 1, medium: 0, low: 2 },
                review_mode_counts: { individual: 1, batch: 2 },
                high_priority_step_count: 1,
                batch_step_count: 1,
                requires_human_confirmation: true,
                can_auto_apply: false,
                should_generate_next_chapter: false,
                recommended_actions: [
                  'pause_generation_until_proposals_resolved',
                  'resolve_individual_proposals_first',
                  'resolve_batch_proposals_after_individuals',
                ],
                recommended_next_tools: ['review_world_model_proposals'],
                resolution_steps: [
                  {
                    step_index: 1,
                    action_type: 'review_individual',
                    recommended_resolution: 'manual_individual_review',
                    requires_human_confirmation: true,
                    risk_level: 'high',
                    review_mode: 'individual',
                    candidate_count: 1,
                    subject_refs: ['char.hero'],
                    predicate: 'status',
                    chapter_range: { start: 1, end: 1 },
                    reason: '高风险状态事实需先逐项审阅',
                  },
                  {
                    step_index: 2,
                    action_type: 'review_batch',
                    recommended_resolution: 'batch_review',
                    requires_human_confirmation: true,
                    risk_level: 'low',
                    review_mode: 'batch',
                    candidate_count: 2,
                    subject_refs: ['char.partner'],
                    predicate: 'mentioned_in_chapter',
                    chapter_range: { start: 2, end: 3 },
                    reason: '低风险出场事实可在高风险后批量审阅',
                  },
                ],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('世界模型提案解决计划')
    expect(text).toContain('已阻塞')
    expect(text).toContain('需要人工确认')
    expect(text).toContain('不可自动应用')
    expect(text).toContain('不可继续生成')
    expect(text).toContain('返回 3 / 3')
    expect(text).toContain('高优先级步骤 1')
    expect(text).toContain('批量步骤 1')
    expect(text).toContain('高风险 1')
    expect(text).toContain('低风险 2')
    expect(text).toContain('逐项审阅 1')
    expect(text).toContain('批量审阅 2')
    expect(text).toContain('pause_generation_until_proposals_resolved')
    expect(text).toContain('resolve_individual_proposals_first')
    expect(text).toContain('resolve_batch_proposals_after_individuals')
    expect(text).toContain('review_world_model_proposals')
    expect(text).toContain('#1 char.hero · status')
    expect(text).toContain('逐项审阅 · 手动逐项审阅 · 高风险 · 1 个候选 · 第1章')
    expect(text).toContain('高风险状态事实需先逐项审阅')
    expect(text).toContain('#2 char.partner · mentioned_in_chapter')
    expect(text).toContain('批量审阅 · 批量审阅 · 低风险 · 2 个候选 · 第2-3章')
    expect(text).toContain('低风险出场事实可在高风险后批量审阅')
  })

  it('renders context compression projection from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-context-compression',
          project_id: 'project-1',
          goal: '检查第8章上下文压缩压力',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-context-compression',
              run_id: 'run-context-compression',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_context_compression_projection',
              status: 'success',
              input: { chapter_index: 8, max_chars: 4000 },
              output: {
                status: 'warning',
                chapter_index: 8,
                strategy: {
                  granularity: 'chapter_window',
                  protect_current_chapter: true,
                },
                summary: {
                  prompt_context_chars: 3800,
                  max_chars: 4000,
                  usage_ratio: 0.95,
                  truncated_section_count: 2,
                  context_guard_failure_count: 1,
                },
                risks: [
                  {
                    code: 'context_window_pressure',
                    severity: 'warning',
                    message: '章节上下文接近当前摘要窗口上限，应先压缩或扩大窗口再继续生成。',
                  },
                ],
                compression_plan: {
                  target_max_chars: 3000,
                  protected_head_sections: ['project', 'active_state'],
                  protected_tail_sections: ['recent_chapters', 'critical_context'],
                  pretrim_order: ['source_sections', 'critical_context', 'recent_chapters'],
                  llm_summary_required: true,
                },
                recommended_next_tools: ['build_agent_context_compression_payload', 'inspect_agent_memory_route'],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('上下文压缩')
    expect(text).toContain('警告')
    expect(text).toContain('第8章')
    expect(text).toContain('章节窗口')
    expect(text).toContain('保护当前章节')
    expect(text).toContain('上下文字符 3800')
    expect(text).toContain('预算 4000')
    expect(text).toContain('使用率 95%')
    expect(text).toContain('截断分区 2')
    expect(text).toContain('Guard 失败 1')
    expect(text).toContain('目标 3000')
    expect(text).toContain('头部保护 2')
    expect(text).toContain('尾部保护 2')
    expect(text).toContain('预修剪 3')
    expect(text).toContain('需要 LLM 摘要')
    expect(text).toContain('build_agent_context_compression_payload')
    expect(text).toContain('inspect_agent_memory_route')
    expect(text).toContain('context_window_pressure')
    expect(text).toContain('章节上下文接近当前摘要窗口上限')
  })

  it('renders preflight context budget projection from tool output', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'run-preflight-budget',
          project_id: 'project-1',
          goal: '预检第3章上下文压力',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-preflight-budget',
              run_id: 'run-preflight-budget',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'preflight_writing',
              status: 'success',
              input: { chapter_index: 3, max_context_chars: 500 },
              output: {
                status: 'ready',
                checks: {
                  context_compression: {
                    status: 'warning',
                    summary: {
                      prompt_context_chars: 475,
                      max_chars: 500,
                      usage_ratio: 0.95,
                      context_guard_failure_count: 2,
                    },
                    compression_plan: {
                      status: 'recommended',
                      target_max_chars: 375,
                    },
                  },
                },
                context_compression_payload_preview: {
                  status: 'ready',
                  compression_payload: {
                    target_max_chars: 375,
                    compressed_context_chars: 360,
                  },
                  recommended_next_tools: ['prepare_generate_chapter_execution'],
                },
                issues: [
                  {
                    code: 'context_compression_window_pressure',
                    severity: 'warning',
                    message: '上下文窗口接近上限，继续生成前应先压缩。',
                  },
                ],
                recommended_next_tools: [
                  'record_agent_context_compression_summary',
                  'prepare_generate_chapter_execution',
                ],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('上下文预算')
    expect(text).toContain('警告')
    expect(text).toContain('第3章')
    expect(text).toContain('上下文字符 475')
    expect(text).toContain('预算 500')
    expect(text).toContain('使用率 95%')
    expect(text).toContain('目标 375')
    expect(text).toContain('压缩预览 可用')
    expect(text).toContain('压缩字符 360')
    expect(text).toContain('record_agent_context_compression_summary')
    expect(text).toContain('prepare_generate_chapter_execution')
    expect(text).toContain('context_compression_window_pressure')
    expect(text).toContain('上下文窗口接近上限，继续生成前应先压缩。')
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

  it('renders trace audit intent chain summary without planner internals', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'drawer-trace-intent-chain-run',
          project_id: 'project-1',
          goal: '审计第3章预算预检链路',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-trace-intent-chain-wrapper',
              run_id: 'drawer-trace-intent-chain-run',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_trace_audit',
              status: 'success',
              input: { run_id: 'audited-run-secret-id' },
              output: {
                status: 'completed',
                audit: {
                  status: 'completed',
                  reason: 'run_completed',
                  step_count: 1,
                  trace_count: 0,
                  event_chain_count: 1,
                  context_block_count: 0,
                  intent_chain_status: 'available',
                  planned_tool_count: 1,
                  matched_planned_tool_count: 1,
                },
                run: {
                  id: 'audited-run-secret-id',
                  goal: '预检第3章上下文预算',
                  status: 'success',
                },
                intent_chain: {
                  status: 'available',
                  source: 'run_input_planner',
                  rule_id: 'preflight_context_budget_intent',
                  intent_class: 'preflight_context_budget',
                  mapped_from_action_type: 'preflight_context_budget',
                  chapter_index: 3,
                  planned_tool_count: 1,
                  executed_tool_count: 1,
                  matched_tool_count: 1,
                  planned_tools: [
                    {
                      tool_name: 'preflight_writing',
                      status: 'executed',
                      step_index: 1,
                      source_plan_id: 'plan-secret-id',
                      params: {
                        chapter_index: 3,
                        max_context_chars: 1200,
                      },
                    },
                  ],
                },
                event_chain: [
                  {
                    event_type: 'tool_step',
                    step_id: 'step-secret-id',
                    step_index: 1,
                    tool_name: 'preflight_writing',
                    status: 'success',
                  },
                ],
                context: { total_blocks: 0, blocks: [] },
                steps: [],
                traces: [],
                recommended_actions: [],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('意图链路')
    expect(text).toContain('preflight_context_budget_intent')
    expect(text).toContain('preflight_context_budget')
    expect(text).toContain('第3章')
    expect(text).toContain('计划工具 1')
    expect(text).toContain('已执行 1')
    expect(text).toContain('已匹配 1')
    expect(text).toContain('preflight_writing')
    expect(text).toContain('#1')
    expect(text).toContain('已执行')
    expect(text).not.toContain('audited-run-secret-id')
    expect(text).not.toContain('step-secret-id')
    expect(text).not.toContain('plan-secret-id')
    expect(text).not.toContain('max_context_chars')
    expect(text).not.toContain('1200')
    expect(text).not.toContain('run_input_planner')
    expect(text).not.toContain('source_plan_id')
  })

  it('renders trace audit end-to-end chain summary without trace internals', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'drawer-trace-e2e-run',
          project_id: 'project-1',
          goal: '审计第3章端到端链路',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-trace-e2e-wrapper',
              run_id: 'drawer-trace-e2e-run',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_trace_audit',
              status: 'success',
              input: { run_id: 'audited-run-secret-id' },
              output: {
                status: 'completed',
                audit: {
                  status: 'completed',
                  reason: 'run_completed',
                  step_count: 1,
                  trace_count: 1,
                  event_chain_count: 2,
                  context_block_count: 0,
                  end_to_end_chain_status: 'complete',
                },
                run: {
                  id: 'audited-run-secret-id',
                  goal: '预检第3章上下文预算',
                  status: 'success',
                },
                end_to_end_chain: {
                  status: 'complete',
                  coverage: {
                    intent: true,
                    planned_tools: true,
                    executed_tools: true,
                    model_traces: true,
                    result_message: true,
                  },
                  intent_chain_status: 'available',
                  planned_tool_count: 1,
                  executed_tool_count: 1,
                  matched_tool_count: 1,
                  tool_step_count: 1,
                  model_trace_count: 1,
                  result_message: {
                    status: 'available',
                    action_type: 'preflight_writing',
                    action_status: 'success',
                    message_id: 'message-secret-id',
                  },
                  segments: [
                    {
                      stage: 'intent',
                      status: 'available',
                      rule_id: 'preflight_context_budget_intent',
                      intent_class: 'preflight_context_budget',
                      chapter_index: 3,
                      trace_id: 'trace-secret-id',
                    },
                    { stage: 'planned_tools', status: 'available', count: 1 },
                    { stage: 'executed_tools', status: 'available', count: 1 },
                    { stage: 'model_traces', status: 'available', count: 1 },
                    {
                      stage: 'result_message',
                      status: 'available',
                      action_type: 'preflight_writing',
                      action_status: 'success',
                      message_id: 'message-secret-id',
                    },
                  ],
                },
                event_chain: [],
                context: { total_blocks: 0, blocks: [] },
                steps: [],
                traces: [],
                recommended_actions: [],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('端到端链路')
    expect(text).toContain('完整')
    expect(text).toContain('计划工具 1')
    expect(text).toContain('执行步骤 1')
    expect(text).toContain('模型 Trace 1')
    expect(text).toContain('结果消息')
    expect(text).toContain('preflight_writing')
    expect(text).toContain('成功')
    expect(text).toContain('意图')
    expect(text).toContain('计划工具')
    expect(text).toContain('执行工具')
    expect(text).toContain('模型 Trace')
    expect(text).toContain('结果消息')
    expect(text).not.toContain('audited-run-secret-id')
    expect(text).not.toContain('trace-secret-id')
    expect(text).not.toContain('message-secret-id')
  })

  it('renders trace audit anomaly summary without raw trace internals', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'drawer-trace-anomaly-run',
          project_id: 'project-1',
          goal: '审计第4章异常链路',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-trace-anomaly-wrapper',
              run_id: 'drawer-trace-anomaly-run',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_trace_audit',
              status: 'success',
              input: { run_id: 'audited-run-secret-id' },
              output: {
                status: 'completed',
                audit: {
                  status: 'completed',
                  reason: 'run_completed',
                  step_count: 2,
                  trace_count: 1,
                  event_chain_count: 2,
                  context_block_count: 1,
                  anomaly_status: 'failed',
                  anomaly_issue_count: 6,
                },
                run: {
                  id: 'audited-run-secret-id',
                  goal: '生成第4章',
                  status: 'success',
                },
                anomaly_summary: {
                  status: 'failed',
                  issue_count: 6,
                  severity_counts: { critical: 2, warning: 3, info: 1 },
                  failed_step_count: 1,
                  failed_trace_count: 1,
                  missing_trace_binding_count: 1,
                  unmatched_planned_tool_count: 1,
                  missing_result_message: true,
                  truncated_context_block_count: 1,
                  issues: [
                    {
                      code: 'failed_tool_step',
                      severity: 'critical',
                      tool_name: 'generate_chapter',
                      status: 'failed',
                      step_index: 1,
                      chapter_index: 4,
                      step_id: 'step-secret-id',
                    },
                    {
                      code: 'failed_model_trace',
                      severity: 'critical',
                      trace_type: 'chapter_generation',
                      status: 'failed',
                      chapter_index: 4,
                      error_recorded: true,
                      trace_id: 'trace-secret-id',
                    },
                    {
                      code: 'missing_trace_binding',
                      severity: 'warning',
                      tool_name: 'preflight_writing',
                      status: 'success',
                      step_index: 2,
                      chapter_index: 4,
                      step_id: 'step-missing-trace-secret-id',
                    },
                    {
                      code: 'planned_tool_not_executed',
                      severity: 'warning',
                      tool_name: 'inspect_agent_memory_route',
                      source_plan_id: 'plan-secret-id',
                    },
                    {
                      code: 'missing_result_message',
                      severity: 'warning',
                      stage: 'result_message',
                      message_id: 'message-secret-id',
                    },
                    {
                      code: 'truncated_context_block',
                      severity: 'info',
                      kind: 'longform_memory',
                      title: '长篇记忆',
                      char_count: 14,
                      source_count: 1,
                      trace_id: 'trace-secret-id',
                      key: 'secret-context-key',
                      content: '这段上下文不应进入异常摘要。',
                    },
                  ],
                },
                event_chain: [],
                context: { total_blocks: 0, blocks: [] },
                steps: [],
                traces: [],
                recommended_actions: [],
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('异常摘要')
    expect(text).toContain('失败')
    expect(text).toContain('问题 6')
    expect(text).toContain('严重 2')
    expect(text).toContain('警告 3')
    expect(text).toContain('提示 1')
    expect(text).toContain('失败步骤 1')
    expect(text).toContain('失败 Trace 1')
    expect(text).toContain('缺 Trace 1')
    expect(text).toContain('未执行计划 1')
    expect(text).toContain('缺结果消息')
    expect(text).toContain('截断上下文 1')
    expect(text).toContain('工具步骤失败')
    expect(text).toContain('模型 Trace 失败')
    expect(text).toContain('缺少 Trace 绑定')
    expect(text).toContain('计划工具未执行')
    expect(text).toContain('结果消息缺失')
    expect(text).toContain('上下文块已截断')
    expect(text).toContain('generate_chapter')
    expect(text).toContain('chapter_generation')
    expect(text).toContain('preflight_writing')
    expect(text).toContain('inspect_agent_memory_route')
    expect(text).toContain('第4章')
    expect(text).toContain('长篇记忆')
    expect(text).toContain('14 字')
    expect(text).not.toContain('audited-run-secret-id')
    expect(text).not.toContain('step-secret-id')
    expect(text).not.toContain('trace-secret-id')
    expect(text).not.toContain('message-secret-id')
    expect(text).not.toContain('plan-secret-id')
    expect(text).not.toContain('secret-context-key')
    expect(text).not.toContain('这段上下文不应进入异常摘要')
  })

  it('renders trace anomaly trends without raw run internals', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'drawer-trace-trends-run',
          project_id: 'project-1',
          goal: '检查 Trace 异常趋势',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-trace-trends-wrapper',
              run_id: 'drawer-trace-trends-run',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_trace_anomaly_trends',
              status: 'success',
              input: { limit: 9, chapter_index: 4 },
              output: {
                status: 'completed',
                filters: { limit: 9, chapter_index: 4 },
                trend: {
                  status: 'failed',
                  run_count: 3,
                  affected_run_count: 2,
                  issue_count: 6,
                  affected_run_rate: 0.67,
                  issue_rate: 2,
                  severity_counts: { critical: 2, warning: 3, info: 1 },
                  issue_counts: {
                    failed_model_trace: 1,
                    failed_tool_step: 1,
                    missing_trace_binding: 1,
                    missing_result_message: 1,
                    planned_tool_not_executed: 1,
                    truncated_context_block: 1,
                  },
                  dominant_issue_code: 'failed_model_trace',
                  project_id: 'project-secret-id',
                },
                baseline: {
                  status: 'clear',
                  run_count: 2,
                  affected_run_count: 0,
                  issue_count: 0,
                  affected_run_rate: 0,
                  issue_rate: 0,
                  severity_counts: { critical: 0, warning: 0, info: 0 },
                  issue_counts: {},
                  dominant_issue_code: '',
                  run_id: 'baseline-run-secret-id',
                },
                comparison: {
                  affected_run_rate_delta: 0.67,
                  issue_rate_delta: 2,
                  critical_issue_rate_delta: 0.67,
                },
                thresholds: {
                  affected_run_rate_delta: 0.5,
                  critical_issue_rate_delta: 0.25,
                },
                threshold_config: {
                  status: 'configured',
                  source: 'Project.style_config.agent_trace_anomaly_thresholds',
                  configured_keys: ['affected_run_rate_delta', 'critical_issue_rate_delta'],
                  fallback_keys: [],
                },
                threshold_signals: [
                  {
                    code: 'affected_run_rate_spike',
                    severity: 'warning',
                    title: '受影响运行率升高',
                    recent_value: 0.67,
                    baseline_value: 0,
                    delta: 0.67,
                    threshold: 0.5,
                    trace_id: 'signal-trace-secret-id',
                  },
                  {
                    code: 'critical_issue_rate_spike',
                    severity: 'critical',
                    title: '严重异常率升高',
                    recent_value: 0.67,
                    baseline_value: 0,
                    delta: 0.67,
                    threshold: 0.25,
                    step_id: 'signal-step-secret-id',
                  },
                ],
                calibration: {
                  status: 'needs_tuning',
                  sample: {
                    recent_run_count: 4,
                    baseline_run_count: 4,
                    minimum_run_count: 2,
                    run_id: 'calibration-sample-secret-id',
                  },
                  current_signal_count: 2,
                  current_thresholds: {
                    affected_run_rate_delta: 0.5,
                    critical_issue_rate_delta: 0.25,
                  },
                  suggested_thresholds: {
                    affected_run_rate_delta: 0.67,
                    critical_issue_rate_delta: 0.25,
                  },
                  false_negative_guard: {
                    status: 'passed',
                    reason: 'threshold_signal_present',
                    missed_affected_run_count: 0,
                    missed_issue_count: 0,
                    step_id: 'calibration-fn-secret-step',
                  },
                  false_positive_guard: {
                    status: 'triggered',
                    reason: 'threshold_signal_has_only_info_anomalies',
                    info_only_signal_count: 1,
                    trace_id: 'calibration-fp-secret-trace',
                  },
                  policy: {
                    status: 'review_required',
                    decision: 'raise_affected_run_rate_delta_threshold',
                    reviewed_run_count: 8,
                    minimum_review_run_count: 4,
                    promotion_candidate: false,
                    recommended_thresholds: {
                      affected_run_rate_delta: 0.67,
                      critical_issue_rate_delta: 0.25,
                    },
                    recommended_next_tools: ['inspect_agent_trace_audit', 'inspect_agent_dogfood_evidence'],
                    run_id: 'threshold-policy-secret-run',
                  },
                  recommended_next_tools: ['inspect_agent_trace_audit'],
                  project_id: 'calibration-project-secret-id',
                },
                runs: [
                  {
                    run_index: 1,
                    goal: '生成第5章',
                    status: 'success',
                    entrypoint: 'dialog_auto_plan',
                    chapter_index: 5,
                    anomaly_status: 'failed',
                    issue_count: 5,
                    critical_issue_count: 2,
                    warning_issue_count: 2,
                    info_issue_count: 1,
                    top_issue_codes: ['failed_model_trace', 'failed_tool_step'],
                    run_id: 'run-trend-secret-id',
                    trace_id: 'trace-trend-secret-id',
                  },
                  {
                    run_index: 2,
                    goal: '预检第4章',
                    status: 'success',
                    entrypoint: 'dialog_auto_plan',
                    chapter_index: 4,
                    anomaly_status: 'needs_attention',
                    issue_count: 1,
                    critical_issue_count: 0,
                    warning_issue_count: 1,
                    info_issue_count: 0,
                    top_issue_codes: ['missing_trace_binding'],
                    step_id: 'step-trend-secret-id',
                  },
                ],
                recommended_next_tools: ['inspect_agent_trace_audit', 'plan_recovery_tools'],
                trace: {
                  source: 'inspect_agent_trace_anomaly_trends',
                  version: 'phase74.agent_trace_anomaly_trends.v1',
                  mutability: 'read',
                  context_key: 'trend-secret-context-key',
                },
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Trace 异常趋势')
    expect(text).toContain('失败')
    expect(text).toContain('第4章')
    expect(text).toContain('运行 3')
    expect(text).toContain('受影响 2')
    expect(text).toContain('问题 6')
    expect(text).toContain('严重 2')
    expect(text).toContain('警告 3')
    expect(text).toContain('提示 1')
    expect(text).toContain('基线运行 2')
    expect(text).toContain('基线受影响 0')
    expect(text).toContain('异常率 +67%')
    expect(text).toContain('问题率 +200%')
    expect(text).toContain('受影响运行率升高')
    expect(text).toContain('严重异常率升高')
    expect(text).toContain('阈值 50%')
    expect(text).toContain('阈值 25%')
    expect(text).toContain('阈值来源')
    expect(text).toContain('项目配置')
    expect(text).toContain('校准')
    expect(text).toContain('需要调参')
    expect(text).toContain('样本 4/4')
    expect(text).toContain('当前信号 2')
    expect(text).toContain('建议异常阈值 67%')
    expect(text).toContain('建议严重阈值 25%')
    expect(text).toContain('漏报 guard')
    expect(text).toContain('阈值信号已触发')
    expect(text).toContain('误报 guard')
    expect(text).toContain('仅提示级异常触发')
    expect(text).toContain('提示信号 1')
    expect(text).toContain('固化策略')
    expect(text).toContain('需复核')
    expect(text).toContain('提高异常阈值')
    expect(text).toContain('复核样本 8/4')
    expect(text).toContain('不可固化')
    expect(text).toContain('主要问题')
    expect(text).toContain('模型 Trace 失败')
    expect(text).toContain('工具步骤失败')
    expect(text).toContain('缺少 Trace 绑定')
    expect(text).toContain('结果消息缺失')
    expect(text).toContain('计划工具未执行')
    expect(text).toContain('上下文块已截断')
    expect(text).toContain('生成第5章')
    expect(text).toContain('预检第4章')
    expect(text).toContain('inspect_agent_trace_audit')
    expect(text).toContain('plan_recovery_tools')
    expect(text).not.toContain('run-trend-secret-id')
    expect(text).not.toContain('trace-trend-secret-id')
    expect(text).not.toContain('step-trend-secret-id')
    expect(text).not.toContain('project-secret-id')
    expect(text).not.toContain('trend-secret-context-key')
    expect(text).not.toContain('baseline-run-secret-id')
    expect(text).not.toContain('signal-trace-secret-id')
    expect(text).not.toContain('signal-step-secret-id')
    expect(text).not.toContain('calibration-project-secret-id')
    expect(text).not.toContain('calibration-sample-secret-id')
    expect(text).not.toContain('calibration-fn-secret-step')
    expect(text).not.toContain('calibration-fp-secret-trace')
    expect(text).not.toContain('threshold-policy-secret-run')
    expect(text).not.toContain('Project.style_config.agent_trace_anomaly_thresholds')
  })

  it('renders trace anomaly long run samples without raw run or step internals', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'drawer-long-samples-run',
          project_id: 'project-1',
          goal: '检查 Trace 异常长跑样本',
          status: 'success',
          entrypoint: 'manual_debug_run',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-long-samples-wrapper',
              run_id: 'drawer-long-samples-run',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_trace_anomaly_long_run_samples',
              status: 'success',
              input: { limit: 6, chapter_index: 4 },
              output: {
                status: 'completed',
                filters: {
                  limit: 6,
                  chapter_index: 4,
                  minimum_review_run_count: 4,
                },
                sample_collection: {
                  status: 'ready_for_threshold_review',
                  candidate_run_count: 4,
                  minimum_review_run_count: 4,
                  missing_run_count: 0,
                  step_count: 7,
                  status_counts: {
                    blocked: 1,
                    failed: 1,
                    success: 2,
                  },
                  entrypoint_counts: {
                    dialog_auto_plan: 4,
                  },
                  chapter_indexes: [4, 5],
                  run_id: 'run-long-secret-id',
                  step_id: 'step-long-secret-id',
                },
                review_window: {
                  limit: 2,
                  baseline_limit: 2,
                  chapter_index: 4,
                },
                recommended_next_tools: [
                  'inspect_agent_trace_anomaly_threshold_review',
                  'inspect_agent_dogfood_evidence',
                ],
                recommended_next_tool_calls: [
                  {
                    tool_name: 'inspect_agent_trace_anomaly_threshold_review',
                    params: {
                      limit: 2,
                      baseline_limit: 2,
                      chapter_index: 4,
                    },
                  },
                ],
                side_effects: { executed: [], skipped: [] },
                trace: {
                  source: 'inspect_agent_trace_anomaly_long_run_samples',
                  version: 'phase243.agent_trace_anomaly_long_run_samples.v1',
                  mutability: 'read',
                },
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Trace 长跑样本')
    expect(text).toContain('已完成')
    expect(text).toContain('可复核')
    expect(text).toMatch(/候选运行\s*4/)
    expect(text).toMatch(/最低样本\s*4/)
    expect(text).toMatch(/缺失样本\s*0/)
    expect(text).toMatch(/工具步骤\s*7/)
    expect(text).toContain('第4章')
    expect(text).toContain('第5章')
    expect(text).toContain('成功 2')
    expect(text).toContain('已阻塞 1')
    expect(text).toContain('失败 1')
    expect(text).toContain('复核窗口')
    expect(text).toContain('最近 2 / 基线 2')
    expect(text).toContain('inspect_agent_trace_anomaly_threshold_review')
    expect(text).toContain('inspect_agent_dogfood_evidence')
    expect(text).not.toContain('run-long-secret-id')
    expect(text).not.toContain('step-long-secret-id')
    expect(text).not.toContain('phase243.agent_trace_anomaly_long_run_samples')
    expect(text).not.toContain('dialog_auto_plan')
    expect(text).not.toContain('recommended_next_tool_calls')
    expect(text).not.toContain('params')
    expect(text).not.toContain('mutability')
  })

  it('renders trace anomaly threshold review without raw policy or config internals', () => {
    mount(AgentRunDrawer, {
      attachTo: document.body,
      props: {
        open: true,
        loading: false,
        error: '',
        run: {
          id: 'drawer-threshold-review-run',
          project_id: 'project-1',
          goal: '复核 Trace 异常阈值样本',
          status: 'success',
          entrypoint: 'dialog_auto_plan',
          input: {},
          output: null,
          error: null,
          steps: [
            {
              id: 'step-threshold-review-wrapper',
              run_id: 'drawer-threshold-review-run',
              project_id: 'project-1',
              step_index: 1,
              tool_name: 'inspect_agent_trace_anomaly_threshold_review',
              status: 'success',
              input: { limit: 2, baseline_limit: 2 },
              output: {
                status: 'completed',
                review: {
                  status: 'ready_for_manual_review',
                  policy_decision: 'keep_current_thresholds',
                  sample: {
                    recent_run_count: 2,
                    baseline_run_count: 2,
                    reviewed_run_count: 4,
                    minimum_review_run_count: 4,
                  },
                  signal_count: 1,
                  policy: {
                    run_id: 'threshold-policy-secret-run',
                    trace_id: 'threshold-policy-secret-trace',
                  },
                },
                threshold_candidate: {
                  affected_run_rate_delta: 0.5,
                  critical_issue_rate_delta: 0.25,
                },
                recommended_next_tools: [
                  'prepare_record_agent_trace_anomaly_threshold_config',
                  'inspect_agent_dogfood_evidence',
                ],
                recommended_next_tool_calls: [
                  {
                    tool_name: 'prepare_record_agent_trace_anomaly_threshold_config',
                    params: {
                      affected_run_rate_delta: 0.5,
                      critical_issue_rate_delta: 0.25,
                      source: 'trace_anomaly_threshold_review',
                      reviewed_run_count: 4,
                      reason: 'manual_review_from_trace_anomaly_threshold_review',
                    },
                  },
                ],
                side_effects: {
                  executed: [],
                  skipped: ['record_agent_trace_anomaly_threshold_config'],
                },
                trace: {
                  source: 'inspect_agent_trace_anomaly_threshold_review',
                  version: 'phase242.agent_trace_anomaly_threshold_review.v1',
                  mutability: 'read',
                  config_key: 'Project.style_config.agent_trace_anomaly_thresholds',
                },
              },
            },
          ],
        },
      },
    })

    const text = document.body.textContent || ''
    expect(text).toContain('Trace 阈值复核')
    expect(text).toContain('已完成')
    expect(text).toContain('可人工复核')
    expect(text).toContain('保持当前阈值')
    expect(text).toContain('样本 2/2')
    expect(text).toContain('已复核 4/4')
    expect(text).toContain('阈值信号 1')
    expect(text).toContain('异常阈值 50%')
    expect(text).toContain('严重阈值 25%')
    expect(text).toContain('配置准备')
    expect(text).toContain('已跳过直接写入')
    expect(text).toContain('prepare_record_agent_trace_anomaly_threshold_config')
    expect(text).toContain('inspect_agent_dogfood_evidence')
    expect(text).not.toContain('threshold-policy-secret-run')
    expect(text).not.toContain('threshold-policy-secret-trace')
    expect(text).not.toContain('phase242.agent_trace_anomaly_threshold_review')
    expect(text).not.toContain('manual_review_from_trace_anomaly_threshold_review')
    expect(text).not.toContain('Project.style_config.agent_trace_anomaly_thresholds')
    expect(text).not.toContain('recommended_next_tool_calls')
    expect(text).not.toContain('params')
    expect(text).not.toContain('mutability')
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
