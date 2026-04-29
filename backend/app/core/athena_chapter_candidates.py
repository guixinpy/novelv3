"""Chapter-to-world proposal candidate builders for Athena."""

from __future__ import annotations

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
