"""Chapter-to-world proposal candidate builders for Athena."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session

from app.core.athena_entity_resolver import (
    character_descriptors,
    chapter_sentences,
    count_entity_mentions,
    entity_ref,
    location_descriptors_from_world_model,
    non_character_entities_from_world_model,
    slug,
)
from app.core.world_contracts import DERIVED
from app.models import ChapterContent, ProjectProfileVersion
from app.schemas.world_proposals import ProposalCandidateFactCreate

WIDE_IDENTIFIER_RE = re.compile(r"(?<![A-Za-z0-9])[A-Z]{1,3}-\d+(?:-\d+)*(?![A-Za-z0-9])")
HYPOTHESIS_TERMS = ("可能", "推断", "像是", "也许", "疑似", "尚未确认", "猜测")
LEGACY_PLOT_SIGNAL_LIMIT = 6
HIGH_VALUE_SIGNAL_LIMIT = 12
VIDEO_TERMS = ("录像", "监控", "视频", "画面", "屏幕")
HISTORICAL_TERMS = ("十年前", "旧", "当年", "历史", "雾灾当夜")
MEMORY_ERASURE_TERMS = ("记忆被抹除", "记忆抹除", "记忆删除", "记忆被删除", "删除记忆", "清洗记忆", "记忆清洗")
PARENT_TERMS = ("父亲", "母亲", "父母", "爸爸", "妈妈")
FOG_DISASTER_TERMS = ("雾灾", "灾难")
FOG_CAUSE_TERMS = ("不是天灾", "人祸", "人为", "实验失控", "制造")
UNKNOWN_OPERATOR_TERMS = ("黑衣研究员", "研究员", "操作员", "陌生人", "黑衣人")
INTERVENTION_TERMS = ("强行带进", "带进", "推进", "拖进", "启动", "扫描", "介入")


def candidate_from_l1_fact(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    fact: dict[str, Any],
) -> ProposalCandidateFactCreate:
    name = str(fact.get("subject") or "").strip()
    subject_ref = str(fact.get("subject_ref") or "").strip() or entity_ref("char", name)
    claim_id = f"claim.chapter.{chapter.chapter_index}.{slug(subject_ref)}.presence_count"
    return ProposalCandidateFactCreate(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        contract_version=profile.contract_version,
        claim_id=claim_id,
        chapter_index=chapter.chapter_index,
        intra_chapter_seq=0,
        subject_ref=subject_ref,
        predicate="presence_count",
        object_ref_or_value={
            "count": int(fact.get("new_value") or 1),
            "chapter_index": chapter.chapter_index,
            "source": "l1_rule",
            "matched_names": fact.get("matched_names") or [name],
            "evidence_span": {
                "ref": f"chapter:{chapter.chapter_index}",
                "matched_names": fact.get("matched_names") or [name],
            },
            "quality": candidate_quality(signal="character_presence", confidence_band="medium"),
        },
        claim_layer="truth",
        evidence_refs=[f"chapter:{chapter.chapter_index}"],
        authority_type=DERIVED,
        confidence=float(fact.get("confidence") or 0.85),
        notes=f"自动抽取：{name} 在第{chapter.chapter_index}章出现 {fact.get('new_value', 1)} 次。",
    )


def extract_non_character_entity_mentions(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
) -> list[ProposalCandidateFactCreate]:
    text = chapter.content or ""
    candidates: list[ProposalCandidateFactCreate] = []
    for entity in non_character_entities_from_world_model(db, project_id, profile.version):
        mention_count = count_entity_mentions(text=text, names=entity["names"])
        if mention_count <= 0:
            continue
        candidates.append(
            candidate_from_entity_mention(
                project_id=project_id,
                profile=profile,
                chapter=chapter,
                entity_ref_value=entity["ref"],
                entity_name=entity["name"],
                entity_type=entity["entity_type"],
                mention_count=mention_count,
            )
        )
    return candidates


def extract_chapter_event_candidate(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
) -> ProposalCandidateFactCreate | None:
    summary = chapter_event_summary(chapter)
    if not summary:
        return None
    return ProposalCandidateFactCreate(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        contract_version=profile.contract_version,
        claim_id=f"claim.chapter.{chapter.chapter_index}.event.summary",
        chapter_index=chapter.chapter_index,
        intra_chapter_seq=0,
        subject_ref=f"chapter.{chapter.chapter_index}",
        predicate="event_summary",
        object_ref_or_value={
            "chapter_index": chapter.chapter_index,
            "title": chapter.title or f"第{chapter.chapter_index}章",
            "summary": summary,
            "source": "deterministic_chapter_summary",
            "evidence_span": {
                "ref": f"chapter:{chapter.chapter_index}",
                "text": summary,
            },
            "quality": candidate_quality(signal="event_summary", confidence_band="low", review_priority="high"),
        },
        claim_layer="truth",
        evidence_refs=[f"chapter:{chapter.chapter_index}"],
        authority_type=DERIVED,
        confidence=0.7,
        notes=f"自动抽取：第{chapter.chapter_index}章事件摘要，需人工确认。",
    )


def extract_high_value_plot_signal_candidates(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
) -> list[ProposalCandidateFactCreate]:
    text = chapter.content or ""
    if not text:
        return []
    candidates: list[ProposalCandidateFactCreate] = []
    seen: set[tuple[str, str]] = set()
    sentences = chapter_sentences(text)
    for sentence in sentences:
        for candidate in _identifier_meaning_candidates(
            project_id=project_id,
            profile=profile,
            chapter=chapter,
            sentence=sentence,
        ):
            _append_unique_candidate(candidates, candidate, seen)
        lead = _investigation_lead_candidate(
            project_id=project_id,
            profile=profile,
            chapter=chapter,
            sentence=sentence,
        )
        if lead is not None:
            _append_unique_candidate(candidates, lead, seen)
        if len(candidates) >= LEGACY_PLOT_SIGNAL_LIMIT:
            break
    permission = _access_permission_candidate(
        project_id=project_id,
        profile=profile,
        chapter=chapter,
        sentences=sentences,
    )
    if permission is not None:
        _append_unique_candidate(candidates, permission, seen)
    for candidate in _historical_video_signal_candidates(
        project_id=project_id,
        profile=profile,
        chapter=chapter,
        sentences=sentences,
    ):
        _append_unique_candidate(candidates, candidate, seen)
        if len(candidates) >= HIGH_VALUE_SIGNAL_LIMIT:
            break
    return candidates


def _identifier_meaning_candidates(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    sentence: str,
) -> list[ProposalCandidateFactCreate]:
    if "项目" not in sentence and "不是柜号" not in sentence:
        return []
    candidates: list[ProposalCandidateFactCreate] = []
    for identifier in WIDE_IDENTIFIER_RE.findall(sentence):
        speaker = _speaker_before(sentence, "推断") or _speaker_before(sentence, "判断") or ""
        subject_ref = f"identifier.{slug(identifier)}"
        candidates.append(
            ProposalCandidateFactCreate(
                project_id=project_id,
                project_profile_version_id=profile.id,
                profile_version=profile.version,
                contract_version=profile.contract_version,
                claim_id=f"claim.chapter.{chapter.chapter_index}.{slug(identifier)}.identifier_meaning_hypothesis",
                chapter_index=chapter.chapter_index,
                intra_chapter_seq=0,
                subject_ref=subject_ref,
                predicate="identifier_meaning_hypothesis",
                object_ref_or_value={
                    "chapter_index": chapter.chapter_index,
                    "identifier": identifier,
                    "speaker": speaker or None,
                    "hypothesis": sentence[:220],
                    "is_hypothesis": _is_hypothesis(sentence),
                    "source": "deterministic_plot_signal",
                    "evidence_span": {"ref": f"chapter:{chapter.chapter_index}", "text": sentence[:240]},
                    "quality": candidate_quality(signal="identifier_meaning", confidence_band="medium", review_priority="high"),
                },
                claim_layer="truth",
                evidence_refs=[f"chapter:{chapter.chapter_index}"],
                authority_type=DERIVED,
                confidence=0.82,
                notes=f"自动抽取：{identifier} 出现新的语义解释，需要审阅其是否为角色推断。",
            )
        )
    return candidates


def _access_permission_candidate(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    sentences: list[str],
) -> ProposalCandidateFactCreate | None:
    window = _access_permission_window(sentences)
    if not window:
        return None
    actor = _actor_near_iris(window)
    subject_ref = entity_ref("char", actor) if actor else f"chapter.{chapter.chapter_index}"
    return ProposalCandidateFactCreate(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        contract_version=profile.contract_version,
        claim_id=f"claim.chapter.{chapter.chapter_index}.{slug(subject_ref)}.access_permission_anomaly",
        chapter_index=chapter.chapter_index,
        intra_chapter_seq=0,
        subject_ref=subject_ref,
        predicate="access_permission_anomaly",
        object_ref_or_value={
            "chapter_index": chapter.chapter_index,
            "actor_name": actor or None,
            "anomaly": window[:220],
            "source": "deterministic_plot_signal",
            "evidence_span": {"ref": f"chapter:{chapter.chapter_index}", "text": window[:240]},
            "quality": candidate_quality(signal="access_permission_anomaly", confidence_band="medium", review_priority="high"),
        },
        claim_layer="truth",
        evidence_refs=[f"chapter:{chapter.chapter_index}"],
        authority_type=DERIVED,
        confidence=0.8,
        notes="自动抽取：角色权限或身份异常，需要审阅后再进入世界事实。",
    )


def _investigation_lead_candidate(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    sentence: str,
) -> ProposalCandidateFactCreate | None:
    if not any(term in sentence for term in ("周明远", "清道夫")):
        return None
    if not any(term in sentence for term in ("线索", "最后见过", "行动", "处理", "指向")):
        return None
    lead_key = "周明远" if "周明远" in sentence else "清道夫"
    return ProposalCandidateFactCreate(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        contract_version=profile.contract_version,
        claim_id=f"claim.chapter.{chapter.chapter_index}.{slug(lead_key)}.investigation_lead",
        chapter_index=chapter.chapter_index,
        intra_chapter_seq=0,
        subject_ref=f"lead.{slug(lead_key)}",
        predicate="investigation_lead",
        object_ref_or_value={
            "chapter_index": chapter.chapter_index,
            "lead_key": lead_key,
            "lead": sentence[:220],
            "source": "deterministic_plot_signal",
            "evidence_span": {"ref": f"chapter:{chapter.chapter_index}", "text": sentence[:240]},
            "quality": candidate_quality(signal="investigation_lead", confidence_band="medium", review_priority="high"),
        },
        claim_layer="truth",
        evidence_refs=[f"chapter:{chapter.chapter_index}"],
        authority_type=DERIVED,
        confidence=0.78,
        notes="自动抽取：调查线索会影响后续追查方向，需要单独审阅。",
    )


def _historical_video_signal_candidates(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    sentences: list[str],
) -> list[ProposalCandidateFactCreate]:
    specs = [
        (
            "historical_video_evidence",
            f"chapter.{chapter.chapter_index}.historical_video",
            "video_evidence",
            _historical_video_window(sentences),
            "自动抽取：旧录像或监控证据可能改变主线真相，应单独审阅。",
            0.78,
        ),
        (
            "memory_erasure_hypothesis",
            f"chapter.{chapter.chapter_index}.memory_erasure",
            "memory_erasure",
            _memory_erasure_window(sentences),
            "自动抽取：记忆删除或抹除线索应先保留为待证推断。",
            0.8,
        ),
        (
            "parental_involvement_hypothesis",
            f"chapter.{chapter.chapter_index}.parental_involvement",
            "parental_involvement",
            _parental_involvement_window(sentences),
            "自动抽取：父母参与历史事件的线索会影响人物弧线，应单独审阅。",
            0.78,
        ),
        (
            "fog_disaster_cause_hypothesis",
            f"chapter.{chapter.chapter_index}.fog_disaster_cause",
            "fog_disaster_cause",
            _fog_disaster_cause_window(sentences),
            "自动抽取：雾灾成因线索属于核心谜团，应标为待证推断。",
            0.82,
        ),
        (
            "unknown_operator_intervention",
            f"chapter.{chapter.chapter_index}.unknown_operator",
            "unknown_operator",
            _unknown_operator_window(sentences),
            "自动抽取：未知操作者介入历史事件，需审阅身份和行为边界。",
            0.78,
        ),
    ]
    candidates: list[ProposalCandidateFactCreate] = []
    for predicate, subject_ref, signal, evidence, notes, confidence in specs:
        if not evidence:
            continue
        candidates.append(
            _plot_signal_candidate(
                project_id=project_id,
                profile=profile,
                chapter=chapter,
                subject_ref=subject_ref,
                predicate=predicate,
                signal=signal,
                evidence=evidence,
                notes=notes,
                confidence=confidence,
            )
        )
    return candidates


def _plot_signal_candidate(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    subject_ref: str,
    predicate: str,
    signal: str,
    evidence: str,
    notes: str,
    confidence: float,
) -> ProposalCandidateFactCreate:
    return ProposalCandidateFactCreate(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        contract_version=profile.contract_version,
        claim_id=f"claim.chapter.{chapter.chapter_index}.{slug(subject_ref)}.{predicate}",
        chapter_index=chapter.chapter_index,
        intra_chapter_seq=0,
        subject_ref=subject_ref,
        predicate=predicate,
        object_ref_or_value={
            "chapter_index": chapter.chapter_index,
            "signal": signal,
            "evidence": evidence[:220],
            "is_hypothesis": _is_hypothesis(evidence) or predicate.endswith("_hypothesis"),
            "source": "deterministic_plot_signal",
            "evidence_span": {"ref": f"chapter:{chapter.chapter_index}", "text": evidence[:240]},
            "quality": candidate_quality(signal=signal, confidence_band="medium", review_priority="high"),
        },
        claim_layer="truth",
        evidence_refs=[f"chapter:{chapter.chapter_index}"],
        authority_type=DERIVED,
        confidence=confidence,
        notes=notes,
    )


def _historical_video_window(sentences: list[str]) -> str:
    for index, sentence in enumerate(sentences):
        if not any(term in sentence for term in VIDEO_TERMS):
            continue
        window = "。".join(sentences[index : index + 2])
        if any(term in window for term in HISTORICAL_TERMS + ("实验", "雾灾")):
            return window
    return ""


def _memory_erasure_window(sentences: list[str]) -> str:
    for index, sentence in enumerate(sentences):
        if any(term in sentence for term in MEMORY_ERASURE_TERMS):
            return sentence
        if "记忆" in sentence and any(term in sentence for term in ("抹去", "模糊", "空白", "断片")):
            return sentence
        window = "。".join(sentences[index : index + 8])
        if "记忆" in window and any(term in window for term in ("抹去", "模糊", "空白", "断片")):
            return window
    return ""


def _parental_involvement_window(sentences: list[str]) -> str:
    for index, sentence in enumerate(sentences):
        if not any(term in sentence for term in PARENT_TERMS):
            continue
        window = "。".join(sentences[max(0, index - 1) : index + 2])
        if any(term in window for term in ("实验", "录像", "监控", "雾灾", "舱室")):
            return window
    return ""


def _fog_disaster_cause_window(sentences: list[str]) -> str:
    for sentence in sentences:
        if any(term in sentence for term in FOG_DISASTER_TERMS) and any(term in sentence for term in FOG_CAUSE_TERMS):
            return sentence
    return ""


def _unknown_operator_window(sentences: list[str]) -> str:
    for index, sentence in enumerate(sentences):
        if not any(term in sentence for term in UNKNOWN_OPERATOR_TERMS):
            continue
        window = "。".join(sentences[index : index + 2])
        if any(term in window for term in INTERVENTION_TERMS):
            return window
    return ""


def extract_character_location_candidates(
    *,
    db: Session,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    characters: list[dict[str, Any]],
) -> list[ProposalCandidateFactCreate]:
    text = chapter.content or ""
    if not text:
        return []
    resolved_characters = character_descriptors(characters)
    location_descriptors = location_descriptors_from_world_model(db, project_id, profile.version)
    candidates: list[ProposalCandidateFactCreate] = []
    seen: set[tuple[str, str]] = set()
    for sentence in chapter_sentences(text):
        for character in resolved_characters:
            if count_entity_mentions(text=sentence, names=character["names"]) <= 0:
                continue
            for location in location_descriptors:
                if count_entity_mentions(text=sentence, names=location["names"]) <= 0:
                    continue
                key = (character["ref"], location["ref"])
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(
                    candidate_from_character_location(
                        project_id=project_id,
                        profile=profile,
                        chapter=chapter,
                        character_ref=character["ref"],
                        character_name=character["name"],
                        location_ref=location["ref"],
                        location_name=location["name"],
                        evidence=sentence,
                    )
                )
                if len(candidates) >= 12:
                    return candidates
    return candidates


def _append_unique_candidate(
    candidates: list[ProposalCandidateFactCreate],
    candidate: ProposalCandidateFactCreate,
    seen: set[tuple[str, str]],
) -> None:
    key = (candidate.claim_id, candidate.predicate)
    if key in seen:
        return
    seen.add(key)
    candidates.append(candidate)


def _speaker_before(sentence: str, verb: str) -> str | None:
    match = re.search(rf"([\u4e00-\u9fff]{{2,3}}){verb}", sentence)
    if not match:
        return None
    return match.group(1)


def _actor_near_iris(sentence: str) -> str | None:
    for known_name in ("林深", "林舟", "苏晚晴", "沈聆", "顾衍"):
        if known_name in sentence:
            return known_name
    for pattern in (r"([\u4e00-\u9fff]{2,3})把眼睛", r"([\u4e00-\u9fff]{2,3})的虹膜", r"([\u4e00-\u9fff]{2,3})凑近"):
        match = re.search(pattern, sentence)
        if match:
            return match.group(1)
    return None


def _access_permission_window(sentences: list[str]) -> str:
    for index in range(len(sentences)):
        window = "。".join(sentences[index : index + 6])
        if "虹膜" not in window:
            continue
        if not any(term in window for term in ("眼睛", "扫描", "虹膜数据", "虹膜扫描")):
            continue
        if not any(term in window for term in ("门开了", "开了", "能打开这扇门", "验证通过", "门锁发出")):
            continue
        return window
    return ""


def _is_hypothesis(sentence: str) -> bool:
    return any(term in sentence for term in HYPOTHESIS_TERMS)


def candidate_from_character_location(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    character_ref: str,
    character_name: str,
    location_ref: str,
    location_name: str,
    evidence: str,
) -> ProposalCandidateFactCreate:
    claim_id = f"claim.chapter.{chapter.chapter_index}.{slug(character_ref)}.{slug(location_ref)}.present_at_location"
    return ProposalCandidateFactCreate(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        contract_version=profile.contract_version,
        claim_id=claim_id,
        chapter_index=chapter.chapter_index,
        intra_chapter_seq=0,
        subject_ref=character_ref,
        predicate="present_at_location",
        object_ref_or_value={
            "chapter_index": chapter.chapter_index,
            "character_name": character_name,
            "location_ref": location_ref,
            "location_name": location_name,
            "evidence": evidence[:180],
            "source": "deterministic_cooccurrence",
            "evidence_span": {
                "ref": f"chapter:{chapter.chapter_index}",
                "text": evidence[:220],
            },
            "quality": candidate_quality(signal="cooccurrence", confidence_band="medium"),
        },
        claim_layer="truth",
        evidence_refs=[f"chapter:{chapter.chapter_index}"],
        authority_type=DERIVED,
        confidence=0.78,
        notes=f"自动抽取：{character_name} 与 {location_name} 在同一句场景中共现。",
    )


def candidate_from_entity_mention(
    *,
    project_id: str,
    profile: ProjectProfileVersion,
    chapter: ChapterContent,
    entity_ref_value: str,
    entity_name: str,
    entity_type: str,
    mention_count: int,
) -> ProposalCandidateFactCreate:
    claim_id = f"claim.chapter.{chapter.chapter_index}.{slug(entity_ref_value)}.mentioned_in_chapter"
    return ProposalCandidateFactCreate(
        project_id=project_id,
        project_profile_version_id=profile.id,
        profile_version=profile.version,
        contract_version=profile.contract_version,
        claim_id=claim_id,
        chapter_index=chapter.chapter_index,
        intra_chapter_seq=0,
        subject_ref=entity_ref_value,
        predicate="mentioned_in_chapter",
        object_ref_or_value={
            "chapter_index": chapter.chapter_index,
            "entity_name": entity_name,
            "entity_type": entity_type,
            "mention_count": mention_count,
            "source": "deterministic_mention",
            "evidence_span": {
                "ref": f"chapter:{chapter.chapter_index}",
                "matched_names": [entity_name],
            },
            "quality": candidate_quality(signal="entity_mention", confidence_band="medium"),
        },
        claim_layer="truth",
        evidence_refs=[f"chapter:{chapter.chapter_index}"],
        authority_type=DERIVED,
        confidence=0.75,
        notes=f"自动抽取：{entity_name} 在第{chapter.chapter_index}章被提及 {mention_count} 次。",
    )


def chapter_event_summary(chapter: ChapterContent) -> str:
    sentences = chapter_sentences(chapter.content or "")
    if not sentences:
        return ""
    return "。".join(sentences[:2])[:220]


def candidate_quality(*, signal: str, confidence_band: str, review_priority: str = "normal") -> dict[str, str]:
    return {
        "signal": signal,
        "confidence_band": confidence_band,
        "review_priority": review_priority,
    }
