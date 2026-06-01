from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


_KNOWLEDGE_CANDIDATE_INPUT_PROPERTIES = {
    "memory_type": {"type": "string"},
    "title": {"type": "string"},
    "summary": {"type": "string"},
    "source_refs": {"type": "array"},
    "confidence": {"type": "number"},
    "status": {"type": "string"},
    "tags": {"type": "array"},
}
_KNOWLEDGE_CANDIDATE_REQUIRED = ("memory_type", "title", "summary", "source_refs")
_KNOWLEDGE_CANDIDATE_PREPARE_OUTPUT = object_schema(
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


KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="inspect_agent_knowledge_base_route",
        module="writing_agent",
        category="knowledge_base",
        description="汇总作者偏好、项目策略、学习规则和写法参考，供 Agent 在不污染世界真相的前提下读取创作记忆。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "query": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "route": {"type": "object"},
                "author_preferences": {"type": "object"},
                "project_strategy": {"type": "object"},
                "learned_rules": {"type": "object"},
                "reference_patterns": {"type": "object"},
                "diagnostics": {"type": "array"},
                "recommended_next_tools": {"type": "array"},
            }
        ),
        target_type="agent_knowledge_base_route",
        internal=True,
        non_blocking_report=True,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="plan_post_chapter_memory_capture",
        module="writing_agent",
        category="knowledge_base",
        description="根据已生成章节和审稿证据规划章节后长期记忆沉淀，只返回候选项和审批下一步，不直接写入知识库。",
        input_schema=object_schema(
            {"chapter_index": {"type": "integer", "minimum": 1}},
            required=("chapter_index",),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "project_id": {"type": "string"},
                "chapter_index": {"type": "integer"},
                "target_type": {"type": "string"},
                "capture_status": {"type": "string"},
                "summary": {"type": "object"},
                "candidates": {"type": "array"},
                "recommended_next_tools": {"type": "array"},
                "memory_provenance": {"type": "object"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_post_chapter_memory_capture_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="record_agent_knowledge_base_candidate",
        module="writing_agent",
        category="knowledge_base",
        description="记录知识库候选项，用于沉淀作者偏好、项目策略、写法模式和自优化经验，不写入世界真相。",
        input_schema=object_schema(_KNOWLEDGE_CANDIDATE_INPUT_PROPERTIES, required=_KNOWLEDGE_CANDIDATE_REQUIRED),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "action": {"type": "string"},
                "candidate": {"type": "object"},
                "candidate_count": {"type": "integer"},
            }
        ),
        target_type="agent_knowledge_base_candidate",
        internal=True,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="prepare_record_agent_knowledge_base_candidate",
        module="writing_agent",
        category="knowledge_base",
        description="为知识库候选项写入构建 Agent 计划审批契约，不执行写入。",
        input_schema=object_schema(_KNOWLEDGE_CANDIDATE_INPUT_PROPERTIES, required=_KNOWLEDGE_CANDIDATE_REQUIRED),
        output_schema=_KNOWLEDGE_CANDIDATE_PREPARE_OUTPUT,
        target_type="agent_knowledge_base_candidate_approval",
        internal=True,
        non_blocking_report=True,
        sort_key=11,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="execute_record_agent_knowledge_base_candidate_with_approval",
        module="writing_agent",
        category="knowledge_base",
        description="在确认 Agent 计划审批契约后记录知识库候选项。",
        input_schema=object_schema(
            {
                **_KNOWLEDGE_CANDIDATE_INPUT_PROPERTIES,
                "confirm_execute": {"type": "boolean"},
                "approval_contract_hash": {"type": "string"},
                "approval_contract": {"type": "object"},
                "post_approval_continuation_tools": {"type": "array"},
            },
            required=(
                "memory_type",
                "title",
                "summary",
                "source_refs",
                "confirm_execute",
                "approval_contract_hash",
                "approval_contract",
            ),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "execute_version": {"type": "string"},
                "project_id": {"type": "string"},
                "target_type": {"type": "string"},
                "action": {"type": "string"},
                "candidate": {"type": "object"},
                "candidate_count": {"type": "integer"},
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
        target_type="agent_knowledge_base_candidate",
        internal=True,
        sort_key=12,
        availability_checks=("project_exists",),
    ),
)
