from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.outline_lookup import find_outline_chapter
from app.core.world_proposal_review_queue import build_proposal_review_queue
from app.models import ChapterContent, Outline, Project, ProjectProfileVersion, Setup
from app.prompting.providers.chapter import project_chapter_word_range

GENERIC_TITLE_RE = re.compile(r"^第\s*[\d零〇一二两三四五六七八九十百千]+\s*章$")
FUTURE_OUTLINE_WINDOW = 5
IDENTITY_MARKERS = ("以前是", "其实是", "原来是", "曾是", "真实身份")
CONFLICTING_ROLE_TERMS = ("雾安局研究员", "雾安局特工", "研究员", "特工")
ABILITY_FORBIDDEN_TERMS = ("制造幻觉", "凭空创造", "创造真实记忆", "篡改记忆")
KEY_ITEM_TERMS = ("记忆雾晶", "雾晶", "钥匙", "核心", "信物")
ACQUISITION_TERMS = ("给了", "交给", "递给", "拿到", "获得", "买到")
COST_OR_RISK_TERMS = ("代价", "交换", "条件", "欠", "债", "受伤", "暴露", "损失", "背叛", "追杀", "风险")
KNOWN_TYPO_PATTERNS = {"戴着眼睛": "戴着眼镜"}
PREMATURE_MYSTERY_REVEAL_TERMS = (
    "我就是N-07",
    "那是我",
    "我是从第三研究所逃出来的",
    "十年前那场雾灾，是他们制造的",
    "苏晚晴是实验体",
)


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

    content = chapter.content or ""
    findings.extend(_duplicate_title_findings(db, project_id, chapter))
    findings.extend(_known_typo_findings(content))
    findings.extend(_word_target_findings(project, chapter))
    setup = _setup_payload(db, project_id)
    findings.extend(_character_profile_drift_findings(setup, content))
    findings.extend(_ability_boundary_findings(setup, content))
    findings.extend(_premature_mystery_reveal_findings(content))
    findings.extend(_convenient_key_item_findings(content))
    findings.extend(_structural_tail_findings(content))
    future_overlap = _future_outline_overlap(db, project_id=project_id, chapter_index=chapter_index, content=content)
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
        severity = "blocker" if word_count > round(target_max * 1.5) else "warning"
        return [
            _finding(
                "chapter_over_target",
                severity,
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


def _duplicate_title_findings(db: Session, project_id: str, chapter: ChapterContent) -> list[dict[str, Any]]:
    title = (chapter.title or "").strip()
    if not title or GENERIC_TITLE_RE.match(title):
        return []
    matched_indexes = [
        int(row.chapter_index)
        for row in (
            db.query(ChapterContent.chapter_index)
            .filter(
                ChapterContent.project_id == project_id,
                ChapterContent.chapter_index != chapter.chapter_index,
                ChapterContent.title == title,
            )
            .order_by(ChapterContent.chapter_index.asc())
            .all()
        )
    ]
    if not matched_indexes:
        return []
    return [
        _finding(
            "duplicate_chapter_title",
            "warning",
            f"第{chapter.chapter_index}章标题与既有章节重复，章节列表中容易混淆。",
            evidence={"title": title, "matched_chapter_indexes": matched_indexes},
        )
    ]


def _known_typo_findings(content: str) -> list[dict[str, Any]]:
    if not content:
        return []
    findings: list[dict[str, Any]] = []
    for matched_text, suggestion in KNOWN_TYPO_PATTERNS.items():
        index = content.find(matched_text)
        if index < 0:
            continue
        findings.append(
            _finding(
                "known_typo_pattern",
                "warning",
                "章节正文包含已知易错词，建议修正后再继续写作。",
                evidence={
                    "matched_text": matched_text,
                    "suggestion": suggestion,
                    "excerpt": content[max(0, index - 40) : index + len(matched_text) + 40],
                },
            )
        )
    return findings


def _setup_payload(db: Session, project_id: str) -> Setup | None:
    return (
        db.query(Setup)
        .filter(Setup.project_id == project_id)
        .order_by(Setup.created_at.desc(), Setup.id.desc())
        .first()
    )


def _character_profile_drift_findings(setup: Setup | None, content: str) -> list[dict[str, Any]]:
    if setup is None or not content:
        return []
    findings: list[dict[str, Any]] = []
    for character in setup.characters or []:
        if not isinstance(character, dict):
            continue
        name = str(character.get("name") or "").strip()
        known_profile = str(character.get("background") or character.get("role") or "").strip()
        if not name or name not in content:
            continue
        window = _text_window(content, name, radius=48)
        marker = next((term for term in IDENTITY_MARKERS if term in window), None)
        role = next((term for term in CONFLICTING_ROLE_TERMS if term in window and term not in known_profile), None)
        if marker and role:
            findings.append(
                _finding(
                    "character_profile_drift",
                    "blocker",
                    f"{name} 的身份表述疑似偏离既有设定。",
                    evidence={
                        "character": name,
                        "known_profile": known_profile,
                        "matched_marker": marker,
                        "matched_role": role,
                        "excerpt": window,
                    },
                )
            )
    return findings


def _ability_boundary_findings(setup: Setup | None, content: str) -> list[dict[str, Any]]:
    if setup is None or not content:
        return []
    setup_text = _setup_text(setup)
    if not any(marker in setup_text for marker in ("不能", "不可", "禁止", "无法")):
        return []
    matched_terms = [term for term in ABILITY_FORBIDDEN_TERMS if term in content]
    if not matched_terms:
        return []
    return [
        _finding(
            "ability_boundary_drift",
            "blocker",
            "本章能力表现疑似突破既有世界规则或角色能力边界。",
            evidence={"matched_terms": matched_terms, "known_rules_excerpt": setup_text[:300]},
        )
    ]


def _premature_mystery_reveal_findings(content: str) -> list[dict[str, Any]]:
    if not content or "N-07" not in content:
        return []
    matched_terms = [term for term in PREMATURE_MYSTERY_REVEAL_TERMS if term in content]
    if not matched_terms:
        return []
    index = min(content.find(term) for term in matched_terms if term in content)
    return [
        _finding(
            "premature_mystery_reveal",
            "blocker",
            "本章疑似过早确认核心身份或终局真相，应改为未确认线索或待验证碎片。",
            evidence={
                "matched_terms": matched_terms,
                "excerpt": content[max(0, index - 80) : index + 180],
            },
        )
    ]


def _convenient_key_item_findings(content: str) -> list[dict[str, Any]]:
    if not content:
        return []
    for sentence in _sentences(content):
        matched_terms = [term for term in KEY_ITEM_TERMS if term in sentence]
        if not matched_terms:
            continue
        if not any(term in sentence for term in ACQUISITION_TERMS):
            continue
        if any(term in sentence for term in COST_OR_RISK_TERMS):
            continue
        return [
            _finding(
                "convenient_key_item_acquisition",
                "warning",
                "关键道具或线索获得过于顺滑，建议补足代价、条件、债务或风险。",
                evidence={"matched_terms": matched_terms, "excerpt": sentence},
            )
        ]
    return []


def _structural_tail_findings(content: str) -> list[dict[str, Any]]:
    if not content:
        return []
    if content.count("“") > content.count("”"):
        tail = content[-120:]
        return [
            _finding(
                "unclosed_dialogue_quote",
                "blocker",
                "章节末尾存在未闭合对白引号，疑似压缩或修订后断尾。",
                evidence={"tail_excerpt": tail},
            )
        ]
    return []


def _setup_text(setup: Setup) -> str:
    parts = [setup.world_building, setup.characters, setup.core_concept]
    return " ".join(str(part) for part in parts if part)


def _text_window(content: str, term: str, *, radius: int) -> str:
    index = content.find(term)
    if index < 0:
        return ""
    start = max(index - radius, 0)
    end = min(index + len(term) + radius, len(content))
    return content[start:end]


def _sentences(content: str) -> list[str]:
    return [part.strip() for part in re.split(r"[。！？!?；;]\s*", content) if part.strip()]


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
    revision_codes = {
        "generic_chapter_title",
        "chapter_over_target",
        "future_outline_overlap",
        "missing_outline_chapter",
        "character_profile_drift",
        "ability_boundary_drift",
        "unclosed_dialogue_quote",
        "premature_mystery_reveal",
    }
    if any(finding.get("code") in revision_codes and finding.get("severity") == "blocker" for finding in findings):
        actions.append("revise_chapter")
    if "pending_world_model_proposals" in codes:
        actions.append("review_world_model_proposals")
    return actions


def _safe_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
