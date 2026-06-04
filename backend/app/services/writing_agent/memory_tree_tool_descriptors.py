from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


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
        name="record_agent_memory_tree_summaries",
        module="writing_agent",
        category="longform_memory",
        description="生成并持久化 Memory Tree 的卷级和章级摘要节点，写入 LongformMemory 供后续浏览和检索使用。",
        input_schema=object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "summary": {"type": "object"},
                "nodes": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_memory_tree_summary",
        internal=True,
        non_blocking_report=False,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
)
