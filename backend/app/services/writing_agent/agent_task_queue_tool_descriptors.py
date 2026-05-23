from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


AGENT_TASK_QUEUE_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="inspect_agent_job_projection",
        module="writing_agent",
        category="task_queue",
        description="只读查看后台任务队列的 Agent Job 投影，包括控制面、进度、恢复建议和关联 Agent run。",
        input_schema=object_schema(
            {
                "task_id": {"type": "string"},
                "task_type": {"type": "string"},
                "status": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1},
                "chapter_index": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "summary": {"type": "object"},
                "queue": {"type": "object"},
                "tasks": {"type": "array"},
                "selected_task": {"type": "object"},
                "chapter_reservation": {"type": ["object", "null"]},
                "recommended_tools": {"type": "array"},
            }
        ),
        target_type="agent_job_projection",
        internal=True,
        non_blocking_report=True,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="plan_chapter_conflict_recovery",
        module="writing_agent",
        category="task_queue",
        description="根据目标章节占用投影生成只读冲突恢复工具计划，不直接取消或重排任务。",
        input_schema=object_schema({"chapter_index": {"type": "integer", "minimum": 1}}, required=("chapter_index",)),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "chapter_index": {"type": "integer"},
                "conflict": {"type": "object"},
                "recovery": {"type": "object"},
                "tools": {"type": "array"},
                "recovery_options": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
)
