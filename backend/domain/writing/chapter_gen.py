"""章节生成（arch-refactor 最小闭环版）。

组装最小上下文（大纲章节 + 上一章摘要 + 项目快照）→ provider.complete → 章节文本。
完整上下文组装（检索/记忆/风格块）在阶段 3 迁入时补全。

内联提示词风格（生成统一 v2 的延续）：提示词与领域逻辑同处，不经旧 prompting 管线。
"""
from __future__ import annotations

from core.providers.base import Provider

# 章节生成提示词（内联，v2 风格）
_CHAPTER_SYSTEM_PROMPT = """你是一位擅长长篇网络小说的资深作者。你的任务是撰写小说章节正文。

写作要求：
- 只输出章节正文，不要输出章题、不要使用 markdown 标记（**、# 等）
- 使用全角标点（，。！？：“”），不使用半角标点
- 对话使用「“”」全角引号且必须成对
- 不得出现「第X章」章题行
- 情节要有推进，章末留下悬念或信息增量"""


def build_chapter_prompt(
    *,
    project_snapshot: str,
    outline_chapter: str,
    prev_chapter_summary: str,
    chapter_index: int,
    word_target: int,
    extra_feedback: str = "",
) -> str:
    """组装章节生成用户消息（最小闭环上下文）。"""
    parts = [
        f"【当前任务】撰写第 {chapter_index} 章，目标字数约 {word_target} 字。",
        "",
        "【项目设定】",
        project_snapshot[:4000],
        "",
        "【本章大纲】",
        outline_chapter[:2000] or "（无大纲摘要，请根据设定自然推进剧情）",
    ]
    if prev_chapter_summary:
        parts += ["", "【上一章摘要】", prev_chapter_summary[:1500]]
    if extra_feedback:
        parts += ["", "【额外要求】", extra_feedback[:1500]]
    parts += ["", "请直接开始撰写本章正文。"]
    return "\n".join(parts)


async def generate_chapter(
    provider: Provider,
    *,
    project_snapshot: str,
    outline_chapter: str,
    prev_chapter_summary: str,
    chapter_index: int,
    word_target: int = 2000,
    extra_feedback: str = "",
    temperature: float | None = None,
) -> str:
    """生成章节正文（返回纯文本）。"""
    prompt = build_chapter_prompt(
        project_snapshot=project_snapshot,
        outline_chapter=outline_chapter,
        prev_chapter_summary=prev_chapter_summary,
        chapter_index=chapter_index,
        word_target=word_target,
        extra_feedback=extra_feedback,
    )
    kwargs = {}
    if temperature is not None:
        kwargs["temperature"] = temperature
    response = await provider.complete(
        [
            {"role": "system", "content": _CHAPTER_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        tools=None,
        **kwargs,
    )
    return response.content
