"""领域工具（arch-refactor 最小闭环）：write_chapter / check_chapter_format。

- write_chapter：生成结果落库 chapter_contents + artifact 落盘（大产出移出上下文，
  openhuman 三级治理第三级）
- check_chapter_format：格式/结构校验（纯函数迁移 domain/writing）

工具返回值形状保持旧契约（status=written + word_count + chapter_index），
压缩摘要（core/context/compaction.py）依赖此形状提取「最近写入章节」。
"""
from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from core.tools.artifact import validate_artifact_path
from core.tools.base import ArtifactRef, ToolContext, ToolResult, ToolRegistry, tool
from domain.writing.format_checker import check_chapter_hook, check_text_format
from domain.writing.structural_similarity import detect_structure_repeats


class WriteChapterArgs(BaseModel):
    chapter_index: int = Field(..., ge=1, description="章节号（从 1 开始）")
    content: str = Field(..., min_length=50, description="章节正文")
    title: str = Field(default="", max_length=100, description="章节标题（可空）")


class CheckFormatArgs(BaseModel):
    chapter_index: int = Field(..., ge=1, description="章节号")


def register_writing_tools(registry: ToolRegistry) -> None:
    @tool(
        registry=registry,
        name="write_chapter",
        description=(
            "写入（新建或覆盖）指定章节的正文。章节正文是完整章节内容，"
            "不含章题行、不含 markdown 标记。返回写入状态与字数。"
        ),
        args_model=WriteChapterArgs,
        permission="write",
    )
    def write_chapter(
        ctx: ToolContext,
        chapter_index: int,
        content: str,
        title: str = "",
    ) -> ToolResult:
        db = ctx.db
        if db is None:
            return ToolResult.fail("工具上下文缺少 db 会话", error_code="tool_context_missing")
        project_id = ctx.project_id
        if not project_id:
            return ToolResult.fail("工具上下文缺少 project_id", error_code="tool_context_missing")

        from app.models import ChapterContent  # 旧 models 迁移前暂时引用

        existing = (
            db.query(ChapterContent)
            .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index)
            .first()
        )
        word_count = len(content)
        if existing:
            existing.content = content
            existing.title = title or existing.title
            existing.word_count = word_count
            existing.status = "generated"
        else:
            db.add(
                ChapterContent(
                    project_id=project_id,
                    chapter_index=chapter_index,
                    title=title or f"第{chapter_index}章",
                    content=content,
                    word_count=word_count,
                    status="generated",
                )
            )
        db.commit()

        # artifact 落盘：章节文本写文件、回传路径指针（大产出移出上下文）
        work_root = Path(ctx.extras.get("work_dir", "."))
        artifact = None
        rel_path = f"chapters/chapter_{chapter_index:03d}.md"
        validated = validate_artifact_path(rel_path, work_root)
        if validated is not None:
            try:
                path = Path(validated.path)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                artifact = ArtifactRef(path=rel_path, bytes=len(content.encode("utf-8")), summary=f"第{chapter_index}章")
            except OSError:
                artifact = None  # 落盘失败不阻断写入（弱失败）

        return ToolResult.ok(
            {
                "status": "written",
                "chapter_index": chapter_index,
                "word_count": word_count,
                "title": title,
                "created_or_updated": "updated" if existing else "created",
            },
            artifact=artifact,
        )

    @tool(
        registry=registry,
        name="check_chapter_format",
        description=(
            "检查指定章节的格式与结构问题（markdown 残留/备选词/章题行/引号/标点/结构重复）。"
            "返回 issue 列表，空列表表示通过。"
        ),
        args_model=CheckFormatArgs,
        permission="read",
    )
    def check_chapter_format(ctx: ToolContext, chapter_index: int) -> ToolResult:
        db = ctx.db
        if db is None or not ctx.project_id:
            return ToolResult.fail("工具上下文缺少 db/project_id", error_code="tool_context_missing")

        from app.models import ChapterContent

        chapter = (
            db.query(ChapterContent)
            .filter(ChapterContent.project_id == ctx.project_id, ChapterContent.chapter_index == chapter_index)
            .first()
        )
        if chapter is None:
            return ToolResult.fail(
                f"章节 {chapter_index} 不存在。请先用 write_chapter 写入该章节。",
                error_code="chapter_not_found",
            )
        issues = check_text_format(chapter.content)
        issues += check_chapter_hook(chapter.content)
        # 结构重复：以最近 20 章为窗口检测标题重复（T5 弱化版仅标题）
        window = (
            db.query(ChapterContent)
            .filter(
                ChapterContent.project_id == ctx.project_id,
                ChapterContent.chapter_index <= chapter_index,
            )
            .order_by(ChapterContent.chapter_index.desc())
            .limit(20)
            .all()
        )
        if len(window) > 1:
            issues += detect_structure_repeats(
                [{"index": c.chapter_index, "title": c.title or "", "content": c.content or ""} for c in window]
            )
        return ToolResult.ok({"chapter_index": chapter_index, "quality": "pass" if not issues else "fail", "issues": issues})
