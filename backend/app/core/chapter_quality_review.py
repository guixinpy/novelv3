from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.outline_lookup import find_outline_chapter
from app.core.world_proposal_review_queue import build_proposal_review_queue
from app.models import ChapterContent, Outline, Project, ProjectProfileVersion
from app.prompting.providers.chapter import project_chapter_word_range

GENERIC_TITLE_RE = re.compile(r"^第\s*[\d零〇一二两三四五六七八九十百千]+\s*章$")
FUTURE_OUTLINE_WINDOW = 5


def review_chapter_quality(db: Session, project_id: str, chapter_index: int) -> dict[str, Any]:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        return _result(chapter_index=chapter_index, findings=[_finding("missing_project", "blocker", "项目不存在。")])

    chapter = (
        db.query(ChapterContent)
        .filter(ChapterContent.project_id == project_id, ChapterContent.chapter_index == chapter_index)
        .first()
    )
    if chapter is None:
        return _result(chapter_index=chapter_index, findings=[_finding("missing_chapter", "blocker", f"第{chapter_index}章尚未生成。")])

    findings: list[dict[str, Any]] = []
    outline_chapter = find_outline_chapter(db, project_id, chapter_index)
    if outline_chapter is None:
        findings.append(_finding("missing_outline_chapter", "blocker", f"第{chapter_index}章缺少章节大纲。"))

    title = (chapter.title or "").strip()
    if GENERIC_TITLE_RE.match(title):
        findings.append(_finding("generic_chapter_title", "blocker", f"第{chapter_index}章标题仍为通用占位标题。"))

    findings.extend(_word_target_findings(project, chapter))
    future_overlap = _future_outline_overlap(db, project_id=project_id, chapter_index=chapter_index, content=chapter.content or "")
    if future_overlap:
        findings.append(
            _finding(
                "future_outline_overlap",
                "blocker",
                "本章疑似提前消耗后续章节规划内容。",
                evidence=future_overlap,
            )
        )

    pending_count = _pending_world_model_proposal_count(db, project_id)
    if pending_count > 0:
        findings.append(
            _finding(
                "pending_world_model_proposals",
                "warning",
                f"世界模型仍有 {pending_count} 条待审提案，继续写作前建议先处理关键事实。",
                evidence={"pending_count": pending_count},
            )
        )

    return _result(chapter_index=chapter_index, findings=findings)


def _word_target_findings(project: Project, chapter: ChapterContent) -> list[dict[str, Any]]:
    target_range = project_chapter_word_range(project)
    if not target_range:
        return []
    target_min, target_max = target_range
    word_count = int(chapter.word_count or 0)
    if word_count > target_max:
        return [
            _finding(
                "chapter_over_target",
                "blocker",
                f"第{chapter.chapter_index}章 {word_count} 字，超过目标上限 {target_max} 字。",
                evidence={"word_count": word_count, "target_max_word_count": target_max},
            )
        ]
    if word_count < target_min:
        return [
            _finding(
                "chapter_under_target",
                "warning",
                f"第{chapter.chapter_index}章 {word_count} 字，低于目标下限 {target_min} 字。",
                evidence={"word_count": word_count, "target_min_word_count": target_min},
            )
        ]
    return []


def _future_outline_overlap(db: Session, *, project_id: str, chapter_index: int, content: str) -> dict[str, Any] | None:
    if not content:
        return None
    outline = (
        db.query(Outline)
        .filter(Outline.project_id == project_id)
        .order_by(Outline.updated_at.desc(), Outline.id.desc())
        .first()
    )
    if outline is None:
        return None
    matches: list[dict[str, Any]] = []
    for chapter in outline.chapters or []:
        if not isinstance(chapter, dict):
            continue
        future_index = _safe_int(chapter.get("chapter_index"))
        if future_index is None or future_index <= chapter_index or future_index > chapter_index + FUTURE_OUTLINE_WINDOW:
            continue
        tokens = _outline_tokens(chapter)
        matched_tokens = _significant_outline_matches(tokens, content)
        if matched_tokens:
            matches.append(
                {
                    "chapter_index": future_index,
                    "title": chapter.get("title"),
                    "matched_tokens": matched_tokens[:5],
                }
            )
    if not matches:
        return None
    return {"matches": matches[:5]}


def _significant_outline_matches(tokens: list[str], content: str) -> list[str]:
    matched_tokens = [token for token in tokens if token and token in content]
    if any(len(token) >= 4 for token in matched_tokens):
        return matched_tokens
    if len(matched_tokens) >= 2:
        return matched_tokens
    return []


def _outline_tokens(chapter: dict[str, Any]) -> list[str]:
    raw_parts = [str(chapter.get("title") or ""), str(chapter.get("summary") or "")]
    tokens: set[str] = set()
    for part in raw_parts:
        for text in re.split(r"[的，。！？、；：:\s]+", part):
            text = text.strip()
            if len(text) >= 2:
                tokens.add(text)
        for match in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", part):
            if len(match) >= 2:
                tokens.add(match)
    return sorted(tokens, key=lambda item: (-len(item), item))


def _pending_world_model_proposal_count(db: Session, project_id: str) -> int:
    try:
        profile = (
            db.query(ProjectProfileVersion)
            .filter(ProjectProfileVersion.project_id == project_id)
            .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
            .first()
        )
        queue = build_proposal_review_queue(db=db, project_id=project_id, profile=profile, limit=1)
        return int(queue.get("total_items") or 0)
    except Exception:
        return 0


def _finding(code: str, severity: str, message: str, *, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, "evidence": evidence or {}}


def _result(*, chapter_index: int, findings: list[dict[str, Any]]) -> dict[str, Any]:
    blocker_count = sum(1 for finding in findings if finding.get("severity") == "blocker")
    warning_count = sum(1 for finding in findings if finding.get("severity") == "warning")
    status = "blocked" if blocker_count else "warning" if warning_count else "ready"
    recommended_actions = _recommended_actions(findings)
    return {
        "status": status,
        "chapter_index": chapter_index,
        "finding_count": len(findings),
        "blocker_count": blocker_count,
        "findings": findings,
        "recommended_actions": recommended_actions,
    }


def _recommended_actions(findings: list[dict[str, Any]]) -> list[str]:
    actions: list[str] = []
    codes = {str(finding.get("code")) for finding in findings}
    if codes & {"generic_chapter_title", "chapter_over_target", "future_outline_overlap", "missing_outline_chapter"}:
        actions.append("revise_chapter")
    if "pending_world_model_proposals" in codes:
        actions.append("review_world_model_proposals")
    return actions


def _safe_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
