from typing import Any

from sqlalchemy.orm import Session

from app.core.context_injection import (
    build_athena_world_context,
    build_athena_world_context_blocks,
    build_hermes_world_context,
    build_hermes_world_context_blocks,
)
from app.core.model_call_trace import build_context_block
from app.models import DialogMessage, Project, ProjectProfileVersion
from app.prompting.assembler import PromptAssembler
from app.prompting.tracing import build_prompt_trace_metadata

CHAT_HISTORY_LIMIT = 8
PHASE_LABELS = {
    "setup": "设定阶段",
    "storyline": "故事线阶段",
    "outline": "大纲阶段",
    "content": "正文阶段",
}
STATUS_LABELS = {
    "draft": "待补全",
    "writing": "正文写作中",
    "outline_generated": "大纲已生成",
    "storyline_generated": "故事线已生成",
    "setup_approved": "设定已确认",
}


def build_dialog_history_messages(
    db: Session,
    dialog_id: str,
    limit: int = CHAT_HISTORY_LIMIT,
) -> list[dict[str, str]]:
    history = _latest_dialog_history(db, dialog_id, limit)
    messages = []
    for item in history:
        if item.role in ("user", "assistant"):
            messages.append({"role": item.role, "content": item.content})
        elif item.role == "system":
            messages.append({"role": "assistant", "content": f"[系统消息] {item.content}"})
    return messages


def build_dialog_history_block(
    db: Session,
    dialog_id: str,
    limit: int = CHAT_HISTORY_LIMIT,
) -> dict[str, Any]:
    history = _latest_dialog_history(db, dialog_id, limit)
    lines = []
    for item in history:
        if item.role in ("user", "assistant"):
            lines.append(f"{item.role}: {item.content}")
        elif item.role == "system":
            lines.append(f"assistant: [系统消息] {item.content}")

    return build_context_block(
        key="dialog.history",
        kind="dialog_history",
        title="对话历史",
        content="\n".join(lines) if lines else "当前对话暂无可用历史。",
        sources=[
            {
                "source_type": "Dialog",
                "source_id": dialog_id,
            }
        ],
    )


def build_hermes_prompt_variables(project: Project, diagnosis, world_context: str) -> dict[str, str]:
    completed_items = getattr(diagnosis, "completed_items", []) or []
    missing_items = getattr(diagnosis, "missing_items", []) or []
    return {
        "project_name": project.name or "未命名项目",
        "project_genre": project.genre or "未分类题材",
        "project_description": project.description or "暂无项目描述",
        "project_phase": _phase_label(project.current_phase),
        "project_status": _status_label(project.status),
        "current_words": str(project.current_word_count or 0),
        "target_chapters": str(project.target_chapter_count or 0),
        "target_words": str(project.target_word_count or 0),
        "completed_items": "、".join(completed_items) if completed_items else "无",
        "missing_items": "、".join(missing_items) if missing_items else "无",
        "suggested_next_step": getattr(diagnosis, "suggested_next_step", None) or "无",
        "world_context": world_context,
    }


def build_athena_prompt_variables(db: Session, project: Project, world_context: str) -> dict[str, str]:
    profile = (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project.id)
        .order_by(ProjectProfileVersion.version.desc())
        .first()
    )
    return {
        "project_name": project.name or "未命名项目",
        "project_genre": project.genre or "未分类题材",
        "project_description": project.description or "暂无项目描述",
        "project_phase": _phase_label(project.current_phase),
        "profile_version": str(profile.version) if profile else "未建立",
        "world_context": world_context,
    }


def build_dialog_call_payload(
    db: Session,
    dialog_id: str,
    project: Project,
    diagnosis,
    dialog_type: str = "hermes",
    history_limit: int = CHAT_HISTORY_LIMIT,
) -> dict[str, Any]:
    normalized_dialog_type = "athena" if dialog_type == "athena" else "hermes"
    if normalized_dialog_type == "athena":
        prompt_id = "dialog.athena"
        world_context = build_athena_world_context(db, project.id)
        context_blocks = build_athena_world_context_blocks(db, project.id)
        variables = build_athena_prompt_variables(db, project, world_context)
    else:
        prompt_id = "dialog.hermes"
        world_context = build_hermes_world_context(db, project.id)
        context_blocks = build_hermes_world_context_blocks(db, project.id)
        variables = build_hermes_prompt_variables(project, diagnosis, world_context)

    context_blocks = [
        *context_blocks,
        build_dialog_history_block(db, dialog_id, limit=history_limit),
    ]
    assembler = PromptAssembler()
    rendered_result = assembler.build(
        prompt_id,
        variables,
        context_blocks=context_blocks,
        messages=[],
    )
    messages = [
        {"role": "system", "content": rendered_result.content},
        *build_dialog_history_messages(db, dialog_id, limit=history_limit),
    ]
    build_result = assembler.build(
        prompt_id,
        variables,
        context_blocks=context_blocks,
        messages=messages,
    )
    trace_metadata = build_prompt_trace_metadata(build_result)
    trace_metadata["dialog_type"] = normalized_dialog_type
    return {
        "messages": build_result.messages,
        "context_blocks": build_result.context_blocks,
        "trace_metadata": trace_metadata,
        "rendered_prompt": build_result.content,
    }


def _latest_dialog_history(db: Session, dialog_id: str, limit: int) -> list[DialogMessage]:
    history = (
        db.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog_id)
        .order_by(DialogMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    history.reverse()
    return history


def _phase_label(phase: str | None) -> str:
    return PHASE_LABELS.get(phase or "", phase or "未开始")


def _status_label(status: str | None) -> str:
    return STATUS_LABELS.get(status or "", status or "待补全")
