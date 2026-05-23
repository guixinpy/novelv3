from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.outline_lookup import find_outline_chapter
from app.models import ChapterContent, Outline, Project, ProjectProfileVersion, Setup, Storyline
from app.services.writing_agent.agent_core_tool_descriptors import AGENT_CORE_TOOL_DESCRIPTORS
from app.services.writing_agent.agent_memory_trace_tool_descriptors import AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS
from app.services.writing_agent.knowledge_base_tool_descriptors import KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.longform_tool_descriptors import LONGFORM_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.review_revision_tool_descriptors import REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.tool_descriptor_types import AgentToolDescriptor
from app.services.writing_agent.tool_descriptor_types import object_schema as _object_schema
from app.services.writing_agent.world_model_tool_descriptors import WORLD_MODEL_AGENT_TOOL_DESCRIPTORS


_STATUS_OUTPUT = _object_schema({"status": {"type": "string"}})
_CHAPTER_PARAMS = _object_schema({"chapter_index": {"type": "integer", "minimum": 1}})
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


_TOOL_DESCRIPTORS: tuple[AgentToolDescriptor, ...] = (
    *AGENT_CORE_TOOL_DESCRIPTORS,
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
    *KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS,
    *AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS,
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
    *REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS,
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
