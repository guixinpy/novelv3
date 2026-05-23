from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


_COMMAND_ARGS_INPUT = object_schema({"command_args": {"type": "string"}})
_OUTLINE_PREVIEW_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "preview_version": {"type": "string"},
        "project_id": {"type": "string"},
        "target_type": {"type": "string"},
        "command_args": {"type": ["string", "null"]},
        "mutation_fingerprint": {"type": "object"},
        "tool_call_id": {"type": "string"},
        "resource_binding": {"type": "object"},
        "agent_plan": {"type": "object"},
        "side_effects": {"type": "object"},
        "recommended_next_tools": {"type": "array"},
        "trace": {"type": "object"},
    }
)
_OUTLINE_PREPARE_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "prepare_version": {"type": "string"},
        "project_id": {"type": "string"},
        "command_args": {"type": ["string", "null"]},
        "mutation_fingerprint": {"type": "object"},
        "tool_call_id": {"type": "string"},
        "resource_binding": {"type": "object"},
        "agent_plan": {"type": "object"},
        "agent_plan_approval_contract": {"type": "object"},
        "agent_plan_approval_contract_hash": {"type": "string"},
        "required_confirmation": {"type": "object"},
        "side_effects": {"type": "object"},
        "recommended_next_tools": {"type": "array"},
        "trace": {"type": "object"},
    }
)


OUTLINE_GENERATION_AGENT_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="preview_generate_outline_execution",
        module="writing_agent",
        category="generation",
        description="预览章节大纲生成的 Agent 写入计划，不执行生成。",
        input_schema=_COMMAND_ARGS_INPUT,
        output_schema=_OUTLINE_PREVIEW_OUTPUT,
        target_type="outline_generation_preview",
        internal=True,
        non_blocking_report=True,
        sort_key=41,
        availability_checks=("setup_exists", "storyline_exists"),
    ),
    AgentToolDescriptor(
        name="prepare_generate_outline_execution",
        module="writing_agent",
        category="generation",
        description="为章节大纲生成构建 Agent 计划审批契约，不执行生成。",
        input_schema=_COMMAND_ARGS_INPUT,
        output_schema=_OUTLINE_PREPARE_OUTPUT,
        target_type="outline_generation_approval",
        internal=True,
        non_blocking_report=True,
        sort_key=42,
        availability_checks=("setup_exists", "storyline_exists"),
    ),
    AgentToolDescriptor(
        name="execute_generate_outline_with_approval",
        module="writing_agent",
        category="generation",
        description="在确认 Agent 计划审批契约后执行章节大纲生成。",
        input_schema=object_schema(
            {
                "command_args": {"type": "string"},
                "confirm_execute": {"type": "boolean"},
                "approval_contract_hash": {"type": "string"},
                "approval_contract": {"type": "object"},
            },
            required=("confirm_execute", "approval_contract_hash", "approval_contract"),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "execute_version": {"type": "string"},
                "project_id": {"type": "string"},
                "target_type": {"type": "string"},
                "trace_id": {"type": ["string", "null"]},
                "agent_plan_approval_verification": {"type": "object"},
                "approval_verification_event": {"type": "object"},
                "execution_resource_binding": {"type": "object"},
                "evidence": {"type": "object"},
                "side_effects": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="outline",
        internal=True,
        sort_key=43,
        availability_checks=("setup_exists", "storyline_exists"),
    ),
)
