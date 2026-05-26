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
                "chapter_index": {"type": "integer", "minimum": 1},
                "query": {"type": "string"},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "levels": {"type": "array"},
                "filters": {"type": "object"},
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
)
