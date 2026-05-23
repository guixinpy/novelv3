from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


_STATUS_OUTPUT = object_schema({"status": {"type": "string"}})
_CHAPTER_PARAMS = object_schema({"chapter_index": {"type": "integer", "minimum": 1}})
_REVISION_PATCH_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "reason": {"type": "string"},
        "message": {"type": "string"},
        "chapter_index": {"type": "integer"},
        "chapter_id": {"type": "string"},
        "revision_id": {"type": ["string", "null"]},
        "revision_index": {"type": "integer"},
        "base_version_id": {"type": "string"},
        "result_version_id": {"type": "string"},
        "applied_replacement_count": {"type": "integer"},
        "applied_replacements": {"type": "array"},
        "word_count": {"type": "integer"},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_next_tools": {"type": "array"},
        "unsupported_actions": {"type": "array"},
    }
)
_CHAPTER_EXPANSION_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "reason": {"type": "string"},
        "message": {"type": "string"},
        "chapter_index": {"type": "integer"},
        "chapter_id": {"type": "string"},
        "revision_id": {"type": "string"},
        "revision_index": {"type": "integer"},
        "base_version_id": {"type": "string"},
        "result_version_id": {"type": "string"},
        "trace_id": {"type": "string"},
        "previous_word_count": {"type": "integer"},
        "word_count": {"type": "integer"},
        "target_min_word_count": {"type": "integer"},
        "target_max_word_count": {"type": ["integer", "null"]},
        "change_summary": {"type": "string"},
        "warnings": {"type": "array"},
        "pending_world_model_proposal_count": {"type": "integer"},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_next_tools": {"type": "array"},
    }
)
_CHAPTER_COMPRESSION_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "reason": {"type": "string"},
        "message": {"type": "string"},
        "chapter_index": {"type": "integer"},
        "chapter_id": {"type": "string"},
        "revision_id": {"type": "string"},
        "revision_index": {"type": "integer"},
        "base_version_id": {"type": "string"},
        "result_version_id": {"type": "string"},
        "trace_id": {"type": "string"},
        "previous_word_count": {"type": "integer"},
        "word_count": {"type": "integer"},
        "target_min_word_count": {"type": "integer"},
        "target_max_word_count": {"type": "integer"},
        "forbidden_terms": {"type": "array"},
        "remaining_forbidden_terms": {"type": "array"},
        "postcondition_retry_count": {"type": "integer"},
        "compression_attempt_count": {"type": "integer"},
        "failed_attempts": {"type": "array"},
        "deterministic_repair_applied": {"type": "boolean"},
        "deterministic_trim_applied": {"type": "boolean"},
        "change_summary": {"type": "string"},
        "warnings": {"type": "array"},
        "pending_world_model_proposal_count": {"type": "integer"},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_next_tools": {"type": "array"},
    }
)


REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="review_chapter_quality",
        module="review",
        category="review",
        description="审查章节是否像正文、是否完整、节奏和字数是否明显异常。",
        input_schema=_CHAPTER_PARAMS,
        output_schema=_STATUS_OUTPUT,
        target_type="review",
        internal=True,
        non_blocking_report=True,
        sort_key=90,
        availability_checks=("generated_chapter_exists",),
    ),
    AgentToolDescriptor(
        name="review_chapter_continuity",
        module="review",
        category="review",
        description="审查章节与前文、人物状态、关键名词和伏笔的连续性。",
        input_schema=object_schema({"chapter_index": {"type": "integer", "minimum": 1}, "lookback": {"type": "integer"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="review",
        internal=True,
        non_blocking_report=True,
        sort_key=100,
        availability_checks=("generated_chapter_exists",),
    ),
    AgentToolDescriptor(
        name="plan_chapter_revision",
        module="review",
        category="review",
        description="基于质量和连续性审查输出章节修订计划。",
        input_schema=_CHAPTER_PARAMS,
        output_schema=_STATUS_OUTPUT,
        target_type="revision_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=110,
        availability_checks=("generated_chapter_exists",),
    ),
    AgentToolDescriptor(
        name="create_revision_draft",
        module="revision",
        category="revision",
        description="根据修订计划创建章节修订草稿。",
        input_schema=_CHAPTER_PARAMS,
        output_schema=_STATUS_OUTPUT,
        target_type="revision",
        internal=True,
        sort_key=120,
        availability_checks=("generated_chapter_exists",),
    ),
    AgentToolDescriptor(
        name="apply_planner_revision_patch",
        module="revision",
        category="revision",
        description="应用由 Agent 修订计划生成的章节补丁。",
        input_schema=object_schema({"chapter_index": {"type": "integer", "minimum": 1}, "revision_id": {"type": "string"}}),
        output_schema=_REVISION_PATCH_OUTPUT,
        target_type="revision",
        internal=True,
        sort_key=130,
        availability_checks=("generated_chapter_exists",),
    ),
    AgentToolDescriptor(
        name="expand_chapter_to_target",
        module="revision",
        category="revision",
        description="在保持剧情和设定一致的前提下扩写章节到目标篇幅。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "min_word_count": {"type": "integer"},
                "extra_instruction": {"type": "string"},
            }
        ),
        output_schema=_CHAPTER_EXPANSION_OUTPUT,
        target_type="revision",
        internal=True,
        sort_key=140,
        availability_checks=("generated_chapter_exists",),
    ),
    AgentToolDescriptor(
        name="compress_chapter_to_target",
        module="revision",
        category="revision",
        description="在保留关键信息的前提下压缩明显失控的章节篇幅。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "target_max_word_count": {"type": "integer"},
                "extra_instruction": {"type": "string"},
                "forbidden_terms": {"type": "array"},
            }
        ),
        output_schema=_CHAPTER_COMPRESSION_OUTPUT,
        target_type="revision",
        internal=True,
        sort_key=150,
        availability_checks=("generated_chapter_exists",),
    ),
)
