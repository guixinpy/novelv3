from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


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
            }
        ),
        target_type="agent_knowledge_base_route",
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
        input_schema=object_schema(
            {
                "memory_type": {"type": "string"},
                "title": {"type": "string"},
                "summary": {"type": "string"},
                "source_refs": {"type": "array"},
                "confidence": {"type": "number"},
                "status": {"type": "string"},
                "tags": {"type": "array"},
            },
            required=("memory_type", "title", "summary", "source_refs"),
        ),
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
)
