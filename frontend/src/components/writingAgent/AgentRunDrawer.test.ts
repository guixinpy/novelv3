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
    expect(text).toContain('1')
    expect(text).not.toContain('planner_trace.agent_health_projection.control_plane_readiness')
    expect(text).not.toContain('inspect_agent_health_projection')
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
