from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


_LONGFORM_MAINTENANCE_INPUT = object_schema(
    {
        "limit": {"type": "integer", "minimum": 1},
        "repair_limit": {"type": "integer", "minimum": 1},
        "post_approval_continuation_tools": {"type": "array"},
    }
)
_LONGFORM_MAINTENANCE_PREPARE_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "prepare_version": {"type": "string"},
        "project_id": {"type": "string"},
        "target_type": {"type": "string"},
        "mutation_fingerprint": {"type": "object"},
        "tool_call_id": {"type": "string"},
        "resource_binding": {"type": "object"},
        "agent_plan": {"type": "object"},
        "agent_plan_approval_contract": {"type": "object"},
        "agent_plan_approval_contract_hash": {"type": "string"},
        "required_confirmation": {"type": "object"},
        "side_effects": {"type": "object"},
        "recommended_next_tools": {"type": "array"},
        "post_approval_continuation_tools": {"type": "array"},
        "trace": {"type": "object"},
    }
)


AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="inspect_agent_trace_audit",
        module="writing_agent",
        category="trace",
        description="汇总 Writing Agent run、步骤、模型调用 Trace 和上下文块，帮助 Agent 解释执行链和失败原因。",
        input_schema=object_schema(
            {
                "run_id": {"type": "string"},
                "chapter_index": {"type": "integer", "minimum": 1},
                "task_id": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "audit": {"type": "object"},
                "run": {"type": "object"},
                "steps": {"type": "array"},
                "traces": {"type": "array"},
                "context": {"type": "object"},
                "failure": {"type": "object"},
                "recommended_actions": {"type": "array"},
                "profile_policy_audit": {"type": ["object", "null"]},
            }
        ),
        target_type="agent_trace_audit",
        internal=True,
        non_blocking_report=True,
        sort_key=6,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_memory_route",
        module="writing_agent",
        category="longform_memory",
        description="汇总长篇记忆、检索索引和维护状态，判断 Agent 下一步应读取上下文、修复记忆还是进入生成前检查。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "query": {"type": "string"},
                "include_context_summary": {"type": "boolean"},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "route": {"type": "object"},
                "longform_memory": {"type": "object"},
                "longform_maintenance": {"type": "object"},
                "retrieval": {"type": "object"},
                "diagnostics": {"type": "array"},
                "context_summary": {"type": "object"},
            }
        ),
        target_type="agent_memory_route",
        internal=True,
        non_blocking_report=True,
        sort_key=7,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="summarize_longform_context",
        module="writing_agent",
        category="longform_memory",
        description="汇总指定章节写作前的长篇记忆、检索证据和上下文来源，供 Agent 规划和生成前读取。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "query": {"type": "string"},
                "max_chars": {"type": "integer", "minimum": 500},
                "include_prompt_context": {"type": "boolean"},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "chapter_index": {"type": "integer"},
                "project": {"type": "object"},
                "progress": {"type": "object"},
                "context_summary": {"type": "object"},
                "sections": {"type": "array"},
                "source_sections": {"type": "array"},
                "source_section_keys": {"type": "array"},
                "diagnostics": {"type": "array"},
            }
        ),
        target_type="longform_context_summary",
        internal=True,
        non_blocking_report=True,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_context_compression_projection",
        module="writing_agent",
        category="longform_memory",
        description="只读投影章节上下文窗口、截断、压缩压力和 ContextGuard 断路风险，供 Agent 生成前自检。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "max_chars": {"type": "integer", "minimum": 500},
                "context_guard_failure_count": {"type": "integer", "minimum": 0},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "strategy": {"type": "object"},
                "summary": {"type": "object"},
                "risks": {"type": "array"},
                "recommended_next_tools": {"type": "array"},
                "recovery": {"type": "object"},
                "memory_provenance": {"type": "object"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_context_compression_projection",
        internal=True,
        non_blocking_report=True,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_memory_activation_plan",
        module="writing_agent",
        category="longform_memory",
        description="为目标章节生成长记忆激活计划，选择既往章节、伏笔、世界模型和风格锚点供生成前使用。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "query": {"type": "string"},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "activation": {"type": "object"},
                "coverage": {"type": "object"},
                "risks": {"type": "array"},
                "recommended_next_tools": {"type": "array"},
                "prompt_block": {"type": "string"},
                "memory_provenance": {"type": "object"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_memory_activation_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="repair_longform_maintenance",
        module="athena_longform",
        category="maintenance",
        description="修复长篇记忆和检索索引缺口，使后续章节生成可获得稳定上下文。",
        input_schema=_LONGFORM_MAINTENANCE_INPUT,
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "repaired_memory_count": {"type": "integer"},
                "repaired_retrieval_count": {"type": "integer"},
                "remaining": {"type": "object"},
            }
        ),
        target_type="longform_maintenance",
        internal=True,
        sort_key=9,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="prepare_repair_longform_maintenance",
        module="writing_agent",
        category="maintenance",
        description="为长篇记忆和检索维护修复构建 Agent 计划审批契约，不执行修复。",
        input_schema=_LONGFORM_MAINTENANCE_INPUT,
        output_schema=_LONGFORM_MAINTENANCE_PREPARE_OUTPUT,
        target_type="longform_maintenance_approval",
        internal=True,
        non_blocking_report=True,
        sort_key=9,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="execute_repair_longform_maintenance_with_approval",
        module="writing_agent",
        category="maintenance",
        description="在确认 Agent 计划审批契约后修复长篇记忆和检索维护缺口。",
        input_schema=object_schema(
            {
                "limit": {"type": "integer", "minimum": 1},
                "repair_limit": {"type": "integer", "minimum": 1},
                "confirm_execute": {"type": "boolean"},
                "approval_contract_hash": {"type": "string"},
                "approval_contract": {"type": "object"},
                "post_approval_continuation_tools": {"type": "array"},
            },
            required=("confirm_execute", "approval_contract_hash", "approval_contract"),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "execute_version": {"type": "string"},
                "project_id": {"type": "string"},
                "target_type": {"type": "string"},
                "repaired_memory_count": {"type": "integer"},
                "repaired_retrieval_count": {"type": "integer"},
                "remaining": {"type": "object"},
                "repair_result": {"type": "object"},
                "agent_plan_approval_verification": {"type": "object"},
                "approval_verification_event": {"type": "object"},
                "execution_resource_binding": {"type": "object"},
                "evidence": {"type": "object"},
                "side_effects": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
                "post_approval_continuation_tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="longform_maintenance",
        internal=True,
        sort_key=9,
        availability_checks=("project_exists",),
    ),
)
