from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


_CHAPTER_PARAMS = object_schema({"chapter_index": {"type": "integer", "minimum": 1}})
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


AGENT_CORE_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="describe_agent_tools",
        module="writing_agent",
        category="preflight",
        description="返回当前项目和章节下 Agent 可见工具、隐藏工具和缺失依赖诊断。",
        input_schema=_CHAPTER_PARAMS,
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "visible_tools": {"type": "array"},
                "hidden_tools": {"type": "array"},
                "diagnostics": {"type": "array"},
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
        input_schema=object_schema({"source": {"type": "string"}}),
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
        input_schema=object_schema({"source": {"type": "string"}}),
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
