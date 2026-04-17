from app.models import Setup, ChapterContent


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
