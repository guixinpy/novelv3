from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.outline_lookup import find_outline_chapter
from app.models import ChapterContent, Outline, Project, ProjectProfileVersion, Setup, Storyline
from app.services.writing_agent.knowledge_base_tool_descriptors import KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.longform_tool_descriptors import LONGFORM_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor
from app.services.writing_agent.tool_descriptor_types import object_schema as _object_schema
from app.services.writing_agent.world_model_tool_descriptors import WORLD_MODEL_AGENT_TOOL_DESCRIPTORS


_STATUS_OUTPUT = _object_schema({"status": {"type": "string"}})
_CHAPTER_PARAMS = _object_schema({"chapter_index": {"type": "integer", "minimum": 1}})
_REVISION_PATCH_OUTPUT = _object_schema(
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
_CHAPTER_EXPANSION_OUTPUT = _object_schema(
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
_CHAPTER_COMPRESSION_OUTPUT = _object_schema(
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
_WINDOW_PARAMS = _object_schema(
    {
        "chapter_index": {"type": "integer", "minimum": 1},
        "start_chapter": {"type": "integer", "minimum": 1},
        "end_chapter": {"type": "integer", "minimum": 1},
        "command_args": {"type": "string"},
    }
)
_OUTLINE_WINDOW_OUTPUT = _object_schema(
    {
        "status": {"type": "string"},
        "start_chapter": {"type": "integer"},
        "end_chapter": {"type": "integer"},
        "outline_id": {"type": "string"},
        "total_chapters": {"type": "integer"},
        "added_chapter_count": {"type": "integer"},
        "merge": {"type": "object"},
        "trace_id": {"type": ["string", "null"]},
        "should_generate_next_chapter": {"type": "boolean"},
        "recommended_next_tools": {"type": "array"},
    }
)
_AGENT_PLAN_APPROVAL_CONTRACT_OUTPUT = _object_schema(
    {
        "status": {"type": "string"},
        "version": {"type": "string"},
        "project_id": {"type": ["string", "null"]},
        "plan_id": {"type": ["string", "null"]},
        "source_projection_id": {"type": ["string", "null"]},
        "write_step_count": {"type": "integer"},
        "write_steps": {"type": "array"},
        "approval": {"type": "object"},
        "trace": {"type": "object"},
    }
)
_AGENT_PLAN_APPROVAL_VERIFICATION_OUTPUT = _object_schema(
    {
        "status": {"type": "string"},
        "version": {"type": "string"},
        "reason": {"type": "string"},
        "current_contract": {"type": "object"},
        "drift": {"type": "object"},
        "recommended_next_tools": {"type": "array"},
        "trace": {"type": "object"},
    }
)
_AGENT_WRITE_GATE_COVERAGE_OUTPUT = _object_schema(
    {
        "status": {"type": "string"},
        "version": {"type": "string"},
        "summary": {"type": "object"},
        "write_tools": {"type": "array"},
        "recommended_next_targets": {"type": "array"},
        "trace": {"type": "object"},
    }
)


_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    AgentToolDescriptor(
        name="describe_agent_tools",
        module="writing_agent",
        category="preflight",
        description="返回当前项目和章节下 Agent 可见工具、隐藏工具和缺失依赖诊断。",
        input_schema=_CHAPTER_PARAMS,
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "visible_tools": {"type": "array"},
                "hidden_tools": {"type": "array"},
                "diagnostics": {"type": "array"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        sort_key=5,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="plan_writing_agent_run",
        module="writing_agent",
        category="preflight",
        description="根据高层写作意图生成可解释的 Writing Agent 工具链计划。",
        input_schema=_object_schema(
            {
                "goal": {"type": "string"},
                "chapter_index": {"type": "integer", "minimum": 1},
                "intent": {"type": "string"},
            }
        ),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "intent_class": {"type": "string"},
                "steps": {"type": "array"},
                "tools": {"type": "array"},
                "approval_contract": {"type": "object"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=6,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="plan_dialog_intent_agent_run",
        module="writing_agent",
        category="preflight",
        description="根据自然语言对话意图投影生成只读 Writing Agent 工具链计划，不直接执行工具。",
        input_schema=_object_schema(
            {
                "text": {"type": "string"},
                "dialog_state": {"type": "string"},
                "pending_action_id": {"type": "string"},
                "missing_items": {"type": "array"},
                "completed_items": {"type": "array"},
                "suggested_next_step": {"type": "string"},
            },
            required=("text",),
        ),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "intent_projection": {"type": "object"},
                "planner": {"type": "object"},
                "plan": {"type": ["object", "null"]},
                "tools": {"type": "array"},
                "approval_contract": {"type": "object"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=7,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="preview_agent_plan_approval_contract",
        module="writing_agent",
        category="preflight",
        description="为 Writing Agent 计划中的写入步骤生成只读审批契约和稳定哈希，不执行任何工具。",
        input_schema=_object_schema({"plan": {"type": "object"}}, required=("plan",)),
        output_schema=_AGENT_PLAN_APPROVAL_CONTRACT_OUTPUT,
        target_type="agent_plan_approval_contract",
        internal=True,
        non_blocking_report=True,
        sort_key=7,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="verify_agent_plan_approval_contract",
        module="writing_agent",
        category="preflight",
        description="只读校验 Writing Agent 计划审批契约哈希，报告缺失、错配或漂移，不执行任何写入工具。",
        input_schema=_object_schema(
            {
                "plan": {"type": "object"},
                "approval_contract_hash": {"type": "string"},
                "approval_contract": {"type": "object"},
            },
            required=("plan",),
        ),
        output_schema=_AGENT_PLAN_APPROVAL_VERIFICATION_OUTPUT,
        target_type="agent_plan_approval_verification",
        internal=True,
        non_blocking_report=True,
        sort_key=7,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="plan_recovery_tools",
        module="writing_agent",
        category="preflight",
        description="根据已阻塞或失败的 Writing Agent run 生成只读恢复工具链计划，不自动执行恢复。",
        input_schema=_object_schema({"run_id": {"type": "string"}}),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "source_run_id": {"type": "string"},
                "source_step": {"type": "object"},
                "recovery": {"type": "object"},
                "tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=7,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="plan_recommended_followups",
        module="writing_agent",
        category="preflight",
        description="根据指定 Writing Agent run 的运行时推荐生成只读后继工具计划。",
        input_schema=_object_schema({"run_id": {"type": "string"}}),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "source_run_id": {"type": "string"},
                "source_step": {"type": "object"},
                "recommended_followups": {"type": "object"},
                "tools": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=8,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_slash_command_route",
        module="writing_agent",
        category="preflight",
        description="返回斜杠命令到 Writing Agent 工具的只读路由投影，用于对话入口 Agent 化自查。",
        input_schema=_object_schema({"command_name": {"type": "string"}}),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "routes": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=9,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_dialog_route_projection",
        module="writing_agent",
        category="preflight",
        description="返回自然语言 intent、按钮 action 和斜杠命令到 Writing Agent 工具的统一路由投影。",
        input_schema=_object_schema({"source": {"type": "string"}}),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "routes": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_route_preference_projection",
        module="writing_agent",
        category="preflight",
        description="返回对话入口当前路由与推荐 Agent 审批工具链的只读偏好投影，不改变运行时路由。",
        input_schema=_object_schema({"source": {"type": "string"}}),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "summary": {"type": "object"},
                "routes": {"type": "array"},
                "trace": {"type": "object"},
            }
        ),
        target_type="agent_route_preference_projection",
        internal=True,
        non_blocking_report=True,
        sort_key=11,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_intent_projection",
        module="writing_agent",
        category="preflight",
        description="返回自然语言输入经 IntentRouter 规则匹配后的可解释投影报告。",
        input_schema=_object_schema(
            {
                "text": {"type": "string"},
                "missing_items": {"type": "array"},
                "completed_items": {"type": "array"},
                "suggested_next_step": {"type": "string"},
            },
            required=("text",),
        ),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "rule_id": {"type": ["string", "null"]},
                "reason": {"type": ["string", "null"]},
                "candidate": {"type": ["object", "null"]},
                "agent_route": {"type": ["object", "null"]},
                "diagnosis": {"type": "object"},
                "extracted_params": {"type": "object"},
            }
        ),
        target_type="agent_tool_plan",
        internal=True,
        non_blocking_report=True,
        sort_key=11,
        availability_checks=("project_exists",),
    ),
    *LONGFORM_AGENT_TOOL_DESCRIPTORS,
    AgentToolDescriptor(
        name="inspect_agent_job_projection",
        module="writing_agent",
        category="task_queue",
        description="只读查看后台任务队列的 Agent Job 投影，包括控制面、进度、恢复建议和关联 Agent run。",
        input_schema=_object_schema(
            {
                "task_id": {"type": "string"},
                "task_type": {"type": "string"},
                "status": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1},
                "chapter_index": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=_object_schema(
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
        input_schema=_object_schema({"chapter_index": {"type": "integer", "minimum": 1}}, required=("chapter_index",)),
        output_schema=_object_schema(
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
    AgentToolDescriptor(
        name="inspect_agent_tool_contracts",
        module="writing_agent",
        category="preflight",
        description="只读输出 Writing Agent 工具契约快照、覆盖率和迁移差距，用于持续重构模块为 Agent 工具。",
        input_schema=_object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "include_gap_details": {"type": "boolean"},
            }
        ),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "summary": {"type": "object"},
                "coverage": {"type": "object"},
                "tools": {"type": "array"},
                "gaps": {"type": "array"},
                "reference_alignment": {"type": "object"},
                "recommended_next_steps": {"type": "array"},
            }
        ),
        target_type="agent_tool_contracts",
        internal=True,
        non_blocking_report=True,
        sort_key=11,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_write_gate_coverage",
        module="writing_agent",
        category="preflight",
        description="只读输出写入工具的 Agent 计划审批门禁覆盖度，用于选择下一批执行硬化目标。",
        input_schema=_object_schema(),
        output_schema=_AGENT_WRITE_GATE_COVERAGE_OUTPUT,
        target_type="agent_write_gate_coverage",
        internal=True,
        non_blocking_report=True,
        sort_key=12,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="inspect_agent_mutation_fingerprints",
        module="writing_agent",
        category="preflight",
        description="只读计算计划写入工具的稳定 mutation fingerprint，用于恢复、审批和冲突诊断绑定具体目标。",
        input_schema=_object_schema(
            {
                "tools": {
                    "type": "array",
                    "items": _object_schema(
                        {
                            "tool_name": {"type": "string"},
                            "params": {"type": "object"},
                        }
                    ),
                },
            }
        ),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "version": {"type": "string"},
                "project_id": {"type": "string"},
                "summary": {"type": "object"},
                "fingerprints": {"type": "array"},
                "recommended_next_tools": {"type": "array"},
            }
        ),
        target_type="agent_mutation_fingerprint",
        internal=True,
        non_blocking_report=True,
        sort_key=12,
        availability_checks=("project_exists",),
    ),
    *KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS,
    AgentToolDescriptor(
        name="inspect_agent_trace_audit",
        module="writing_agent",
        category="trace",
        description="汇总 Writing Agent run、步骤、模型调用 Trace 和上下文块，帮助 Agent 解释执行链和失败原因。",
        input_schema=_object_schema(
            {
                "run_id": {"type": "string"},
                "chapter_index": {"type": "integer", "minimum": 1},
                "task_id": {"type": "string"},
                "limit": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "audit": {"type": "object"},
                "run": {"type": "object"},
                "steps": {"type": "array"},
                "traces": {"type": "array"},
                "context": {"type": "object"},
                "failure": {"type": "object"},
                "recommended_actions": {"type": "array"},
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
        input_schema=_object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "query": {"type": "string"},
                "include_context_summary": {"type": "boolean"},
            }
        ),
        output_schema=_object_schema(
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
        input_schema=_object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "query": {"type": "string"},
                "max_chars": {"type": "integer", "minimum": 500},
                "include_prompt_context": {"type": "boolean"},
            }
        ),
        output_schema=_object_schema(
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
        input_schema=_object_schema(
            {
                "limit": {"type": "integer", "minimum": 1},
                "repair_limit": {"type": "integer", "minimum": 1},
            }
        ),
        output_schema=_object_schema(
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
    AgentToolDescriptor(
        name="preflight_writing",
        module="writing_agent",
        category="preflight",
        description="检查指定章节生成前的设定、大纲、前文、世界模型、检索和字数策略状态。",
        input_schema=_CHAPTER_PARAMS,
        output_schema=_STATUS_OUTPUT,
        target_type="preflight",
        internal=True,
        sort_key=10,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="generate_setup",
        module="hermes",
        category="generation",
        description="根据项目意图生成小说基础设定。",
        input_schema=_object_schema({"command_args": {"type": "string"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="setup",
        sort_key=20,
        availability_checks=("project_exists",),
    ),
    AgentToolDescriptor(
        name="generate_storyline",
        module="hermes",
        category="generation",
        description="基于设定生成叙事主线、支线和伏笔结构。",
        input_schema=_object_schema({"command_args": {"type": "string"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="storyline",
        sort_key=30,
        availability_checks=("setup_exists",),
    ),
    AgentToolDescriptor(
        name="generate_outline",
        module="hermes",
        category="generation",
        description="基于设定和故事线生成章节大纲。",
        input_schema=_object_schema({"command_args": {"type": "string"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="outline",
        sort_key=40,
        availability_checks=("setup_exists", "storyline_exists"),
    ),
    AgentToolDescriptor(
        name="expand_outline_window",
        module="athena_narrative",
        category="generation",
        description="补齐或扩展指定章节窗口的大纲，并注入 Agent 长篇约束。",
        input_schema=_WINDOW_PARAMS,
        output_schema=_OUTLINE_WINDOW_OUTPUT,
        target_type="outline",
        internal=True,
        sort_key=45,
        availability_checks=("setup_exists", "storyline_exists", "outline_exists"),
    ),
    AgentToolDescriptor(
        name="generate_chapter",
        module="hermes",
        category="generation",
        description="生成指定章节正文，并融合前文状态、检索、Athena 和 Agent 约束。",
        input_schema=_CHAPTER_PARAMS,
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "chapter_index": {"type": "integer"},
                "trace_id": {"type": "string"},
                "athena_analysis": {"type": "object"},
                "agent_continuity_feedback": {"type": "object"},
                "agent_generation_feedback": {"type": "object"},
                "chapter_length_decision": {"type": "object"},
                "world_model_proposal_diagnostic": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
            }
        ),
        target_type="chapter",
        sort_key=50,
        availability_checks=("setup_exists", "outline_chapter_exists", "previous_chapter_exists"),
        warning_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="prepare_generate_chapter_execution",
        module="writing_agent",
        category="generation",
        description="为直接章节生成构建 Agent 计划审批契约，不执行正文生成。",
        input_schema=_object_schema({"chapter_index": {"type": "integer", "minimum": 1}}, required=("chapter_index",)),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "prepare_version": {"type": "string"},
                "chapter_index": {"type": "integer"},
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
        target_type="chapter_generation_approval",
        internal=True,
        non_blocking_report=True,
        sort_key=51,
        availability_checks=("project_exists", "outline_chapter_exists", "previous_chapter_exists"),
        warning_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="execute_generate_chapter_with_approval",
        module="writing_agent",
        category="generation",
        description="在确认 Agent 计划审批契约后执行指定章节正文生成。",
        input_schema=_object_schema(
            {
                "chapter_index": {"type": "integer", "minimum": 1},
                "command_args": {"type": "string"},
                "confirm_execute": {"type": "boolean"},
                "approval_contract_hash": {"type": "string"},
                "approval_contract": {"type": "object"},
            },
            required=("chapter_index", "confirm_execute", "approval_contract_hash", "approval_contract"),
        ),
        output_schema=_object_schema(
            {
                "status": {"type": "string"},
                "execute_version": {"type": "string"},
                "chapter_index": {"type": "integer"},
                "trace_id": {"type": "string"},
                "agent_plan_approval_verification": {"type": "object"},
                "execution_resource_binding": {"type": "object"},
                "evidence": {"type": "object"},
                "recommended_next_tools": {"type": "array"},
            }
        ),
        target_type="chapter",
        internal=True,
        sort_key=52,
        availability_checks=("project_exists", "outline_chapter_exists", "previous_chapter_exists"),
        warning_checks=("world_model_profile_exists",),
    ),
    *WORLD_MODEL_AGENT_TOOL_DESCRIPTORS,
    AgentToolDescriptor(
        name="backfill_outline_gaps",
        module="athena_narrative",
        category="maintenance",
        description="根据已生成章节回填缺失的历史章节大纲。",
        input_schema=_object_schema({"before_chapter": {"type": "integer", "minimum": 1}}),
        output_schema=_STATUS_OUTPUT,
        target_type="outline",
        internal=True,
        sort_key=80,
        availability_checks=("outline_exists",),
    ),
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
        input_schema=_object_schema({"chapter_index": {"type": "integer", "minimum": 1}, "lookback": {"type": "integer"}}),
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
        input_schema=_object_schema({"chapter_index": {"type": "integer", "minimum": 1}, "revision_id": {"type": "string"}}),
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
        input_schema=_object_schema(
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
        input_schema=_object_schema(
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

_TOOLS_BY_NAME = {descriptor.name: descriptor for descriptor in _TOOL_DESCRIPTORS}


def list_agent_tool_descriptors() -> tuple[AgentToolDescriptor, ...]:
    return tuple(sorted(_TOOL_DESCRIPTORS, key=lambda descriptor: (descriptor.sort_key, descriptor.name)))


def get_agent_tool_descriptor(name: str) -> AgentToolDescriptor | None:
    return _TOOLS_BY_NAME.get(name)


def allowed_tool_names() -> set[str]:
    return set(_TOOLS_BY_NAME)


def internal_tool_names() -> set[str]:
    return {descriptor.name for descriptor in _TOOL_DESCRIPTORS if descriptor.internal}


def non_blocking_report_tool_names() -> set[str]:
    return {descriptor.name for descriptor in _TOOL_DESCRIPTORS if descriptor.non_blocking_report}


def target_type_for_tool(name: str) -> str | None:
    descriptor = get_agent_tool_descriptor(name)
    return descriptor.target_type if descriptor else None


def build_agent_tool_plan(db: Session, project_id: str, chapter_index: int | None = None) -> dict[str, Any]:
    state = _load_project_tool_state(db, project_id, chapter_index)
    visible_tools: list[dict[str, Any]] = []
    hidden_tools: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    for descriptor in list_agent_tool_descriptors():
        tool_diagnostics = _diagnostics_for_descriptor(descriptor, state)
        diagnostics.extend(tool_diagnostics)
        blockers = [item for item in tool_diagnostics if item["severity"] == "blocker"]
        public_descriptor = descriptor.to_public_dict()
        if blockers:
            hidden_tools.append({**public_descriptor, "diagnostics": tool_diagnostics})
        else:
            visible_tools.append({**public_descriptor, "diagnostics": tool_diagnostics})

    return {
        "status": "completed",
        "project_id": project_id,
        "chapter_index": chapter_index,
        "visible_tools": visible_tools,
        "hidden_tools": hidden_tools,
        "diagnostics": diagnostics,
        "toolsets": _group_visible_tools_by_category(visible_tools),
    }


def _group_visible_tools_by_category(tools: list[dict[str, Any]]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for tool in tools:
        grouped.setdefault(str(tool["category"]), []).append(str(tool["name"]))
    return grouped


@dataclass(frozen=True)
class _ProjectToolState:
    project_exists: bool
    setup_exists: bool
    storyline_exists: bool
    outline_exists: bool
    outline_chapter_exists: bool
    previous_chapter_exists: bool
    generated_chapter_exists: bool
    world_model_profile_exists: bool
    chapter_index: int | None


def _load_project_tool_state(db: Session, project_id: str, chapter_index: int | None) -> _ProjectToolState:
    project_exists = db.query(Project.id).filter(Project.id == project_id).first() is not None
    setup_exists = db.query(Setup.id).filter(Setup.project_id == project_id).first() is not None
    storyline_exists = db.query(Storyline.id).filter(Storyline.project_id == project_id).first() is not None
    outline_exists = db.query(Outline.id).filter(Outline.project_id == project_id).first() is not None
    outline_chapter_exists = bool(chapter_index and find_outline_chapter(db, project_id, chapter_index))
    previous_chapter_exists = _previous_chapter_exists(db, project_id, chapter_index)
    generated_chapter_exists = _generated_chapter_exists(db, project_id, chapter_index)
    world_model_profile_exists = (
        db.query(ProjectProfileVersion.id).filter(ProjectProfileVersion.project_id == project_id).first() is not None
    )
    return _ProjectToolState(
        project_exists=project_exists,
        setup_exists=setup_exists,
        storyline_exists=storyline_exists,
        outline_exists=outline_exists,
        outline_chapter_exists=outline_chapter_exists,
        previous_chapter_exists=previous_chapter_exists,
        generated_chapter_exists=generated_chapter_exists,
        world_model_profile_exists=world_model_profile_exists,
        chapter_index=chapter_index,
    )


def _previous_chapter_exists(db: Session, project_id: str, chapter_index: int | None) -> bool:
    if chapter_index is None or chapter_index <= 1:
        return True
    return (
        db.query(ChapterContent.id)
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index - 1)
        .first()
        is not None
    )


def _generated_chapter_exists(db: Session, project_id: str, chapter_index: int | None) -> bool:
    if chapter_index is None:
        return False
    return (
        db.query(ChapterContent.id)
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index)
        .first()
        is not None
    )


def _diagnostics_for_descriptor(descriptor: AgentToolDescriptor, state: _ProjectToolState) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    for check_name in descriptor.availability_checks:
        diagnostic = _diagnostic_for_check(descriptor.name, check_name, state, severity="blocker")
        if diagnostic:
            diagnostics.append(diagnostic)
    for check_name in descriptor.warning_checks:
        diagnostic = _diagnostic_for_check(descriptor.name, check_name, state, severity="warning")
        if diagnostic:
            diagnostics.append(diagnostic)
    return diagnostics


def _diagnostic_for_check(
    tool_name: str,
    check_name: str,
    state: _ProjectToolState,
    *,
    severity: str,
) -> dict[str, Any] | None:
    if check_name == "project_exists" and not state.project_exists:
        return _diagnostic(tool_name, "missing_project", severity, "项目不存在。")
    if check_name == "setup_exists" and not state.setup_exists:
        return _diagnostic(tool_name, "missing_setup", severity, "项目缺少已生成设定。")
    if check_name == "storyline_exists" and not state.storyline_exists:
        return _diagnostic(tool_name, "missing_storyline", severity, "项目缺少已生成故事线。")
    if check_name == "outline_exists" and not state.outline_exists:
        return _diagnostic(tool_name, "missing_outline", severity, "项目缺少已生成章节大纲。")
    if check_name == "outline_chapter_exists":
        if state.chapter_index is None:
            return _diagnostic(tool_name, "missing_chapter_index", severity, "工具需要指定章节序号。")
        if not state.outline_chapter_exists:
            return _diagnostic(tool_name, "missing_outline_chapter", severity, f"第{state.chapter_index}章缺少章节大纲。")
    if check_name == "previous_chapter_exists":
        if state.chapter_index is None:
            return _diagnostic(tool_name, "missing_chapter_index", severity, "工具需要指定章节序号。")
        if not state.previous_chapter_exists:
            return _diagnostic(tool_name, "missing_previous_chapter", severity, f"第{state.chapter_index - 1}章尚未生成。")
    if check_name == "generated_chapter_exists":
        if state.chapter_index is None:
            return _diagnostic(tool_name, "missing_chapter_index", severity, "工具需要指定章节序号。")
        if not state.generated_chapter_exists:
            return _diagnostic(tool_name, "missing_generated_chapter", severity, f"第{state.chapter_index}章尚未生成。")
    if check_name == "world_model_profile_exists" and not state.world_model_profile_exists:
        return _diagnostic(tool_name, "missing_world_model_profile", severity, "项目尚未导入 Athena 世界模型 profile。")
    return None


def _diagnostic(tool_name: str, code: str, severity: str, message: str) -> dict[str, Any]:
    return {"tool_name": tool_name, "code": code, "severity": severity, "message": message}
