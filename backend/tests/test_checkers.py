from unittest.mock import MagicMock

from app.core.checkers import ForeshadowingChecker, RelationshipChecker


def test_foreshadowing_checker_detects_unresolved():
    checker = ForeshadowingChecker()
    foreshadowing = [
        {"hint": "神秘符号", "planted_chapter": 1, "resolved_chapter": 5, "status": "planted"},
    ]
    issues = checker.check("proj1", 10, foreshadowing)
    assert len(issues) == 1
    assert issues[0]["checker_name"] == "ForeshadowingChecker"


def test_foreshadowing_checker_no_issue_when_within_range():
    checker = ForeshadowingChecker()
    foreshadowing = [
        {"hint": "神秘符号", "planted_chapter": 1, "resolved_chapter": 5, "status": "planted"},
    ]
    issues = checker.check("proj1", 5, foreshadowing)
    assert len(issues) == 0


def test_relationship_checker():
    checker = RelationshipChecker()
    chapter = MagicMock()
    chapter.project_id = "test"
    chapter.chapter_index = 1
    facts = [{"type": "relationship_change", "subject": "A", "attribute": "enemy", "new_value": "B", "evidence": "test"}]
    characters = [{"name": "A", "relationships": [{"target": "B", "type": "friend"}]}]
    issues = checker.check(chapter, facts, characters)
    assert len(issues) == 1
