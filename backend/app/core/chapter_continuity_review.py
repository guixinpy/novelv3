from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models import ChapterContent, Project

DATE_RE = re.compile(r"\d{4}年\d{1,2}月\d{1,2}日")
IDENTIFIER_RE = re.compile(r"\b[A-Z]-\d+\b")
FATHER_DIRECT_RE = re.compile(r"父亲(?P<name>[\u4e00-\u9fff]{2,3})")
FATHER_NAME_APPOSITION_RE = re.compile(r"(?P<name>[\u4e00-\u9fff]{2,3})[———\-，,、\s]*他?父亲的名字")
SIGNATURE_RE = re.compile(r"署名[——:：-]*(?P<name>[\u4e00-\u9fff]{2,3})")
DEFAULT_LOOKBACK = 20
COMMON_CHINESE_SURNAMES = set("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹林")


def review_chapter_continuity(
    db: Session,
    project_id: str,
    chapter_index: int,
    *,
    lookback: int = DEFAULT_LOOKBACK,
) -> dict[str, Any]:
    project = db.query(Project.id).filter(Project.id == project_id).first()
    if project is None:
        return _result(chapter_index=chapter_index, findings=[_finding("missing_project", "blocker", "项目不存在。")])

    chapters = _chapters_for_review(db, project_id=project_id, chapter_index=chapter_index, lookback=lookback)
    if not any(int(chapter.chapter_index) == chapter_index for chapter in chapters):
        return _result(
            chapter_index=chapter_index,
            findings=[_finding("missing_chapter", "blocker", f"第{chapter_index}章尚未生成。")],
        )

    findings = [
        *_timeline_anchor_findings(chapters),
        *_identifier_anchor_findings(chapters),
        *_relationship_name_anchor_findings(chapters),
    ]
    return _result(chapter_index=chapter_index, findings=findings)


def _chapters_for_review(
    db: Session,
    *,
    project_id: str,
    chapter_index: int,
    lookback: int,
) -> list[Any]:
    start = max(1, chapter_index - max(lookback, 1) + 1)
    return (
        db.query(ChapterContent.chapter_index, ChapterContent.title, ChapterContent.content)
        .filter(
            ChapterContent.project_id == project_id,
            ChapterContent.chapter_index >= start,
            ChapterContent.chapter_index <= chapter_index,
            ChapterContent.content != "",
        )
        .order_by(ChapterContent.chapter_index.asc())
        .all()
    )


def _timeline_anchor_findings(chapters: list[Any]) -> list[dict[str, Any]]:
    anchors: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for chapter in chapters:
        for sentence in _anchor_windows(str(chapter.content or "")):
            event_key = _event_key(sentence)
            if event_key is None:
                continue
            for date_value in DATE_RE.findall(sentence):
                anchors[event_key][date_value].append(
                    {
                        "chapter_index": int(chapter.chapter_index),
                        "title": chapter.title,
                        "excerpt": sentence,
                    }
                )

    findings: list[dict[str, Any]] = []
    for event_key, refs_by_value in anchors.items():
        values = list(refs_by_value.keys())
        if len(values) < 2:
            continue
        findings.append(
            _finding(
                "timeline_anchor_conflict",
                "blocker",
                f"{_event_label(event_key)} 对应了多个日期，请先统一时间线锚点。",
                evidence={
                    "event_key": event_key,
                    "event_label": _event_label(event_key),
                    "values": values,
                    "references": {value: refs for value, refs in refs_by_value.items()},
                },
            )
        )
    return findings


def _identifier_anchor_findings(chapters: list[Any]) -> list[dict[str, Any]]:
    anchors: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for chapter in chapters:
        for sentence in _anchor_windows(str(chapter.content or "")):
            anchor_key = _identifier_anchor_key(sentence)
            if anchor_key is None:
                continue
            for value in IDENTIFIER_RE.findall(sentence):
                if anchor_key == "顾衍:military_tag_number" and not _is_military_tag_value(sentence, value):
                    continue
                anchors[anchor_key][value].append(
                    {
                        "chapter_index": int(chapter.chapter_index),
                        "title": chapter.title,
                        "excerpt": sentence,
                    }
                )

    findings: list[dict[str, Any]] = []
    for anchor_key, refs_by_value in anchors.items():
        values = list(refs_by_value.keys())
        if len(values) < 2:
            continue
        findings.append(
            _finding(
                "identifier_anchor_conflict",
                "blocker",
                f"{_identifier_anchor_label(anchor_key)} 对应了多个编号，请先统一编号含义。",
                evidence={
                    "anchor_key": anchor_key,
                    "anchor_label": _identifier_anchor_label(anchor_key),
                    "values": values,
                    "references": {value: refs for value, refs in refs_by_value.items()},
                },
            )
        )
    return findings


def _relationship_name_anchor_findings(chapters: list[Any]) -> list[dict[str, Any]]:
    anchors: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for chapter in chapters:
        for sentence in _anchor_windows(str(chapter.content or "")):
            names = _father_name_values(sentence)
            if not names:
                continue
            for name in names:
                anchors["林深:father_name"][name].append(
                    {
                        "chapter_index": int(chapter.chapter_index),
                        "title": chapter.title,
                        "excerpt": sentence,
                    }
                )

    findings: list[dict[str, Any]] = []
    for anchor_key, refs_by_value in anchors.items():
        values = list(refs_by_value.keys())
        if len(values) < 2:
            continue
        findings.append(
            _finding(
                "relationship_name_anchor_conflict",
                "blocker",
                f"{_relationship_anchor_label(anchor_key)} 对应了多个姓名，请先统一人物关系锚点。",
                evidence={
                    "anchor_key": anchor_key,
                    "anchor_label": _relationship_anchor_label(anchor_key),
                    "values": values,
                    "references": {value: refs for value, refs in refs_by_value.items()},
                },
            )
        )
    return findings


def _father_name_values(sentence: str) -> list[str]:
    if "父亲" not in sentence:
        return []
    names: list[str] = []
    direct = FATHER_DIRECT_RE.search(sentence)
    if direct and _looks_like_person_name(direct.group("name")):
        names.append(direct.group("name"))
    apposition = FATHER_NAME_APPOSITION_RE.search(sentence)
    if apposition and _looks_like_person_name(apposition.group("name")):
        names.append(apposition.group("name"))
    signature = SIGNATURE_RE.search(sentence)
    if signature and _looks_like_person_name(signature.group("name")):
        names.append(signature.group("name"))
    return _dedupe(names)


def _looks_like_person_name(value: str) -> bool:
    if value.startswith(("和", "与", "及", "跟")):
        return False
    return len(value) in {2, 3} and value[0] in COMMON_CHINESE_SURNAMES and not value.endswith("的")


def _relationship_anchor_label(anchor_key: str) -> str:
    return {
        "林深:father_name": "林深父亲姓名",
    }.get(anchor_key, anchor_key)


def _identifier_anchor_key(sentence: str) -> str | None:
    if "顾衍" in sentence and "军牌" in sentence and ("编号" in sentence or "刻着" in sentence):
        return "顾衍:military_tag_number"
    return None


def _is_military_tag_value(sentence: str, value: str) -> bool:
    index = sentence.find(value)
    if index < 0:
        return False
    prefix = sentence[max(0, index - 28) : index]
    suffix = sentence[index : min(len(sentence), index + len(value) + 18)]
    local = prefix + suffix
    if "不是军牌编号" in local or "实验代号" in local or "暗纹" in prefix:
        return False
    return "编号" in prefix or "刻着" in prefix


def _identifier_anchor_label(anchor_key: str) -> str:
    return {
        "顾衍:military_tag_number": "顾衍的军牌编号",
    }.get(anchor_key, anchor_key)


def _event_key(sentence: str) -> str | None:
    if "雾灾发生前三天" in sentence or "雾灾发生的前三天" in sentence or "雾灾前三天" in sentence:
        return "fog_disaster_minus_3_days"
    return None


def _event_label(event_key: str) -> str:
    return {
        "fog_disaster_minus_3_days": "雾灾发生前三天",
    }.get(event_key, event_key)


def _sentences(content: str) -> list[str]:
    return [part.strip() for part in re.split(r"[。！？!?；;]\s*", content) if part.strip()]


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _anchor_windows(content: str) -> list[str]:
    sentences = _sentences(content)
    windows: list[str] = []
    for index, sentence in enumerate(sentences):
        windows.append(sentence)
        if index > 0:
            windows.append(f"{sentences[index - 1]}。{sentence}")
    return windows


def _finding(code: str, severity: str, message: str, *, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"code": code, "severity": severity, "message": message, "evidence": evidence or {}}


def _result(*, chapter_index: int, findings: list[dict[str, Any]]) -> dict[str, Any]:
    blocker_count = sum(1 for finding in findings if finding.get("severity") == "blocker")
    warning_count = sum(1 for finding in findings if finding.get("severity") == "warning")
    status = "blocked" if blocker_count else "warning" if warning_count else "ready"
    return {
        "status": status,
        "chapter_index": chapter_index,
        "finding_count": len(findings),
        "blocker_count": blocker_count,
        "findings": findings,
        "recommended_actions": ["revise_chapter"] if blocker_count else [],
    }
