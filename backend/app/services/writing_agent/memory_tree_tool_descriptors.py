from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema

_MEMORY_TREE_SUMMARY_INPUT_PROPERTIES = {
    "chapter_index": {"type": "integer", "minimum": 1},
    "quality_chapter_index": {"type": "integer", "minimum": 1},
    "quality_query": {"type": "string"},
    "post_approval_continuation_tools": {"type": "array"},
}
_MEMORY_TREE_SUMMARY_PREPARE_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "prepare_version": {"type": "string"},
        "project_id": {"type": "string"},
        "target_type": {"type": "string"},
        "summary_plan": {"type": "object"},
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
_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_INPUT_PROPERTIES = {
    "candidate_trace_id": {"type": "string"},
    "quality_chapter_index": {"type": "integer", "minimum": 1},
    "quality_query": {"type": "string"},
    "post_approval_continuation_tools": {"type": "array"},
}
_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_BATCH_INPUT_PROPERTIES = {
    "candidate_trace_ids": {"type": "array"},
    "chapter_index": {"type": "integer", "minimum": 1},
    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
    "quality_query": {"type": "string"},
}
_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_BATCH_EXECUTE_INPUT_PROPERTIES = {
    "confirm_execute": {"type": "boolean"},
    "candidate_executions": {"type": "array"},
}
_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_PREPARE_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "prepare_version": {"type": "string"},
        "project_id": {"type": "string"},
        "target_type": {"type": "string"},
        "candidate_summary": {"type": "object"},
        "summary_plan": {"type": "object"},
        "mutation_fingerprint": {"type": "object"},
        "tool_call_id": {"type": "string"},
        "resource_binding": {"type": "object"},
        "agent_plan": {"type": "object"},
        "agent_plan_approval_contract": {"type": "object"},
        "agent_plan_approval_contract_hash": {"type": "string"},
        "required_confirmation": {"type": "object"},
        "side_effects": {"type": "object"},
        "recommended_next_tools": {"type": "array"},
        "recommended_next_tool_calls": {"type": "array"},
        "post_approval_continuation_tools": {"type": "array"},
        "trace": {"type": "object"},
    }
)
_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_BATCH_PREPARE_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "prepare_version": {"type": "string"},
        "project_id": {"type": "string"},
        "target_type": {"type": "string"},
        "filters": {"type": "object"},
        "summary": {"type": "object"},
        "candidate_preparations": {"type": "array"},
        "required_confirmation": {"type": "object"},
        "side_effects": {"type": "object"},
        "recommended_next_tools": {"type": "array"},
        "recommended_next_tool_calls": {"type": "array"},
        "trace": {"type": "object"},
    }
)
_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_BATCH_EXECUTE_OUTPUT = object_schema(
    {
        "status": {"type": "string"},
        "execute_version": {"type": "string"},
        "project_id": {"type": "string"},
        "target_type": {"type": "string"},
        "reason": {"type": "string"},
        "summary": {"type": "object"},
        "candidate_results": {"type": "array"},
        "side_effects": {"type": "object"},
        "recommended_next_tools": {"type": "array"},
        "trace": {"type": "object"},
    }
)


MEMORY_TREE_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="inspect_agent_memory_tree",
        module="writing_agent",
        category="longform_memory",
        description="只读投影长篇记忆树，按 volume/chapter/scene/beat 层级汇总章节内容、Outline、Storyline 和 LongformMemory 来源。",
        input_schema=object_schema(
            {
                "level": {"type": "string", "enum": ["volume", "chapter", "scene", "beat"]},
                "node_id": {"type": "string"},
                "expand_node_id": {"type": "string"},
                "chapter_index": {"type": "integer", "minimum": 1},
                "query": {"type": "string"},
                "include_ancestors": {"type": "boolean"},
                "max_depth": {"type": "integer", "minimum": 0},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "levels": {"type": "array"},
                "filters": {"type": "object"},
                "navigation": {"type": "object"},
                "summary": {"type": "object"},
                "roots": {"type": "array"},
                "nodes": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_memory_tree",
        internal=True,
        non_blocking_report=True,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_memory_tree_quality",
        module="writing_agent",
        category="longform_memory",
        description="只读审计 Memory Tree 的节点覆盖、摘要支撑和语义探针匹配情况，作为真实长篇质量验证的可审计基线。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "query": {"type": "string"},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "filters": {"type": "object"},
                "coverage": {"type": "object"},
                "semantic_probe": {"type": "object"},
                "diagnostics": {"type": "array"},
                "recommended_next_tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_memory_tree_quality",
        internal=True,
        non_blocking_report=True,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="build_agent_memory_tree_llm_summary_plan",
        module="writing_agent",
        category="longform_memory",
        description="只读构建 Memory Tree 章级 LLM 摘要计划，返回证据窗口、Trace 要求、prompt 契约和质量复核门槛，不执行模型调用或写入。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "query": {"type": "string"},
                "max_source_chars": {"type": "integer", "minimum": 120},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "summary_target": {"type": "object"},
                "evidence_window": {"type": "object"},
                "llm_prompt_contract": {"type": "object"},
                "quality_gate": {"type": "object"},
                "side_effects": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_memory_tree_llm_summary_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=9,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="summarize_agent_memory_tree_llm_candidate",
        module="writing_agent",
        category="longform_memory",
        description="基于 Memory Tree 章级 LLM 摘要计划生成可审计候选摘要，记录模型调用 Trace，但不写入 LongformMemory。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "query": {"type": "string"},
                "max_source_chars": {"type": "integer", "minimum": 120},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "summary_target": {"type": "object"},
                "evidence_window": {"type": "object"},
                "candidate": {"type": "object"},
                "quality_gate": {"type": "object"},
                "candidate_write_policy": {"type": "object"},
                "side_effects": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_memory_tree_llm_summary_candidate",
        internal=True,
        non_blocking_report=True,
        sort_key=9,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_memory_tree_llm_candidates",
        module="writing_agent",
        category="longform_memory",
        description="只读检查已记录在模型调用 Trace 中的 Memory Tree LLM 摘要候选，便于候选复核和后续审批式物化。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "filters": {"type": "object"},
                "summary": {"type": "object"},
                "candidates": {"type": "array"},
                "recommended_next_tools": {"type": "array"},
                "recommended_next_tool_calls": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_memory_tree_llm_summary_candidate_trace",
        internal=True,
        non_blocking_report=True,
        sort_key=9,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="record_agent_memory_tree_summaries",
        module="writing_agent",
        category="longform_memory",
        description="生成并持久化 Memory Tree 的卷级和章级摘要节点，写入 LongformMemory 供后续浏览和检索使用。",
        input_schema=object_schema({"chapter_index": {"type": "integer", "minimum": 1}}),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "reason": {"type": "string"},
                "required_approval": {"type": "object"},
                "summary": {"type": "object"},
                "nodes": {"type": "array"},
                "side_effects": {"type": "object"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_memory_tree_summary",
        internal=True,
        non_blocking_report=False,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="record_agent_memory_tree_llm_candidate_summary",
        module="writing_agent",
        category="longform_memory",
        description="将已审批的 Memory Tree LLM 候选摘要持久化为章级 LongformMemory 摘要；直接调用只返回审批要求，不执行写入。",
        input_schema=object_schema(
            {
                "candidate_trace_id": {"type": "string"},
                "quality_chapter_index": {"type": "integer", "minimum": 1},
                "quality_query": {"type": "string"},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "reason": {"type": "string"},
                "required_approval": {"type": "object"},
                "materialization": {"type": "object"},
                "side_effects": {"type": "object"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_memory_tree_llm_candidate_summary",
        internal=True,
        non_blocking_report=False,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="prepare_record_agent_memory_tree_llm_candidate_summary",
        module="writing_agent",
        category="longform_memory",
        description="为 Memory Tree LLM 候选摘要写入构建 trace 绑定的 Agent 计划审批契约，不执行写入。",
        input_schema=object_schema(_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_INPUT_PROPERTIES),
        output_schema=_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_PREPARE_OUTPUT,
        target_type="agent_memory_tree_llm_candidate_summary_approval",
        internal=True,
        non_blocking_report=True,
        sort_key=9,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="prepare_record_agent_memory_tree_llm_candidate_summaries_batch",
        module="writing_agent",
        category="longform_memory",
        description="为多个 Memory Tree LLM 候选摘要批量构建逐条 trace 绑定的 Agent 计划审批契约，不执行写入。",
        input_schema=object_schema(_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_BATCH_INPUT_PROPERTIES),
        output_schema=_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_BATCH_PREPARE_OUTPUT,
        target_type="agent_memory_tree_llm_candidate_summary_batch_approval",
        internal=True,
        non_blocking_report=True,
        sort_key=9,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="execute_record_agent_memory_tree_llm_candidate_summary_with_approval",
        module="writing_agent",
        category="longform_memory",
        description="验证 trace 绑定的 Agent 计划审批契约后，将选中的 Memory Tree LLM 候选摘要写入 LongformMemory 并返回质量复核。",
        input_schema=object_schema(
            {
                **_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_INPUT_PROPERTIES,
                "confirm_execute": {"type": "boolean"},
                "approval_contract_hash": {"type": "string"},
                "approval_contract": {"type": "object"},
            },
            required=("candidate_trace_id", "confirm_execute", "approval_contract_hash", "approval_contract"),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "execute_version": {"type": "string"},
                "project_id": {"type": "string"},
                "target_type": {"type": "string"},
                "materialization": {"type": "object"},
                "post_materialization_quality": {"type": "object"},
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
        target_type="agent_memory_tree_llm_candidate_summary",
        internal=True,
        non_blocking_report=False,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="execute_record_agent_memory_tree_llm_candidate_summaries_batch_with_approval",
        module="writing_agent",
        category="longform_memory",
        description="逐条验证 Memory Tree LLM 候选摘要审批契约后批量写入已审批候选；每个候选仍必须携带独立审批 payload。",
        input_schema=object_schema(
            _MEMORY_TREE_LLM_CANDIDATE_SUMMARY_BATCH_EXECUTE_INPUT_PROPERTIES,
            required=("confirm_execute", "candidate_executions"),
        ),
        output_schema=_MEMORY_TREE_LLM_CANDIDATE_SUMMARY_BATCH_EXECUTE_OUTPUT,
        target_type="agent_memory_tree_llm_candidate_summary_batch",
        internal=True,
        non_blocking_report=False,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="prepare_record_agent_memory_tree_summaries",
        module="writing_agent",
        category="longform_memory",
        description="为 Memory Tree 卷级和章级摘要物化构建 Agent 计划审批契约，不执行写入。",
        input_schema=object_schema(_MEMORY_TREE_SUMMARY_INPUT_PROPERTIES),
        output_schema=_MEMORY_TREE_SUMMARY_PREPARE_OUTPUT,
        target_type="agent_memory_tree_summary_approval",
        internal=True,
        non_blocking_report=True,
        sort_key=9,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="execute_record_agent_memory_tree_summaries_with_approval",
        module="writing_agent",
        category="longform_memory",
        description="在确认 Agent 计划审批契约后物化 Memory Tree 摘要，并立即返回质量复核投影。",
        input_schema=object_schema(
            {
                **_MEMORY_TREE_SUMMARY_INPUT_PROPERTIES,
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
                "materialization": {"type": "object"},
                "post_materialization_quality": {"type": "object"},
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
        target_type="agent_memory_tree_summary",
        internal=True,
        non_blocking_report=False,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
)
