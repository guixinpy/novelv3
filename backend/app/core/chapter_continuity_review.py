from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from sqlalchemy.orm import Session

from app.models import ChapterContent, Project, ProjectProfileVersion, WorldFactClaim

DATE_RE = re.compile(r"\d{4}年\d{1,2}月\d{1,2}日")
IDENTIFIER_RE = re.compile(r"\b[A-Z]-\d+\b")
WIDE_IDENTIFIER_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z]{1,3}-\d+(?:-\d+)*(?![A-Za-z0-9])")
FATHER_DIRECT_RE = re.compile(r"父亲(?P<name>[\u4e00-\u9fff]{2,3})")
FATHER_NAME_APPOSITION_RE = re.compile(r"(?P<name>[\u4e00-\u9fff]{2,3})[———\-，,、\s]*他?父亲的名字")
SIGNATURE_RE = re.compile(r"署名[——:：-]*(?P<name>[\u4e00-\u9fff]{2,3})")
DEFAULT_LOOKBACK = 20
COMMON_CHINESE_SURNAMES = set("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜谢邹喻柏水窦章云苏潘葛奚范彭郎鲁韦昌马苗凤花方俞任袁柳鲍史唐费廉岑薛雷贺倪汤滕殷罗毕郝邬安常乐于时傅皮卞齐康伍余元卜顾孟平黄和穆萧尹林")
TRANSITION_TERMS = ("转移", "赶到", "穿过", "撤到", "抵达", "回到", "带他们", "几小时后", "数小时后", "次日", "第二天", "清晨之前")
TIME_MARKERS = ("夜里", "深夜", "凌晨", "清晨", "上午", "正午", "午后", "傍晚", "黄昏")
LOCATION_MARKERS = (
    "地下临时藏身点",
    "临时藏身点",
    "赵猛的安全屋",
    "安全屋",
    "暗渠",
    "排水管",
    "旧实验室",
    "地下室",
    "灯塔",
    "诊所",
)
HYPOTHESIS_TERMS = ("可能", "推断", "像是", "像", "也许", "疑似", "尚未确认", "猜测")
STABLE_TRUTH_ANCHOR_KEYS = {
    ("林深", "father_name"): "林深:father_name",
    ("顾衍", "military_tag_number"): "顾衍:military_tag_number",
    ("event.fog_disaster.minus_3_days", "relative_event_date"): "fog_disaster_minus_3_days",
}


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
        *_stable_truth_anchor_findings(
            chapters,
            _stable_truth_anchors(db, project_id=project_id, chapter_index=chapter_index),
        ),
        *_timeline_anchor_findings(chapters),
        *_identifier_anchor_findings(chapters),
        *_relationship_name_anchor_findings(chapters),
        *_adjacent_transition_findings(chapters, chapter_index),
        *_identifier_semantic_findings(chapters, chapter_index),
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
    anchors = _timeline_observed_anchors(chapters)
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
    anchors = _identifier_observed_anchors(chapters)
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


def _timeline_observed_anchors(chapters: list[Any]) -> dict[str, dict[str, list[dict[str, Any]]]]:
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
    return anchors


def _identifier_observed_anchors(chapters: list[Any]) -> dict[str, dict[str, list[dict[str, Any]]]]:
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
    return anchors


def _relationship_name_anchor_findings(chapters: list[Any]) -> list[dict[str, Any]]:
    anchors = _relationship_observed_anchors(chapters)
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


def _adjacent_transition_findings(chapters: list[Any], chapter_index: int) -> list[dict[str, Any]]:
    previous, current = _adjacent_chapter_pair(chapters, chapter_index)
    if previous is None or current is None:
        return []
    current_opening = _opening_excerpt(str(current.content or ""))
    if _has_transition_cue(current_opening):
        return []
    previous_ending = _ending_excerpt(str(previous.content or ""))
    previous_locations = _matched_terms(previous_ending, LOCATION_MARKERS)
    current_locations = _matched_terms(current_opening, LOCATION_MARKERS)
    previous_times = _matched_terms(previous_ending, TIME_MARKERS)
    current_times = _matched_terms(current_opening, TIME_MARKERS)
    location_shift = bool(previous_locations and current_locations and set(previous_locations).isdisjoint(current_locations))
    time_shift = bool(previous_times and current_times and set(previous_times).isdisjoint(current_times))
    if not (location_shift or time_shift):
        return []
    return [
        _finding(
            "adjacent_chapter_transition_gap",
            "warning",
            "相邻章节开场发生地点或时间切换，但当前章开头缺少明确过渡交代。",
            evidence={
                "previous_chapter_index": int(previous.chapter_index),
                "current_chapter_index": int(current.chapter_index),
                "previous_locations": previous_locations,
                "current_locations": current_locations,
                "previous_times": previous_times,
                "current_times": current_times,
                "previous_excerpt": previous_ending,
                "current_excerpt": current_opening,
            },
        )
    ]


def _identifier_semantic_findings(chapters: list[Any], chapter_index: int) -> list[dict[str, Any]]:
    current = next((chapter for chapter in chapters if int(chapter.chapter_index) == chapter_index), None)
    if current is None:
        return []
    history = [chapter for chapter in chapters if int(chapter.chapter_index) < chapter_index]
    if not history:
        return []
    previous_semantics = _identifier_semantics(history)
    current_semantics = _identifier_semantics([current])
    findings: list[dict[str, Any]] = []
    for identifier, current_refs in current_semantics.items():
        previous_refs = previous_semantics.get(identifier) or []
        for current_ref in current_refs:
            current_kind = current_ref["semantic_kind"]
            if current_kind == "unknown":
                continue
            previous_ref = next(
                (
                    ref
                    for ref in previous_refs
                    if ref["semantic_kind"] != "unknown" and ref["semantic_kind"] != current_kind
                ),
                None,
            )
            if previous_ref is None:
                continue
            findings.append(
                _finding(
                    "identifier_semantic_drift",
                    "warning",
                    f"{identifier} 的语义从 {_identifier_semantic_label(previous_ref['semantic_kind'])} 转向 {_identifier_semantic_label(current_kind)}，需要保持为推测或补足证据。",
                    evidence={
                        "identifier": identifier,
                        "previous_semantic_kind": previous_ref["semantic_kind"],
                        "current_semantic_kind": current_kind,
                        "current_is_hypothesis": _is_hypothesis(current_ref["excerpt"]),
                        "previous_reference": previous_ref,
                        "current_reference": current_ref,
                    },
                )
            )
            break
    return findings


def _stable_truth_anchor_findings(
    chapters: list[Any],
    truth_anchors: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not truth_anchors:
        return []
    observed = _observed_anchors(chapters)
    findings: list[dict[str, Any]] = []
    for anchor_key, truth in truth_anchors.items():
        refs_by_value = observed.get(anchor_key) or {}
        observed_values = [value for value in refs_by_value if value != truth["value"]]
        if not observed_values:
            continue
        findings.append(
            _finding(
                "stable_truth_anchor_conflict",
                "blocker",
                f"{_anchor_label(anchor_key)} 与已确认世界真相不一致，请先修正连续性锚点。",
                evidence={
                    "anchor_key": anchor_key,
                    "anchor_label": _anchor_label(anchor_key),
                    "truth_claim_id": truth["claim_id"],
                    "truth_value": truth["value"],
                    "observed_values": observed_values,
                    "references": {value: refs_by_value[value] for value in observed_values},
                },
            )
        )
    return findings


def _observed_anchors(chapters: list[Any]) -> dict[str, dict[str, list[dict[str, Any]]]]:
    observed: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for source in [
        _timeline_observed_anchors(chapters),
        _identifier_observed_anchors(chapters),
        _relationship_observed_anchors(chapters),
    ]:
        for anchor_key, refs_by_value in source.items():
            for value, refs in refs_by_value.items():
                observed[anchor_key][value].extend(refs)
    return observed


def _adjacent_chapter_pair(chapters: list[Any], chapter_index: int) -> tuple[Any | None, Any | None]:
    previous = None
    current = None
    for chapter in chapters:
        index = int(chapter.chapter_index)
        if index == chapter_index - 1:
            previous = chapter
        elif index == chapter_index:
            current = chapter
    return previous, current


def _opening_excerpt(content: str, *, max_chars: int = 180) -> str:
    sentences = _sentences(content)
    if not sentences:
        return content[:max_chars]
    return "。".join(sentences[:2])[:max_chars]


def _ending_excerpt(content: str, *, max_chars: int = 180) -> str:
    sentences = _sentences(content)
    if not sentences:
        return content[-max_chars:]
    return "。".join(sentences[-2:])[-max_chars:]


def _matched_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if term in text]


def _has_transition_cue(text: str) -> bool:
    return any(term in text for term in TRANSITION_TERMS)


def _identifier_semantics(chapters: list[Any]) -> dict[str, list[dict[str, Any]]]:
    semantics: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for chapter in chapters:
        for sentence in _anchor_windows(str(chapter.content or "")):
            for identifier in WIDE_IDENTIFIER_RE.findall(sentence):
                semantics[identifier].append(
                    {
                        "chapter_index": int(chapter.chapter_index),
                        "title": chapter.title,
                        "semantic_kind": _identifier_semantic_kind(sentence, identifier),
                        "excerpt": sentence,
                    }
                )
    return semantics


def _identifier_semantic_kind(sentence: str, identifier: str) -> str:
    index = sentence.find(identifier)
    if index < 0:
        return "unknown"
    window = sentence[max(0, index - 32) : min(len(sentence), index + len(identifier) + 48)]
    if any(term in window for term in ("项目", "实验项目", "第七号实验")):
        return "project_number"
    if any(term in window for term in ("证物柜", "柜号", "证物编号")) and not any(
        term in window for term in ("不是柜号", "并非柜号")
    ):
        return "evidence_locker"
    if any(term in window for term in ("实验体", "实验代号", "代号", "编号")) and not any(
        term in window for term in ("证物柜", "柜号")
    ):
        return "experiment_code"
    if any(term in window for term in ("虹膜门", "门禁", "记录", "档案")):
        return "event_record"
    return "unknown"


def _identifier_semantic_label(kind: str) -> str:
    return {
        "evidence_locker": "证物柜/证物编号",
        "project_number": "项目编号",
        "experiment_code": "实验代号",
        "event_record": "事件记录",
        "unknown": "未知语义",
    }.get(kind, kind)


def _is_hypothesis(text: str) -> bool:
    return any(term in text for term in HYPOTHESIS_TERMS)


def _relationship_observed_anchors(chapters: list[Any]) -> dict[str, dict[str, list[dict[str, Any]]]]:
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
    return anchors


def _stable_truth_anchors(db: Session, *, project_id: str, chapter_index: int) -> dict[str, dict[str, Any]]:
    profile = _current_profile(db, project_id)
    if profile is None:
        return {}
    facts = (
        db.query(WorldFactClaim)
        .filter(
            WorldFactClaim.project_id == project_id,
            WorldFactClaim.project_profile_version_id == profile.id,
            WorldFactClaim.profile_version == profile.version,
            WorldFactClaim.claim_status == "confirmed",
            WorldFactClaim.claim_layer == "truth",
            WorldFactClaim.predicate.in_({predicate for _subject, predicate in STABLE_TRUTH_ANCHOR_KEYS}),
            (WorldFactClaim.chapter_index.is_(None)) | (WorldFactClaim.chapter_index <= chapter_index),
        )
        .order_by(
            WorldFactClaim.chapter_index.asc().nullsfirst(),
            WorldFactClaim.intra_chapter_seq.asc(),
            WorldFactClaim.claim_id.asc(),
        )
        .all()
    )
    anchors: dict[str, dict[str, Any]] = {}
    for fact in facts:
        anchor_key = STABLE_TRUTH_ANCHOR_KEYS.get((fact.subject_ref, fact.predicate))
        if anchor_key is None:
            continue
        anchors[anchor_key] = {
            "claim_id": fact.claim_id,
            "value": _truth_value(fact.object_ref_or_value),
        }
    return anchors


def _current_profile(db: Session, project_id: str) -> ProjectProfileVersion | None:
    return (
        db.query(ProjectProfileVersion)
        .filter(ProjectProfileVersion.project_id == project_id)
        .order_by(ProjectProfileVersion.version.desc(), ProjectProfileVersion.created_at.desc())
        .first()
    )


def _truth_value(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("value", "date", "name", "number"):
            if key in value:
                return str(value[key])
    return str(value)


def _anchor_label(anchor_key: str) -> str:
    if anchor_key == "fog_disaster_minus_3_days":
        return _event_label(anchor_key)
    if anchor_key == "顾衍:military_tag_number":
        return _identifier_anchor_label(anchor_key)
    if anchor_key == "林深:father_name":
        return _relationship_anchor_label(anchor_key)
    return anchor_key


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
