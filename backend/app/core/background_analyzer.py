import json
import logging

from sqlalchemy import text

from app.core.checkers import ForeshadowingChecker, LocationChecker, RelationshipChecker, TimelineChecker
from app.core.consistency_checker import ConsistencyChecker
from app.core.cross_validator import CrossValidator
from app.core.l1_extractor import L1RuleExtractor
from app.core.l2_extractor import L2LLMExtractor
from app.db import SessionLocal
from app.models import ChapterContent, ConsistencyCheck, ExtractedFact, Setup

logger = logging.getLogger(__name__)


class BackgroundAnalyzer:
    def __init__(self):
        self.l1 = L1RuleExtractor()
        self.l2 = L2LLMExtractor()
        self.cross = CrossValidator()
        self.char_checker = ConsistencyChecker()
        self.loc_checker = LocationChecker()
        self.time_checker = TimelineChecker()
        self.rel_checker = RelationshipChecker()
        self.fs_checker = ForeshadowingChecker()

    async def run_deep_check(self, project_id: str, chapter_index: int) -> dict:
        db = SessionLocal()
        try:
            chapter = db.query(ChapterContent).filter(
                ChapterContent.project_id == project_id,
                ChapterContent.chapter_index == chapter_index,
            ).first()
            if not chapter:
                return {"issues": [], "error": "Chapter not found"}

            setup = db.query(Setup).filter(Setup.project_id == project_id).first()
            characters = setup.characters or [] if setup else []

            l1_facts = self.l1.extract(chapter, characters)
            l2_facts = await self.l2.extract(chapter.content or "")

            cross_result = self.cross.validate(l1_facts, l2_facts)

            all_facts = l1_facts + cross_result["confirmed"] + cross_result["pending"]

            issues = []
            issues.extend(self.char_checker.check(project_id, chapter, setup))
            issues.extend(self.loc_checker.check(chapter, all_facts))
            issues.extend(self.time_checker.check(chapter, all_facts))
            issues.extend(self.rel_checker.check(chapter, all_facts, characters))

            overdue_foreshadowing = _load_overdue_foreshadowing_candidates(db, project_id, chapter_index)
            if overdue_foreshadowing:
                issues.extend(self.fs_checker.check(project_id, chapter_index, overdue_foreshadowing))

            for conflict in cross_result["conflicts"]:
                issues.append({
                    "project_id": project_id,
                    "chapter_index": chapter_index,
                    "checker_name": "CrossValidator",
                    "severity": "warn",
                    "subject": conflict["l2"].get("subject", ""),
                    "description": conflict["reason"],
                    "evidence": str(conflict),
                    "suggested_fix": "人工确认哪个提取结果正确",
                    "status": "pending",
                })

            db.query(ConsistencyCheck).filter(
                ConsistencyCheck.project_id == project_id,
                ConsistencyCheck.chapter_index == chapter_index,
            ).delete()
            for issue in issues:
                db.add(ConsistencyCheck(**issue))

            for fact in all_facts:
                db.add(ExtractedFact(
                    project_id=project_id,
                    chapter_index=chapter_index,
                    type=fact.get("type", "unknown"),
                    source="l2_llm" if fact.get("validation") else "l1_rule",
                    confidence=fact.get("confidence", 1.0),
                    data=fact,
                    evidence={"text": fact.get("evidence", "")},
                    validation=fact.get("validation"),
                ))

            db.commit()
            logger.info("Deep check completed", extra={"project_id": project_id, "chapter_index": chapter_index, "issues": len(issues)})
            return {"issues": issues, "facts_count": len(all_facts)}
        except Exception as e:
            logger.error("Deep check failed", extra={"error": str(e)})
            return {"issues": [], "error": str(e)}
        finally:
            db.close()


def _load_overdue_foreshadowing_candidates(db, project_id: str, chapter_index: int, *, limit: int = 500) -> list[dict]:
    rows = (
        db.execute(
            text(
                """
                SELECT item.value AS value
                FROM storylines, json_each(storylines.foreshadowing) AS item
                WHERE storylines.id = (
                    SELECT id
                    FROM storylines
                    WHERE project_id = :project_id
                    ORDER BY updated_at DESC
                    LIMIT 1
                )
                AND COALESCE(NULLIF(json_extract(item.value, '$.status'), ''), 'planted') = 'planted'
                AND json_extract(item.value, '$.resolved_chapter') IS NOT NULL
                AND :chapter_index > CAST(json_extract(item.value, '$.resolved_chapter') AS INTEGER) + 2
                ORDER BY CAST(item.key AS INTEGER)
                LIMIT :limit
                """
            ),
            {"project_id": project_id, "chapter_index": chapter_index, "limit": limit},
        )
        .mappings()
        .all()
    )
    candidates: list[dict] = []
    for row in rows:
        value = row["value"]
        if isinstance(value, dict):
            candidates.append(value)
            continue
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                continue
            if isinstance(decoded, dict):
                candidates.append(decoded)
    return candidates
