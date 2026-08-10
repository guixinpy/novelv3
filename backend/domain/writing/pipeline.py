"""章节写作管线（workflow 图机制落地：plan → execute ⇄ review → finalize）。

- plan: 从 DB 组装任务上下文（大纲章节摘要 + 上一章摘要 + 项目快照）
- execute: generate_chapter（provider 生成，修订时带理由重写）
- review: format_checker + 结构窗口检测（error 级 issue → REVISE）
- finalize: 落库 chapter_contents（含字数统计）
- 修订循环: review fail → execute 带修订理由重写（max_revisions 上限）

机制（core/workflow）与真实实现解耦：本模块注入 worker，可 mock 测试。
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from core.providers.base import Provider
from core.workflow.base import ReviewCommand, ReviewVerdict, WorkflowEngine, WorkflowResult
from domain.memory.project_snapshot import build_project_snapshot
from domain.writing.chapter_gen import generate_chapter
from domain.writing.format_checker import check_chapter_hook, check_text_format
from domain.writing.structural_similarity import detect_structure_repeats


class ChapterPipeline:
    """单章写作管线：plan→execute⇄review→finalize（大纲→撰写→评审⇄修订→定稿）。

    注（code-review 三轮 #14）：09 定稿的"触发点 1"（章末自省回调）已移除——
    ChapterPipeline 无任何生产调用方（生产写章走 harness + write_chapter 工具），
    introspect 回调是死代码；自优化触发统一走 API 层 BackgroundTasks 路径。
    若未来人工标注/revise 流程接线 pipeline，自省应作为独立服务由调用方编排。
    """

    def __init__(
        self,
        provider: Provider,
        db: Session,
        project_id: str,
        *,
        max_revisions: int = 2,
        word_target: int = 2000,
    ) -> None:
        self.provider = provider
        self.db = db
        self.project_id = project_id
        self.max_revisions = max_revisions
        self.word_target = word_target

    async def run(self, chapter_index: int, *, extra_feedback: str = "") -> WorkflowResult:
        engine = WorkflowEngine(
            plan=self._plan,
            execute=self._execute,
            review=self._review,
            finalize=self._finalize,
            max_revisions=self.max_revisions,
        )
        context = {
            "chapter_index": chapter_index,
            "extra_feedback": extra_feedback,
            "word_target": self.word_target,
        }
        return await engine.run(context)

    # ── workers ──

    def _plan(self, context: dict) -> dict:
        from app.models import ChapterContent, Outline

        db = self.db
        project_id = self.project_id
        chapter_index = context["chapter_index"]

        # 大纲章节摘要
        outline_chapter = ""
        outline = db.query(Outline).filter(Outline.project_id == project_id).first()
        if outline is not None:
            for ch in outline.chapters or []:
                if ch.get("chapter_index") == chapter_index:
                    outline_chapter = str(ch.get("summary") or "")
                    break
        # 上一章摘要（最近 3 章简述）
        prev_chapters = (
            db.query(ChapterContent)
            .filter(
                ChapterContent.project_id == project_id,
                ChapterContent.chapter_index < chapter_index,
            )
            .order_by(ChapterContent.chapter_index.desc())
            .limit(3)
            .all()
        )
        prev_summary = "；".join(
            f"Ch{c.chapter_index}《{c.title}》：{c.content[:60]}…" for c in reversed(prev_chapters)
        )
        snapshot = build_project_snapshot(db, project_id) or ""
        return {
            "outline_chapter": outline_chapter,
            "prev_summary": prev_summary,
            "snapshot": snapshot,
        }

    async def _execute(self, context: dict, reason: str) -> str:
        planned = context.get("_planned") or self._plan(context)
        context["_planned"] = planned
        return await generate_chapter(
            self.provider,
            project_snapshot=planned["snapshot"],
            outline_chapter=planned["outline_chapter"],
            prev_chapter_summary=planned["prev_summary"],
            chapter_index=context["chapter_index"],
            word_target=context["word_target"],
            extra_feedback=reason or context.get("extra_feedback", ""),
        )

    def _review(self, context: dict, output: str) -> ReviewVerdict:
        from app.models import ChapterContent

        chapter_index = context["chapter_index"]
        issues = check_text_format(output)
        issues += check_chapter_hook(output)
        # 结构窗口：最近 20 章标题重复检测
        window = (
            self.db.query(ChapterContent)
            .filter(
                ChapterContent.project_id == self.project_id,
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
        error_issues = [i for i in issues if i.get("severity") == "error"]
        if error_issues:
            detail = "；".join(f"{i.get('type')}: {i.get('detail')}" for i in error_issues[:3])
            return ReviewVerdict(command=ReviewCommand.REVISE, reason=detail, issues=issues)
        return ReviewVerdict(command=ReviewCommand.APPROVE, issues=issues)

    def _finalize(self, context: dict, output: str) -> dict:
        from app.models import ChapterContent

        chapter_index = context["chapter_index"]
        existing = (
            self.db.query(ChapterContent)
            .filter(
                ChapterContent.project_id == self.project_id,
                ChapterContent.chapter_index == chapter_index,
            )
            .first()
        )
        word_count = len(output)
        if existing:
            existing.content = output
            existing.word_count = word_count
            existing.status = "generated"
        else:
            self.db.add(
                ChapterContent(
                    project_id=self.project_id,
                    chapter_index=chapter_index,
                    title=f"第{chapter_index}章",
                    content=output,
                    word_count=word_count,
                    status="generated",
                )
            )
        self.db.commit()
        return {
            "status": "written",
            "chapter_index": chapter_index,
            "word_count": word_count,
            "revisions": context.get("_revisions", 0),
        }
