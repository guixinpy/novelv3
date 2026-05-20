from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.core.outline_lookup import find_outline_chapter
from app.models import ChapterContent, Outline, Project, ProjectProfileVersion, Setup, Storyline


@dataclass(frozen=True)
class AgentToolDescriptor:
    name: str
    module: str
    category: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    target_type: str | None
    internal: bool = False
    non_blocking_report: bool = False
    sort_key: int = 100
    availability_checks: tuple[str, ...] = ()
    warning_checks: tuple[str, ...] = ()

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "module": self.module,
            "category": self.category,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "target_type": self.target_type,
            "internal": self.internal,
            "non_blocking_report": self.non_blocking_report,
        }


def _object_schema(properties: dict[str, Any] | None = None, required: tuple[str, ...] = ()) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": "object", "properties": properties or {}, "additionalProperties": True}
    if required:
        schema["required"] = list(required)
    return schema


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
        output_schema=_STATUS_OUTPUT,
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
        output_schema=_STATUS_OUTPUT,
        target_type="chapter",
        sort_key=50,
        availability_checks=("setup_exists", "outline_chapter_exists", "previous_chapter_exists"),
        warning_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="import_setup_world_model",
        module="athena_world_model",
        category="athena_world_model",
        description="将项目设定导入 Athena 世界模型，形成可审计的初始事实层。",
        input_schema=_object_schema(),
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        sort_key=60,
        availability_checks=("setup_exists",),
    ),
    AgentToolDescriptor(
        name="analyze_chapter_world_model",
        module="athena_world_model",
        category="athena_world_model",
        description="分析已生成章节，抽取世界模型候选事实和提案。",
        input_schema=_CHAPTER_PARAMS,
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        sort_key=70,
        availability_checks=("generated_chapter_exists", "world_model_profile_exists"),
    ),
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
        output_schema=_STATUS_OUTPUT,
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
        input_schema=_object_schema({"chapter_index": {"type": "integer", "minimum": 1}, "min_word_count": {"type": "integer"}}),
        output_schema=_STATUS_OUTPUT,
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
        input_schema=_object_schema({"chapter_index": {"type": "integer", "minimum": 1}, "target_max_word_count": {"type": "integer"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="revision",
        internal=True,
        sort_key=150,
        availability_checks=("generated_chapter_exists",),
    ),
    AgentToolDescriptor(
        name="review_world_model_proposals",
        module="athena_world_model",
        category="athena_world_model",
        description="查看待处理的世界模型提案和冲突摘要。",
        input_schema=_object_schema({"offset": {"type": "integer"}, "limit": {"type": "integer"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=160,
        availability_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="plan_world_model_proposal_resolution",
        module="athena_world_model",
        category="athena_world_model",
        description="为世界模型提案生成处理计划。",
        input_schema=_object_schema({"offset": {"type": "integer"}, "limit": {"type": "integer"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=170,
        availability_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="preview_world_model_proposal_resolution",
        module="athena_world_model",
        category="athena_world_model",
        description="预览世界模型提案处理决策的影响。",
        input_schema=_object_schema({"decisions": {"type": "array"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=180,
        availability_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="apply_world_model_proposal_resolution",
        module="athena_world_model",
        category="athena_world_model",
        description="在确认后应用世界模型提案处理决策。",
        input_schema=_object_schema({"decisions": {"type": "array"}, "confirm_apply": {"type": "boolean"}}),
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=190,
        availability_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="draft_world_model_proposal_resolution_decisions",
        module="athena_world_model",
        category="athena_world_model",
        description="为待处理世界模型提案草拟批量处理决策。",
        input_schema=_object_schema(
            {
                "limit": {"type": "integer"},
                "predicate_policies": {"type": "object"},
                "include_unclassified": {"type": "boolean"},
            }
        ),
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=200,
        availability_checks=("world_model_profile_exists",),
    ),
    AgentToolDescriptor(
        name="seed_continuity_anchor_proposals",
        module="athena_world_model",
        category="maintenance",
        description="为关键连续性锚点生成世界模型提案。",
        input_schema=_object_schema(),
        output_schema=_STATUS_OUTPUT,
        target_type="world_model",
        internal=True,
        non_blocking_report=True,
        sort_key=210,
        availability_checks=("world_model_profile_exists",),
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
