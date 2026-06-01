from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


_CHAPTER_PARAMS = object_schema(
    {
        "chapter_index": {"type": "integer", "minimum": 1},
    }
)
_DESCRIBE_AGENT_TOOLS_INPUT = object_schema(
    {
        "chapter_index": {"type": "integer", "minimum": 1},
        "agent_profile": {"type": "string"},
    }
)
_AGENT_PLAN_APPROVAL_CONTRACT_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "version": {"type": "string"},
        "project_id": {"type": ["string", "null"]},
        "plan_id": {"type": ["string", "null"]},
        "source_projection_id": {"type": ["string", "null"]},
        "write_step_count": {"type": "integer"},
        "write_steps": {"type": "array"},
        "approval": {"type": "object"},
        "trace": {"type": "object"},
    }
)
_AGENT_PLAN_APPROVAL_VERIFICATION_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "version": {"type": "string"},
        "reason": {"type": "string"},
        "current_contract": {"type": "object"},
        "drift": {"type": "object"},
        "recommended_next_tools": {"type": "array"},
        "trace": {"type": "object"},
    }
)
_AGENT_WRITE_GATE_COVERAGE_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "version": {"type": "string"},
        "summary": {"type": "object"},
        "write_tools": {"type": "array"},
        "recommended_next_targets": {"type": "array"},
        "trace": {"type": "object"},
    }
)
_AGENT_HEALTH_PROJECTION_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "version": {"type": "string"},
        "profile_policy": {"type": ["object", "null"]},
        "agent_definition_registry": {"type": "object"},
        "agent_worker_route_registry": {"type": "object"},
        "route_preference": {"type": "object"},
        "tool_contracts": {"type": "object"},
        "command_contracts": {"type": "object"},
        "control_plane_readiness": {"type": "object"},
        "write_gate": {"type": "object"},
        "trace_audit": {"type": ["object", "null"]},
        "creative_quality": {"type": "object"},
        "context_compression": {"type": ["object", "null"]},
        "memory_activation": {"type": ["object", "null"]},
        "post_chapter_memory_capture": {"type": ["object", "null"]},
        "narrative_trends": {"type": "object"},
        "reference_alignment": {"type": "object"},
        "dogfood_evidence": {"type": "object"},
        "diagnostics": {"type": "array"},
        "recommended_tools": {"type": "array"},
        "recommended_next_tools": {"type": "array"},
        "trace": {"type": "object"},
    }
)
_AGENT_CONTROL_PLANE_READINESS_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "version": {"type": "string"},
        "summary": {"type": "object"},
        "diagnostics": {"type": "array"},
        "recommended_next_tools": {"type": "array"},
        "control_surfaces": {"type": "object"},
        "trace": {"type": "object"},
    }
)
_AGENT_REFERENCE_ALIGNMENT_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "version": {"type": "string"},
        "source_refs": {"type": "array"},
        "summary": {"type": "object"},
        "patterns": {"type": "array"},
        "capability_alignment": {"type": "array"},
        "recommended_next_tools": {"type": "array"},
        "trace": {"type": "object"},
    }
)
_AGENT_DOGFOOD_EVIDENCE_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "version": {"type": "string"},
        "source_refs": {"type": "array"},
        "summary": {"type": "object"},
        "capability_coverage": {"type": "array"},
        "evidence": {"type": "array"},
        "diagnostics": {"type": "array"},
        "recommended_next_tools": {"type": "array"},
        "trace": {"type": "object"},
    }
)


AGENT_CORE_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="describe_agent_tools",
        module="writing_agent",
        category="preflight",
        description="返回当前项目和章节下 Agent 可见工具、隐藏工具和缺失依赖诊断。",
        input_schema=_DESCRIBE_AGENT_TOOLS_INPUT,
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "visible_tools": {"type": "array"},
                "hidden_tools": {"type": "array"},
                "diagnostics": {"type": "array"},
                "agent_profile_scope": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        sort_key=5,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="plan_writing_agent_run",
        module="writing_agent",
        category="preflight",
        description="根据高层写作意图生成可解释的 Writing Agent 工具链计划。",
        input_schema=object_schema(
            {
                "goal": {"type": "string"},
                "chapter_index": {"type": "integer", "minimum": 1},
                "intent": {"type": "string"},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "intent_class": {"type": "string"},
                "steps": {"type": "array"},
                "tools": {"type": "array"},
                "approval_contract": {"type": "object"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=6,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="plan_dialog_intent_agent_run",
        module="writing_agent",
        category="preflight",
        description="根据自然语言对话意图投影生成只读 Writing Agent 工具链计划，不直接执行工具。",
        input_schema=object_schema(
            {
                "text": {"type": "string"},
                "dialog_state": {"type": "string"},
                "pending_action_id": {"type": "string"},
                "missing_items": {"type": "array"},
                "completed_items": {"type": "array"},
                "suggested_next_step": {"type": "string"},
            },
            required=("text",),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "intent_projection": {"type": "object"},
                "planner": {"type": "object"},
                "plan": {"type": ["object", "null"]},
                "tools": {"type": "array"},
                "approval_contract": {"type": "object"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=7,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="preview_agent_plan_approval_contract",
        module="writing_agent",
        category="preflight",
        description="为 Writing Agent 计划中的写入步骤生成只读审批契约和稳定哈希，不执行任何工具。",
        input_schema=object_schema({"plan": {"type": "object"}}, required=("plan",)),
        output_schema=_AGENT_PLAN_APPROVAL_CONTRACT_OUTPUT,
        target_type="agent_plan_approval_contract",
        internal=True,
        non_blocking_report=True,
        sort_key=7,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="verify_agent_plan_approval_contract",
        module="writing_agent",
        category="preflight",
        description="只读校验 Writing Agent 计划审批契约哈希，报告缺失、错配或漂移，不执行任何写入工具。",
        input_schema=object_schema(
            {
                "plan": {"type": "object"},
                "approval_contract_hash": {"type": "string"},
                "approval_contract": {"type": "object"},
            },
            required=("plan",),
        ),
        output_schema=_AGENT_PLAN_APPROVAL_VERIFICATION_OUTPUT,
        target_type="agent_plan_approval_verification",
        internal=True,
        non_blocking_report=True,
        sort_key=7,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_health_projection",
        module="writing_agent",
        category="preflight",
        description="聚合 Agent profile 策略、路由偏好、工具契约、写入门禁和可选运行 Trace 的只读健康投影。",
        input_schema=object_schema(
            {
                "run_id": {"type": "string"},
                "source": {"type": "string"},
                "chapter_index": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=_AGENT_HEALTH_PROJECTION_OUTPUT,
        target_type="agent_health_projection",
        internal=True,
        non_blocking_report=True,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_control_plane_readiness",
        module="writing_agent",
        category="preflight",
        description="聚合工具契约与命令契约的控制面就绪度摘要，用于 Agent 编排前自检。",
        input_schema=object_schema(),
        output_schema=_AGENT_CONTROL_PLANE_READINESS_OUTPUT,
        target_type="agent_control_plane_readiness",
        internal=True,
        non_blocking_report=True,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="plan_recovery_tools",
        module="writing_agent",
        category="preflight",
        description="根据已阻塞或失败的 Writing Agent run 生成只读恢复工具链计划，不自动执行恢复。",
        input_schema=object_schema({"run_id": {"type": "string"}}),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "source_run_id": {"type": "string"},
                "source_step": {"type": "object"},
                "recovery": {"type": "object"},
                "tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=7,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="plan_recommended_followups",
        module="writing_agent",
        category="preflight",
        description="根据指定 Writing Agent run 的运行时推荐生成只读后继工具计划。",
        input_schema=object_schema({"run_id": {"type": "string"}}),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "source_run_id": {"type": "string"},
                "source_step": {"type": "object"},
                "recommended_followups": {"type": "object"},
                "tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_worker_dispatch",
        module="writing_agent",
        category="preflight",
        description="只读预览工具任务到 Writing Agent worker profile 的分派边界，不执行任何 worker 任务。",
        input_schema=object_schema(
            {
                "worker_name": {"type": "string"},
                "parent_run_id": {"type": "string"},
                "tasks": {
                    "type": "array",
                    "items": object_schema(
                        {
                            "tool_name": {"type": "string"},
                            "params": {"type": "object"},
                            "children": {"type": "array"},
                            "delegate_to": {"type": "string"},
                            "delegate_to_worker": {"type": "string"},
                        },
                        required=("tool_name",),
                    ),
                },
            },
            required=("tasks",),
        ),
        output_schema=object_schema(
            {
                "version": {"type": "string"},
                "status": {"type": "string"},
                "worker": {"type": "object"},
                "summary": {"type": "object"},
                "definition_registry": {"type": "object"},
                "route_registry": {"type": "object"},
                "orphan_recovery": {"type": "object"},
                "task_envelopes": {"type": "array"},
                "worker_dispatches": {"type": "array"},
                "issues": {"type": "array"},
            }
        ),
        target_type="agent_worker_dispatch",
        internal=True,
        non_blocking_report=True,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="apply_agent_worker_orphan_recovery",
        module="writing_agent",
        category="preflight",
        description="确认后清理孤兒 worker run：将仍 active 的孤兒 run 标记为 blocked，并可安全创建 pending redispatch run。",
        input_schema=object_schema(
            {
                "confirm_apply": {"type": "boolean"},
                "confirm_redispatch": {"type": "boolean"},
                "run_ids": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "minimum": 1},
            },
            required=("confirm_apply",),
        ),
        output_schema=object_schema(
            {
                "version": {"type": "string"},
                "status": {"type": "string"},
                "reason": {"type": "string"},
                "write_performed": {"type": "boolean"},
                "summary": {"type": "object"},
                "orphan_worker_runs": {"type": "array"},
                "side_effects": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_worker_orphan_recovery_apply",
        internal=True,
        non_blocking_report=False,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_slash_command_route",
        module="writing_agent",
        category="preflight",
        description="返回斜杠命令到 Writing Agent 工具的只读路由投影，用于对话入口 Agent 化自查。",
        input_schema=object_schema({"command_name": {"type": "string"}}),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "routes": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=9,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_dialog_route_projection",
        module="writing_agent",
        category="preflight",
        description="返回自然语言 intent、按钮 action 和斜杠命令到 Writing Agent 工具的统一路由投影。",
        input_schema=object_schema(
            {
                "source": {"type": "string"},
                "approval_chain_opt_in_action_types": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "routes": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_route_preference_projection",
        module="writing_agent",
        category="preflight",
        description="返回对话入口当前路由与推荐 Agent 审批工具链的只读偏好投影，不改变运行时路由。",
        input_schema=object_schema(
            {
                "source": {"type": "string"},
                "approval_chain_opt_in_action_types": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "summary": {"type": "object"},
                "routes": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_route_preference_projection",
        internal=True,
        non_blocking_report=True,
        sort_key=11,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="plan_agent_route_approval_opt_in",
        module="writing_agent",
        category="preflight",
        description="返回对话 route 写入 approval-chain opt-in metadata 前的只读计划和 guardrails，不执行写入。",
        input_schema=object_schema(
            {
                "pending_action_id": {"type": "string"},
                "agent_route": {"type": "object"},
                "action_type": {"type": "string"},
                "source": {"type": "string"},
                "command_name": {"type": "string"},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "can_apply": {"type": "boolean"},
                "write_performed": {"type": "boolean"},
                "metadata_patch": {"type": "object"},
                "route_before": {"type": ["object", "null"]},
                "route_after": {"type": ["object", "null"]},
                "preference": {"type": ["object", "null"]},
                "suggestion": {"type": ["object", "null"]},
                "risk": {"type": "object"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_route_approval_opt_in_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=12,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="preview_pending_action_route_approval_opt_in_apply",
        module="writing_agent",
        category="preflight",
        description="只读预览对 pending action route 应用 approval-chain opt-in patch 后的 params diff，不执行写入。",
        input_schema=object_schema({"pending_action_id": {"type": "string"}}, required=("pending_action_id",)),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "write_performed": {"type": "boolean"},
                "pending_action_id": {"type": "string"},
                "pending_action_type": {"type": ["string", "null"]},
                "params_before": {"type": ["object", "null"]},
                "params_after": {"type": ["object", "null"]},
                "params_diff": {"type": "object"},
                "route_plan": {"type": ["object", "null"]},
                "risk": {"type": "object"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_route_approval_opt_in_apply_preview",
        internal=True,
        non_blocking_report=True,
        sort_key=13,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="preview_pending_action_route_approval_opt_in_apply_contract",
        module="writing_agent",
        category="preflight",
        description="只读生成 pending action route approval-chain opt-in apply 的审批契约和稳定确认哈希，不执行写入。",
        input_schema=object_schema({"pending_action_id": {"type": "string"}}, required=("pending_action_id",)),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "required_confirmation": {"type": "boolean"},
                "approval_contract_hash": {"type": ["string", "null"]},
                "approval_contract": {"type": ["object", "null"]},
                "route_apply_preview": {"type": "object"},
                "risk": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
                "recommended_next_tool_calls": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_route_approval_opt_in_apply_contract",
        internal=True,
        non_blocking_report=True,
        sort_key=14,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="apply_pending_action_route_approval_opt_in",
        module="writing_agent",
        category="preflight",
        description="确认审批契约后将 pending action route 切换到 Agent approval-chain opt-in，不执行 pending action。",
        input_schema=object_schema(
            {
                "pending_action_id": {"type": "string"},
                "confirm_apply": {"type": "boolean"},
                "approval_contract_hash": {"type": "string"},
                "approval_contract": {"type": "object"},
            },
            required=("pending_action_id", "confirm_apply", "approval_contract_hash", "approval_contract"),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "reason": {"type": "string"},
                "write_performed": {"type": "boolean"},
                "pending_action_id": {"type": ["string", "null"]},
                "pending_action_type": {"type": ["string", "null"]},
                "params_before": {"type": ["object", "null"]},
                "params_after": {"type": ["object", "null"]},
                "params_diff": {"type": "object"},
                "route_apply_preview": {"type": ["object", "null"]},
                "approval_verification": {"type": ["object", "null"]},
                "risk": {"type": "object"},
                "side_effects": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_route_approval_opt_in_apply",
        internal=True,
        non_blocking_report=False,
        sort_key=15,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="prepare_apply_pending_action_route_approval_opt_in",
        module="writing_agent",
        category="preflight",
        description="为 pending action route 的 Agent approval-chain opt-in 应用构建 Agent 计划审批契约，不写入。",
        input_schema=object_schema({"pending_action_id": {"type": "string"}}, required=("pending_action_id",)),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "prepare_version": {"type": "string"},
                "project_id": {"type": "string"},
                "pending_action_id": {"type": "string"},
                "target_type": {"type": "string"},
                "route_apply_approval_contract": {"type": "object"},
                "route_apply_approval_contract_hash": {"type": "string"},
                "route_apply_preview": {"type": "object"},
                "mutation_fingerprint": {"type": "object"},
                "tool_call_id": {"type": "string"},
                "resource_binding": {"type": "object"},
                "agent_plan": {"type": "object"},
                "agent_plan_approval_contract": {"type": "object"},
                "agent_plan_approval_contract_hash": {"type": "string"},
                "required_confirmation": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
            }
        ),
        target_type="agent_route_approval_opt_in_apply_approval",
        internal=True,
        non_blocking_report=True,
        sort_key=16,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="execute_apply_pending_action_route_approval_opt_in_with_approval",
        module="writing_agent",
        category="preflight",
        description="在 route contract 与 Agent plan approval 均确认后应用 pending action route opt-in。",
        input_schema=object_schema(
            {
                "pending_action_id": {"type": "string"},
                "confirm_execute": {"type": "boolean"},
                "route_apply_approval_contract_hash": {"type": "string"},
                "route_apply_approval_contract": {"type": "object"},
                "agent_plan_approval_contract_hash": {"type": "string"},
                "agent_plan_approval_contract": {"type": "object"},
            },
            required=(
                "pending_action_id",
                "confirm_execute",
                "route_apply_approval_contract_hash",
                "route_apply_approval_contract",
                "agent_plan_approval_contract_hash",
                "agent_plan_approval_contract",
            ),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "execute_version": {"type": "string"},
                "reason": {"type": "string"},
                "write_performed": {"type": "boolean"},
                "pending_action_id": {"type": ["string", "null"]},
                "pending_action_type": {"type": ["string", "null"]},
                "params_before": {"type": ["object", "null"]},
                "params_after": {"type": ["object", "null"]},
                "params_diff": {"type": "object"},
                "route_apply_preview": {"type": ["object", "null"]},
                "route_apply_approval_verification": {"type": ["object", "null"]},
                "agent_plan_approval_verification": {"type": "object"},
                "execution_resource_binding": {"type": "object"},
                "evidence": {"type": "object"},
                "side_effects": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_route_approval_opt_in_apply",
        internal=True,
        non_blocking_report=False,
        sort_key=17,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_dialog_control_plane_projection",
        module="writing_agent",
        category="preflight",
        description="返回对话 pending action control plane 的当前运行工具与推荐审批工具链投影，不改变运行时路由。",
        input_schema=object_schema({"action_type": {"type": "string"}}),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "summary": {"type": "object"},
                "actions": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_dialog_control_plane_projection",
        internal=True,
        non_blocking_report=True,
        sort_key=12,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_intent_projection",
        module="writing_agent",
        category="preflight",
        description="返回自然语言输入经 IntentRouter 规则匹配后的可解释投影报告。",
        input_schema=object_schema(
            {
                "text": {"type": "string"},
                "missing_items": {"type": "array"},
                "completed_items": {"type": "array"},
                "suggested_next_step": {"type": "string"},
            },
            required=("text",),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "rule_id": {"type": ["string", "null"]},
                "reason": {"type": ["string", "null"]},
                "candidate": {"type": ["object", "null"]},
                "agent_route": {"type": ["object", "null"]},
                "diagnosis": {"type": "object"},
                "extracted_params": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=11,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_reference_alignment",
        module="writing_agent",
        category="preflight",
        description="只读输出三个本地参考 Agent 项目的可复用模式、novelv3 已采纳决策和下一步工具建议。",
        input_schema=object_schema(),
        output_schema=_AGENT_REFERENCE_ALIGNMENT_OUTPUT,
        target_type="agent_reference_alignment",
        internal=True,
        non_blocking_report=True,
        sort_key=11,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_dogfood_evidence",
        module="writing_agent",
        category="preflight",
        description="只读输出真实长篇 dogfood / pressure-test 证据覆盖度，供 Agent 判断是否可继续生成与恢复。",
        input_schema=object_schema(),
        output_schema=_AGENT_DOGFOOD_EVIDENCE_OUTPUT,
        target_type="agent_dogfood_evidence",
        internal=True,
        non_blocking_report=True,
        sort_key=11,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_tool_contracts",
        module="writing_agent",
        category="preflight",
        description="只读输出 Writing Agent 工具契约快照、覆盖率和迁移差距，用于持续重构模块为 Agent 工具。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "include_gap_details": {"type": "boolean"},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "summary": {"type": "object"},
                "coverage": {"type": "object"},
                "tools": {"type": "array"},
                "gaps": {"type": "array"},
                "reference_alignment": {"type": "object"},
                "recommended_next_steps": {"type": "array"},
            }
        ),
        target_type="agent_tool_contracts",
        internal=True,
        non_blocking_report=True,
        sort_key=11,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_command_contracts",
        module="writing_agent",
        category="preflight",
        description="只读输出 Hermes slash 命令控制面的 Agent 契约快照、投影类型和依赖工具缺口。",
        input_schema=object_schema(),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "summary": {"type": "object"},
                "commands": {"type": "array"},
                "gaps": {"type": "array"},
                "recommended_next_tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_command_contracts",
        internal=True,
        non_blocking_report=True,
        sort_key=11,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_legacy_hermes_action_migration",
        module="writing_agent",
        category="preflight",
        description="只读输出 legacy Hermes 生成动作迁移为 Agent-native preview/approval/execute 工具的路线图。",
        input_schema=object_schema(),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "summary": {"type": "object"},
                "tools": {"type": "array"},
                "recommended_next_tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_migration_projection",
        internal=True,
        non_blocking_report=True,
        sort_key=11,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_write_gate_coverage",
        module="writing_agent",
        category="preflight",
        description="只读输出写入工具的 Agent 计划审批门禁覆盖度，用于选择下一批执行硬化目标。",
        input_schema=object_schema(),
        output_schema=_AGENT_WRITE_GATE_COVERAGE_OUTPUT,
        target_type="agent_write_gate_coverage",
        internal=True,
        non_blocking_report=True,
        sort_key=12,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_mutation_fingerprints",
        module="writing_agent",
        category="preflight",
        description="只读计算计划写入工具的稳定 mutation fingerprint，用于恢复、审批和冲突诊断绑定具体目标。",
        input_schema=object_schema(
            {
                "tools": {
                    "type": "array",
                    "items": object_schema(
                        {
                            "tool_name": {"type": "string"},
                            "params": {"type": "object"},
                        }
                    ),
                },
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "project_id": {"type": "string"},
                "summary": {"type": "object"},
                "fingerprints": {"type": "array"},
                "recommended_next_tools": {"type": "array"},
            }
        ),
        target_type="agent_mutation_fingerprint",
        internal=True,
        non_blocking_report=True,
        sort_key=12,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="preflight_writing",
        module="writing_agent",
        category="preflight",
        description="检查指定章节生成前的设定、大纲、前文、世界模型、检索和字数策略状态。",
        input_schema=_CHAPTER_PARAMS,
        output_schema=object_schema({"status": {"type": "string"}}),
        target_type="preflight",
        internal=True,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
)
