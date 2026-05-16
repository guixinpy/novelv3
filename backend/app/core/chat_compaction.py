from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models import DialogMessage
from app.prompting.assembler import PromptAssembler
from app.schemas import ProjectDiagnosisOut

MAX_COMPACTION_DIALOG_LINES_CHARS = 12_000
COMPACTION_MESSAGE_CONTENT_QUERY_CHARS = 2_000


@dataclass(frozen=True)
class CompactionSummary:
    title: str
    summary_text: str
    compacted_count: int


def select_compactable_plain_messages(db: Session, dialog_id: str) -> list[Any]:
    last_summary = (
        db.query(DialogMessage.created_at, DialogMessage.id)
        .filter(
            DialogMessage.dialog_id == dialog_id,
            DialogMessage.message_type == "summary",
        )
        .order_by(DialogMessage.created_at.desc(), DialogMessage.id.desc())
        .first()
    )
    query = db.query(
        DialogMessage.id,
        DialogMessage.role,
        DialogMessage.message_type,
        func.substr(DialogMessage.content, 1, COMPACTION_MESSAGE_CONTENT_QUERY_CHARS).label("content"),
        DialogMessage.action_result,
    ).filter(
        DialogMessage.dialog_id == dialog_id,
        DialogMessage.message_type == "plain",
    )
    if last_summary is not None:
        query = query.filter(
            or_(
                DialogMessage.created_at > last_summary.created_at,
                and_(
                    DialogMessage.created_at == last_summary.created_at,
                    DialogMessage.id > last_summary.id,
                ),
            )
        )
    return query.order_by(DialogMessage.created_at.asc(), DialogMessage.id.asc()).all()


async def build_compaction_summary(
    messages: list[DialogMessage],
    *,
    ai_service,
    model: str,
    project_name: str,
    diagnosis: ProjectDiagnosisOut,
) -> CompactionSummary:
    compacted_count = len(messages)
    fallback_summary = _build_deterministic_fallback(messages, diagnosis)
    summary_text = fallback_summary

    try:
        prompt = PromptAssembler().build(
            "dialog.compact",
            {
                "project_name": project_name or "未命名项目",
                "dialog_lines": _build_dialog_lines(messages),
            },
        ).content
        result = await ai_service.complete(
            [{"role": "system", "content": prompt}],
            temperature=0.2,
            max_tokens=450,
            model=model or "deepseek-chat",
        )
        generated = (getattr(result, "content", "") or "").strip()
        if generated:
            summary_text = generated
    except Exception:
        summary_text = fallback_summary

    return CompactionSummary(
        title=f"对话摘要（{compacted_count}条）",
        summary_text=summary_text,
        compacted_count=compacted_count,
    )


def _build_dialog_lines(messages: list[DialogMessage]) -> str:
    lines: list[str] = []
    for index, message in enumerate(messages, start=1):
        text = _normalize_text(message.content)
        if text:
            lines.append(f"{index}. [{message.role}] {text}")
    if not lines:
        return "（无可用对话内容）"
    full_text = "\n".join(lines)
    if len(full_text) <= MAX_COMPACTION_DIALOG_LINES_CHARS:
        return full_text
    return _bounded_recent_dialog_lines(lines)


def _bounded_recent_dialog_lines(lines: list[str]) -> str:
    selected_reversed: list[str] = []
    selected_chars = 0
    for line in reversed(lines):
        selected_count = len(selected_reversed) + 1
        omitted_count = len(lines) - selected_count
        notice = _omission_notice(omitted_count, selected_count)
        separator_chars = len(selected_reversed)
        candidate_chars = selected_chars + len(line) + separator_chars + len(notice) + 1
        if candidate_chars <= MAX_COMPACTION_DIALOG_LINES_CHARS:
            selected_reversed.append(line)
            selected_chars += len(line)
            continue
        if not selected_reversed:
            budget = max(0, MAX_COMPACTION_DIALOG_LINES_CHARS - len(notice) - 1)
            selected_reversed.append(_truncate_text(line, budget))
        break

    selected = list(reversed(selected_reversed))
    omitted_count = len(lines) - len(selected)
    notice = _omission_notice(omitted_count, len(selected))
    result = "\n".join([notice, *selected])
    while len(result) > MAX_COMPACTION_DIALOG_LINES_CHARS and len(selected) > 1:
        selected = selected[1:]
        omitted_count = len(lines) - len(selected)
        notice = _omission_notice(omitted_count, len(selected))
        result = "\n".join([notice, *selected])
    if len(result) > MAX_COMPACTION_DIALOG_LINES_CHARS:
        budget = max(0, MAX_COMPACTION_DIALOG_LINES_CHARS - len(notice) - 1)
        result = "\n".join([notice, _truncate_text(selected[-1], budget)])
    return result


def _omission_notice(omitted_count: int, kept_count: int) -> str:
    return f"（已省略 {omitted_count} 条较早对话；以下保留最近 {kept_count} 条用于压缩。）"


def _truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return f"{text[:limit - 3].rstrip()}..."

def _build_deterministic_fallback(
    messages: list[DialogMessage],
    diagnosis: ProjectDiagnosisOut,
) -> str:
    latest_user_goal = next(
        (_normalize_text(message.content) for message in reversed(messages) if message.role == "user" and _normalize_text(message.content)),
        "未提取到明确目标",
    )
    latest_action = "未记录到明确动作"
    for message in reversed(messages):
        action_result = getattr(message, "action_result", None) or {}
        action_type = str(action_result.get("type") or "").strip()
        action_status = str(action_result.get("status") or "").strip()
        if action_type or action_status:
            latest_action = f"{action_type or 'unknown'} / {action_status or 'unknown'}"
            break

    latest_command_args = "无"
    for message in reversed(messages):
        text = _normalize_text(getattr(message, "content", None))
        if "附加要求：" in text:
            latest_command_args = text.split("附加要求：", 1)[1].strip("。 ")
            break

    missing_labels = "、".join(_item_label(item) for item in diagnosis.missing_items) if diagnosis.missing_items else "无"
    completed_labels = "、".join(_item_label(item) for item in diagnosis.completed_items) if diagnosis.completed_items else "无"
    next_step = diagnosis.suggested_next_step or "无"

    return "\n".join([
        f"用户目标：{latest_user_goal}",
        f"最近动作：{latest_action}",
        f"项目诊断：已完成 {completed_labels}；缺失 {missing_labels}；建议下一步 {next_step}",
        f"最近补充要求：{latest_command_args}",
    ])


def _item_label(name: str) -> str:
    return {
        "setup": "设定",
        "storyline": "故事线",
        "outline": "大纲",
        "content": "正文",
    }.get(name, name)


def _normalize_text(text: str | None) -> str:
    raw = (text or "").replace("\n", " ").strip()
    return " ".join(raw.split())
