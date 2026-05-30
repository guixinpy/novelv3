from __future__ import annotations

from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor, object_schema


LONGFORM_AGENT_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="plan_longform_chapter_batch",
        module="writing_agent",
        category="task_queue",
        description="基于项目状态和可选 continuation state 生成只读长篇章节批次 DAG 计划，不直接入队或执行。",
        input_schema=object_schema(
            {
                "source_run_id": {"type": "string"},
                "start_chapter": {"type": "integer", "minimum": 1},
                "batch_size": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "batch": {"type": "object"},
                "dag": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
                "source_continuation_state": {"type": "object"},
            }
        ),
        target_type="longform_batch_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="enqueue_longform_chapter_batch",
        module="writing_agent",
        category="task_queue",
        description="为长篇章节批次入队构建审批重定向，直接调用不写入后台任务队列。",
        input_schema=object_schema(
            {
                "source_run_id": {"type": "string"},
                "start_chapter": {"type": "integer", "minimum": 1},
                "batch_size": {"type": "integer", "minimum": 1},
                "confirm_enqueue": {"type": "boolean"},
                "plan_hash": {"type": "string"},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "plan_hash": {"type": "string"},
                "batch": {"type": "object"},
                "dag": {"type": "object"},
                "task": {"type": "object"},
                "queue_policy": {"type": "object"},
            }
        ),
        target_type="background_task",
        internal=True,
        sort_key=9,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="prepare_enqueue_longform_chapter_batch",
        module="writing_agent",
        category="task_queue",
        description="为长篇章节批次入队构建 Agent 计划审批契约，不写入后台任务队列。",
        input_schema=object_schema(
            {
                "source_run_id": {"type": "string"},
                "start_chapter": {"type": "integer", "minimum": 1},
                "batch_size": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "prepare_version": {"type": "string"},
                "project_id": {"type": "string"},
                "plan_hash": {"type": "string"},
                "enqueue_preview": {"type": "object"},
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
        target_type="background_task_enqueue_approval",
        internal=True,
        non_blocking_report=True,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="execute_enqueue_longform_chapter_batch_with_approval",
        module="writing_agent",
        category="task_queue",
        description="在确认 Agent 计划审批契约后将长篇章节批次计划写入后台任务队列。",
        input_schema=object_schema(
            {
                "source_run_id": {"type": "string"},
                "start_chapter": {"type": "integer", "minimum": 1},
                "batch_size": {"type": "integer", "minimum": 1},
                "plan_hash": {"type": "string"},
                "confirm_execute": {"type": "boolean"},
                "approval_contract_hash": {"type": "string"},
                "approval_contract": {"type": "object"},
            },
            required=("plan_hash", "confirm_execute", "approval_contract_hash", "approval_contract"),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "plan_hash": {"type": "string"},
                "batch": {"type": "object"},
                "dag": {"type": "object"},
                "task": {"type": "object"},
                "queue_policy": {"type": "object"},
                "agent_plan_approval_verification": {"type": "object"},
                "execution_resource_binding": {"type": "object"},
                "side_effects": {"type": "object"},
            }
        ),
        target_type="background_task_enqueue",
        internal=True,
        sort_key=11,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_longform_chapter_batch",
        module="writing_agent",
        category="task_queue",
        description="只读查看已物化的长篇章节批次后台任务、章节范围、计划哈希和恢复状态。",
        input_schema=object_schema(
            {
                "task_id": {"type": "string"},
                "plan_hash": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "summary": {"type": "object"},
                "tasks": {"type": "array"},
                "selected_task": {"type": "object"},
            }
        ),
        target_type="background_task",
        internal=True,
        non_blocking_report=True,
        sort_key=12,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="execute_longform_chapter_batch_preflight",
        module="writing_agent",
        category="task_queue",
        description="对已物化的长篇章节批次执行安全预检并写入断点，停止在正文生成前。",
        input_schema=object_schema(
            {
                "task_id": {"type": "string"},
                "max_chapters": {"type": "integer", "minimum": 1},
                "confirm_checkpoint": {"type": "boolean"},
            },
            required=("task_id",),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "task": {"type": "object"},
                "canonical_execution_plan": {"type": "object"},
                "checkpoint": {"type": "object"},
                "side_effects": {"type": "object"},
            }
        ),
        target_type="background_task",
        internal=True,
        sort_key=13,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="prepare_longform_chapter_batch_execution",
        module="writing_agent",
        category="task_queue",
        description="将已通过预检的长篇章节批次固化为可审批的执行尝试清单，不启动真实生成。",
        input_schema=object_schema(
            {
                "task_id": {"type": "string"},
                "confirm_prepare": {"type": "boolean"},
            },
            required=("task_id",),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "task": {"type": "object"},
                "attempt_manifest": {"type": "object"},
                "approval_contract": {"type": "object"},
                "side_effects": {"type": "object"},
            }
        ),
        target_type="background_task",
        internal=True,
        sort_key=14,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="execute_longform_chapter_batch",
        module="writing_agent",
        category="task_queue",
        description="消费已审批的长篇批次执行契约，受控生成单章并写入执行证据。",
        input_schema=object_schema(
            {
                "task_id": {"type": "string"},
                "confirm_execute": {"type": "boolean"},
                "attempt_manifest_hash": {"type": "string"},
                "approval_contract_hash": {"type": "string"},
            },
            required=("task_id", "confirm_execute", "attempt_manifest_hash", "approval_contract_hash"),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "task": {"type": "object"},
                "chapter_index": {"type": "integer"},
                "generation": {"type": "object"},
                "execution_checkpoint": {"type": "object"},
                "agent_plan_approval_verification": {"type": "object"},
                "execution_resource_binding": {"type": "object"},
                "side_effects": {"type": "object"},
            }
        ),
        target_type="background_task",
        internal=True,
        sort_key=15,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="review_longform_chapter_batch_execution",
        module="writing_agent",
        category="task_queue",
        description="审查已执行的长篇批次单章，写入质量、连续性和世界模型分析证据。",
        input_schema=object_schema(
            {
                "task_id": {"type": "string"},
                "lookback": {"type": "integer", "minimum": 1},
                "confirm_review": {"type": "boolean"},
            },
            required=("task_id",),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "task": {"type": "object"},
                "chapter_index": {"type": "integer"},
                "review_gate": {"type": "object"},
                "reviews": {"type": "object"},
                "side_effects": {"type": "object"},
            }
        ),
        target_type="background_task",
        internal=True,
        sort_key=16,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="route_longform_chapter_batch_after_review",
        module="writing_agent",
        category="task_queue",
        description="根据长篇批次生成后审查结果，路由到修订恢复或下一章批次预览。",
        input_schema=object_schema(
            {
                "task_id": {"type": "string"},
                "expected_post_generation_review_hash": {"type": "string"},
                "next_batch_size": {"type": "integer", "minimum": 1},
            },
            required=("task_id",),
        ),
        output_schema=object_schema(
            {
                "status": {"type": "string"},
                "task": {"type": "object"},
                "chapter_index": {"type": "integer"},
                "route_decision": {"type": "object"},
                "recovery_plan": {"type": "object"},
                "next_batch_plan": {"type": "object"},
            }
        ),
        target_type="background_task",
        internal=True,
        sort_key=17,
        availability_checks=("project_exists",),
    ),
)
