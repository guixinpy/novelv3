from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


_STATUS_OUTPUT = object_schema({"status": {"type": "string"}})
_CHAPTER_PARAMS = object_schema({"chapter_index": {"type": "integer", "minimum": 1}})
_SETUP_WORLD_MODEL_IMPORT_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "profile_version": {"type": "integer"},
        "project_profile_version_id": {"type": "string"},
        "created": {"type": "object"},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_next_tools": {"type": "array"},
    }
)
_CONTINUITY_ANCHOR_SEED_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "project_id": {"type": "string"},
        "profile_version": {"type": ["integer", "null"]},
        "proposal_bundle_id": {"type": ["string", "null"]},
        "created_item_count": {"type": "integer"},
        "created_items": {"type": "array"},
        "pending_anchor_count": {"type": "integer"},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_actions": {"type": "array"},
    }
)


WORLD_MODEL_AGENT_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="import_setup_world_model",
        module="athena_world_model",
        category="athena_world_model",
        description="将项目设定导入 Athena 世界模型，形成可审计的初始事实层。",
        input_schema=object_schema(),
        output_schema=_SETUP_WORLD_MODEL_IMPORT_OUTPUT,
        target_type="world_model",
        internal=True,
        sort_key=60,
        availability_checks=("setup_exists",),
    ),
    AgentToolDescriptor(
        name="analyze_chapter_world_model",
        module="athena_world_model",
        category="athena_world_model",
        description="分析已生成章节，抽取世界模型候选事实和提案。",
        input_schema=_CHAPTER_PARAMS,
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        sort_key=70,
        availability_checks=("generated_chapter_exists", "world_model_profile_exists"),
    ),
    AgentToolDescriptor(
        name="review_world_model_proposals",
        module="athena_world_model",
        category="athena_world_model",
        description="查看待处理的世界模型提案和冲突摘要。",
        input_schema=object_schema({"offset": {"type": "integer"}, "limit": {"type": "integer"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=160,
        availability_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_world_model_route",
        module="writing_agent",
        category="athena_world_model",
        description="汇总世界模型 profile、确认事实和待审提案压力，判断 Agent 是否可继续生成或应先处理世界模型。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "subject_ref": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "route": {"type": "object"},
                "profile": {"type": "object"},
                "fact_summary": {"type": "object"},
                "facts": {"type": "array"},
                "proposal_pressure": {"type": "object"},
                "recommended_actions": {"type": "array"},
            }
        ),
        target_type="agent_world_model_route",
        internal=True,
        non_blocking_report=True,
        sort_key=161,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="plan_world_model_proposal_resolution",
        module="athena_world_model",
        category="athena_world_model",
        description="为世界模型提案生成处理计划。",
        input_schema=object_schema({"offset": {"type": "integer"}, "limit": {"type": "integer"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=170,
        availability_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="preview_world_model_proposal_resolution",
        module="athena_world_model",
        category="athena_world_model",
        description="预览世界模型提案处理决策的影响。",
        input_schema=object_schema({"decisions": {"type": "array"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=180,
        availability_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="apply_world_model_proposal_resolution",
        module="athena_world_model",
        category="athena_world_model",
        description="在确认后应用世界模型提案处理决策。",
        input_schema=object_schema(
            {
                "decisions": {"type": "array"},
                "confirm_apply": {"type": "boolean"},
                "approval_contract_hash": {"type": "string"},
                "approval_contract": {"type": "object"},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "project_id": {"type": "string"},
                "profile_version": {"type": ["integer", "null"]},
                "before_actionable_items": {"type": "integer"},
                "after_actionable_items": {"type": "integer"},
                "applied_count": {"type": "integer"},
                "applied_reviews": {"type": "array"},
                "invalid_decision_count": {"type": "integer"},
                "invalid_decisions": {"type": "array"},
                "requires_confirmation": {"type": "boolean"},
                "can_auto_apply": {"type": "boolean"},
                "should_generate_next_chapter": {"type": "boolean"},
                "recommended_actions": {"type": "array"},
            }
        ),
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=190,
        availability_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="draft_world_model_proposal_resolution_decisions",
        module="athena_world_model",
        category="athena_world_model",
        description="为待处理世界模型提案草拟批量处理决策。",
        input_schema=object_schema(
            {
                "limit": {"type": "integer"},
                "predicate_policies": {"type": "object"},
                "include_unclassified": {"type": "boolean"},
            }
        ),
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=200,
        availability_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="draft_high_value_world_proposal_resolution_decisions",
        module="athena_world_model",
        category="athena_world_model",
        description="为高价值剧情事实提案草拟保守处理决策。",
        input_schema=object_schema({"limit": {"type": "integer"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=205,
        availability_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="seed_continuity_anchor_proposals",
        module="athena_world_model",
        category="maintenance",
        description="为关键连续性锚点生成世界模型提案。",
        input_schema=object_schema(),
        output_schema=_CONTINUITY_ANCHOR_SEED_OUTPUT,
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=210,
        availability_checks=("world_model_profile_exists",),
    ),
)
