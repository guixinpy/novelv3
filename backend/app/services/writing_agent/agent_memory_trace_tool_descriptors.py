from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


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
        name="repair_longform_maintenance",
        module="athena_longform",
        category="maintenance",
        description="修复长篇记忆和检索索引缺口，使后续章节生成可获得稳定上下文。",
        input_schema=object_schema(
            {
                "limit": {"type": "integer", "minimum": 1},
                "repair_limit": {"type": "integer", "minimum": 1},
            }
        ),
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
)
