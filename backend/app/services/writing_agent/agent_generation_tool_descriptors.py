from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


_STATUS_OUTPUT = object_schema({"status": {"type": "string"}})
_CHAPTER_PARAMS = object_schema({"chapter_index": {"type": "integer", "minimum": 1}})
_WINDOW_PARAMS = object_schema(
    {
        "chapter_index": {"type": "integer", "minimum": 1},
        "start_chapter": {"type": "integer", "minimum": 1},
        "end_chapter": {"type": "integer", "minimum": 1},
        "command_args": {"type": "string"},
        "confirm_execute": {"type": "boolean"},
    }
)
_OUTLINE_WINDOW_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "start_chapter": {"type": "integer"},
        "end_chapter": {"type": "integer"},
        "outline_id": {"type": "string"},
        "total_chapters": {"type": "integer"},
        "added_chapter_count": {"type": "integer"},
        "merge": {"type": "object"},
        "trace_id": {"type": ["string", "null"]},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_next_tools": {"type": "array"},
    }
)


AGENT_GENERATION_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="expand_outline_window",
        module="athena_narrative",
        category="generation",
        description="补齐或扩展指定章节窗口的大纲，并注入 Agent 长篇约束。",
        input_schema=_WINDOW_PARAMS,
        output_schema=_OUTLINE_WINDOW_OUTPUT,
        target_type="outline",
        internal=True,
        sort_key=45,
        availability_checks=("setup_exists", "storyline_exists", "outline_exists"),
    ),
    AgentToolDescriptor(
        name="prepare_expand_outline_window_execution",
        module="writing_agent",
        category="generation",
        description="为指定章节窗口的大纲扩展构建 Agent 计划审批契约，不修改大纲。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "start_chapter": {"type": "integer", "minimum": 1},
                "end_chapter": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "prepare_version": {"type": "string"},
                "project_id": {"type": "string"},
                "start_chapter": {"type": "integer"},
                "end_chapter": {"type": "integer"},
                "target_type": {"type": "string"},
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
        target_type="outline_window_expansion_approval",
        internal=True,
        non_blocking_report=True,
        sort_key=46,
        availability_checks=("setup_exists", "storyline_exists", "outline_exists"),
    ),
    AgentToolDescriptor(
        name="execute_expand_outline_window_with_approval",
        module="writing_agent",
        category="generation",
        description="在确认 Agent 计划审批契约后扩展指定章节窗口的大纲。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "start_chapter": {"type": "integer", "minimum": 1},
                "end_chapter": {"type": "integer", "minimum": 1},
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
                "start_chapter": {"type": "integer"},
                "end_chapter": {"type": "integer"},
                "outline_id": {"type": "string"},
                "total_chapters": {"type": "integer"},
                "added_chapter_count": {"type": "integer"},
                "merge": {"type": "object"},
                "trace_id": {"type": ["string", "null"]},
                "agent_plan_approval_verification": {"type": "object"},
                "execution_resource_binding": {"type": "object"},
                "evidence": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
            }
        ),
        target_type="outline",
        internal=True,
        sort_key=47,
        availability_checks=("setup_exists", "storyline_exists", "outline_exists"),
    ),
    AgentToolDescriptor(
        name="generate_chapter",
        module="hermes",
        category="generation",
        description="生成指定章节正文，并融合前文状态、检索、Athena 和 Agent 约束。",
        input_schema=_CHAPTER_PARAMS,
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "chapter_index": {"type": "integer"},
                "trace_id": {"type": "string"},
                "athena_analysis": {"type": "object"},
                "agent_continuity_feedback": {"type": "object"},
                "agent_generation_feedback": {"type": "object"},
                "chapter_length_decision": {"type": "object"},
                "world_model_proposal_diagnostic": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
            }
        ),
        target_type="chapter",
        sort_key=50,
        availability_checks=("setup_exists", "outline_chapter_exists", "previous_chapter_exists"),
        warning_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="prepare_generate_chapter_execution",
        module="writing_agent",
        category="generation",
        description="为直接章节生成构建 Agent 计划审批契约，不执行正文生成。",
        input_schema=object_schema({"chapter_index": {"type": "integer", "minimum": 1}}, required=("chapter_index",)),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "prepare_version": {"type": "string"},
                "chapter_index": {"type": "integer"},
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
        target_type="chapter_generation_approval",
        internal=True,
        non_blocking_report=True,
        sort_key=51,
        availability_checks=("project_exists", "outline_chapter_exists", "previous_chapter_exists"),
        warning_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="execute_generate_chapter_with_approval",
        module="writing_agent",
        category="generation",
        description="在确认 Agent 计划审批契约后执行指定章节正文生成。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "command_args": {"type": "string"},
                "confirm_execute": {"type": "boolean"},
                "approval_contract_hash": {"type": "string"},
                "approval_contract": {"type": "object"},
            },
            required=("chapter_index", "confirm_execute", "approval_contract_hash", "approval_contract"),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "execute_version": {"type": "string"},
                "chapter_index": {"type": "integer"},
                "trace_id": {"type": "string"},
                "agent_plan_approval_verification": {"type": "object"},
                "execution_resource_binding": {"type": "object"},
                "evidence": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
            }
        ),
        target_type="chapter",
        internal=True,
        sort_key=52,
        availability_checks=("project_exists", "outline_chapter_exists", "previous_chapter_exists"),
        warning_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="backfill_outline_gaps",
        module="athena_narrative",
        category="maintenance",
        description="根据已生成章节回填缺失的历史章节大纲。",
        input_schema=object_schema({"before_chapter": {"type": "integer", "minimum": 1}}),
        output_schema=_STATUS_OUTPUT,
        target_type="outline",
        internal=True,
        sort_key=80,
        availability_checks=("outline_exists",),
    ),
    AgentToolDescriptor(
        name="prepare_backfill_outline_gaps_execution",
        module="writing_agent",
        category="maintenance",
        description="为历史章节大纲缺口回填构建 Agent 计划审批契约，不修改大纲。",
        input_schema=object_schema({"before_chapter": {"type": "integer", "minimum": 1}}),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "prepare_version": {"type": "string"},
                "project_id": {"type": "string"},
                "before_chapter": {"type": ["integer", "null"]},
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
        target_type="outline_backfill_approval",
        internal=True,
        non_blocking_report=True,
        sort_key=81,
        availability_checks=("outline_exists",),
    ),
    AgentToolDescriptor(
        name="execute_backfill_outline_gaps_with_approval",
        module="writing_agent",
        category="maintenance",
        description="在确认 Agent 计划审批契约后回填缺失的历史章节大纲。",
        input_schema=object_schema(
            {
                "before_chapter": {"type": "integer", "minimum": 1},
                "confirm_execute": {"type": "boolean"},
                "approval_contract_hash": {"type": "string"},
                "approval_contract": {"type": "object"},
            },
            required=("confirm_execute", "approval_contract_hash", "approval_contract"),
        ),
        output_schema=_STATUS_OUTPUT,
        target_type="outline",
        internal=True,
        sort_key=82,
        availability_checks=("outline_exists",),
    ),
)
