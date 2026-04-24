from app.models import ChapterContent


class LocationChecker:
    def check(self, chapter: ChapterContent, facts: list[dict]) -> list[dict]:
        issues = []
        locations_by_char: dict[str, list[str]] = {}
        for fact in facts:
            if fact.get("type") == "location_presence":
                char = fact.get("subject", "")
                loc = fact.get("new_value", "")
                if char and loc:
                    locations_by_char.setdefault(char, []).append(loc)

        for char, locs in locations_by_char.items():
            unique = list(set(locs))
            if len(unique) > 1:
                issues.append({
                    "project_id": chapter.project_id,
                    "chapter_index": chapter.chapter_index,
                    "checker_name": "LocationChecker",
                    "severity": "warn",
                    "subject": char,
                    "description": f"{char} 在本章同时出现在多个地点：{'、'.join(unique)}",
                    "evidence": f"检测到 {len(unique)} 个不同地点",
                    "suggested_fix": "确认角色移动逻辑或修正地点描述",
                    "status": "pending",
                })
        return issues


class TimelineChecker:
    def check(self, chapter: ChapterContent, facts: list[dict]) -> list[dict]:
        issues = []
        time_refs = [f for f in facts if f.get("type") == "time_reference"]
        for i in range(1, len(time_refs)):
            prev = time_refs[i - 1]
            curr = time_refs[i]
            if self._is_time_reversal(prev, curr):
                issues.append({
                    "project_id": chapter.project_id,
                    "chapter_index": chapter.chapter_index,
                    "checker_name": "TimelineChecker",
                    "severity": "warn",
                    "subject": "时间线",
                    "description": f"可能存在时间倒流：{prev.get('new_value', '')} → {curr.get('new_value', '')}",
                    "evidence": f"{prev.get('evidence', '')} / {curr.get('evidence', '')}",
                    "suggested_fix": "检查时间顺序是否合理",
                    "status": "pending",
                })
        return issues

    def _is_time_reversal(self, prev: dict, curr: dict) -> bool:
        return False


class RelationshipChecker:
    def check(self, chapter: ChapterContent, facts: list[dict], setup_characters: list[dict]) -> list[dict]:
        issues = []
        relationships = {}
        for char in setup_characters:
            for rel in char.get("relationships", []):
                key = f"{char.get('name')}-{rel.get('target')}"
                relationships[key] = rel.get("type", "unknown")

        for fact in facts:
            if fact.get("type") == "relationship_change":
                subject = fact.get("subject", "")
                target = fact.get("new_value", "")
                key = f"{subject}-{target}"
                if key in relationships and relationships[key] != fact.get("attribute", ""):
                    issues.append({
                        "project_id": chapter.project_id,
                        "chapter_index": chapter.chapter_index,
                        "checker_name": "RelationshipChecker",
                        "severity": "warn",
                        "subject": subject,
                        "description": f"{subject}与{target}的关系发生未铺垫的变化",
                        "evidence": fact.get("evidence", ""),
                        "suggested_fix": "添加关系转变的铺垫或调整设定",
                        "status": "pending",
                    })
        return issues


class ForeshadowingChecker:
    def check(self, project_id: str, chapter_index: int, storyline_foreshadowing: list[dict]) -> list[dict]:
        issues = []
        for fs in storyline_foreshadowing:
            planted = fs.get("planted_chapter")
            resolved = fs.get("resolved_chapter")
            status = fs.get("status", "planted")
            if status == "planted" and resolved and chapter_index > resolved + 2:
                issues.append({
                    "project_id": project_id,
                    "chapter_index": chapter_index,
                    "checker_name": "ForeshadowingChecker",
                    "severity": "info",
                    "subject": fs.get("hint", ""),
                    "description": f"伏笔'{fs.get('hint', '')}'（第{planted}章埋下）预计在第{resolved}章揭示，但当前已到第{chapter_index}章仍未处理",
                    "evidence": f"planted_chapter={planted}, resolved_chapter={resolved}",
                    "suggested_fix": "在后续章节中揭示该伏笔或标记为已放弃",
                    "status": "pending",
                })
        return issues
