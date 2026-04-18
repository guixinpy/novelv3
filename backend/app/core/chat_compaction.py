from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.prompt_manager import PromptManager
from app.models import DialogMessage


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
) -> CompactionSummary:
    compacted_count = len(messages)
    fallback_summary = _build_deterministic_fallback(messages)
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


def _build_deterministic_fallback(messages: list[DialogMessage]) -> str:
    snippets: list[str] = []
    for message in messages:
        text = _normalize_text(message.content)
        if text:
            snippets.append(f"{message.role}:{text[:80]}")
        if len(snippets) >= 4:
            break

    if not snippets:
        return "本轮可压缩消息为空。"

    return "；".join(snippets)


def _normalize_text(text: str | None) -> str:
    raw = (text or "").replace("\n", " ").strip()
    return " ".join(raw.split())
