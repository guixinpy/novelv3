from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.outline_lookup import find_outline_chapter
from app.models import ChapterContent, Outline, Project, ProjectProfileVersion, Setup, Storyline
from app.services.writing_agent.agent_tool_surface_policy import (
    build_agent_profile_tool_projection,
    build_agent_tool_surface_policy_projection,
)
from app.services.writing_agent.agent_core_tool_descriptors import AGENT_CORE_TOOL_DESCRIPTORS
from app.services.writing_agent.agent_generation_tool_descriptors import AGENT_GENERATION_TOOL_DESCRIPTORS
from app.services.writing_agent.agent_memory_trace_tool_descriptors import AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS
from app.services.writing_agent.agent_task_queue_tool_descriptors import AGENT_TASK_QUEUE_TOOL_DESCRIPTORS
from app.services.writing_agent.hermes_action_tool_descriptors import HERMES_ACTION_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.knowledge_base_tool_descriptors import KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.longform_tool_descriptors import LONGFORM_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.outline_generation_tool_descriptors import OUTLINE_GENERATION_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.review_revision_tool_descriptors import REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.setup_generation_tool_descriptors import SETUP_GENERATION_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.storyline_generation_tool_descriptors import STORYLINE_GENERATION_AGENT_TOOL_DESCRIPTORS
from app.services.writing_agent.world_model_tool_descriptors import WORLD_MODEL_AGENT_TOOL_DESCRIPTORS


_TOOL_DESCRIPTORS: tuple[Any, ...] = (
    *AGENT_CORE_TOOL_DESCRIPTORS,
    *LONGFORM_AGENT_TOOL_DESCRIPTORS,
    *AGENT_TASK_QUEUE_TOOL_DESCRIPTORS,
    *KNOWLEDGE_BASE_AGENT_TOOL_DESCRIPTORS,
    *AGENT_MEMORY_TRACE_TOOL_DESCRIPTORS,
    *HERMES_ACTION_AGENT_TOOL_DESCRIPTORS,
    *SETUP_GENERATION_AGENT_TOOL_DESCRIPTORS,
    *STORYLINE_GENERATION_AGENT_TOOL_DESCRIPTORS,
    *OUTLINE_GENERATION_AGENT_TOOL_DESCRIPTORS,
    *AGENT_GENERATION_TOOL_DESCRIPTORS,
    *WORLD_MODEL_AGENT_TOOL_DESCRIPTORS,
    *REVIEW_REVISION_AGENT_TOOL_DESCRIPTORS,
)

_TOOLS_BY_NAME = {descriptor.name: descriptor for descriptor in _TOOL_DESCRIPTORS}


def list_agent_tool_descriptors() -> tuple[Any, ...]:
    return tuple(sorted(_TOOL_DESCRIPTORS, key=lambda descriptor: (descriptor.sort_key, descriptor.name)))


def get_agent_tool_descriptor(name: str) -> Any | None:
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


def build_agent_tool_plan(
    db: Session,
    project_id: str,
    chapter_index: int | None = None,
    *,
    adapter_metadata_by_name: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    state = _load_project_tool_state(db, project_id, chapter_index)
    adapter_metadata_by_name = adapter_metadata_by_name or {}
    visible_tools: list[dict[str, Any]] = []
    hidden_tools: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []

    for descriptor in list_agent_tool_descriptors():
        tool_diagnostics = _diagnostics_for_descriptor(descriptor, state)
        diagnostics.extend(tool_diagnostics)
        blockers = [item for item in tool_diagnostics if item["severity"] == "blocker"]
        public_descriptor = descriptor.to_public_dict(adapter_metadata_by_name.get(descriptor.name))
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
        "tool_policy_projection": build_agent_tool_surface_policy_projection(visible_tools, hidden_tools),
        "agent_profile_tool_projection": build_agent_profile_tool_projection(visible_tools, hidden_tools),
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


def _diagnostics_for_descriptor(descriptor: Any, state: _ProjectToolState) -> list[dict[str, Any]]:
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
