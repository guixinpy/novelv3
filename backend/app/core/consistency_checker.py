from app.models import Setup, ChapterContent
from app.core.l1_extractor import L1RuleExtractor


class ConsistencyChecker:
    def __init__(self):
        self.extractor = L1RuleExtractor()

    def check(self, project_id: str, chapter: ChapterContent, setup: Setup) -> list[dict]:
        issues = []
        characters = setup.characters or [] if setup else []

        facts = self.extractor.extract(chapter, characters)
        issues.extend(self._check_character_state(chapter, facts, characters))
        return issues

    def _check_character_state(self, chapter: ChapterContent, facts: list[dict], characters: list[dict]) -> list[dict]:
        issues = []
        status_map = {c.get("name"): c.get("character_status", "alive") for c in characters}
        for fact in facts:
            if fact["type"] == "character_presence":
                name = fact["subject"]
                if status_map.get(name) == "dead":
                    issues.append({
                        "project_id": chapter.project_id,
                        "chapter_index": chapter.chapter_index,
                        "checker_name": "CharacterStateChecker",
                        "severity": "fatal",
                        "subject": name,
                        "description": f"已死亡角色 {name} 在本章再次出现",
                        "evidence": f"{name} 出现在第 {chapter.chapter_index} 章",
                        "suggested_fix": "确认角色状态或修改出场安排",
                        "status": "pending",
                    })
        return issues
