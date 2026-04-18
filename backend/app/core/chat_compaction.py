from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.prompt_manager import PromptManager
from app.models import DialogMessage
from app.schemas import ProjectDiagnosisOut


@dataclass(frozen=True)
class CompactionSummary:
    title: str
    summary_text: str
    compacted_count: int


def select_compactable_plain_messages(db: Session, dialog_id: str) -> list[DialogMessage]:
    messages = (
        db.query(DialogMessage)
        .filter(DialogMessage.dialog_id == dialog_id)
        .order_by(DialogMessage.created_at.asc(), DialogMessage.id.asc())
        .all()
    )

    last_summary_index = -1
    for index, message in enumerate(messages):
        if message.message_type == "summary":
            last_summary_index = index

    return [message for message in messages[last_summary_index + 1 :] if message.message_type == "plain"]


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

    prompt = PromptManager().load(
        "compact_dialog_context",
        {
            "project_name": project_name or "未命名项目",
            "dialog_lines": _build_dialog_lines(messages),
        },
    )

    try:
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
    return "\n".join(lines) if lines else "（无可用对话内容）"

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
