import re

from app.models import ChapterContent


class L1RuleExtractor:
    def extract(self, chapter: ChapterContent, characters: list[dict]) -> list[dict]:
        facts = []
        facts.extend(self.extract_character_mentions(chapter, characters))
        facts.extend(self.extract_locations(chapter))
        return facts

    def extract_character_mentions(self, chapter: ChapterContent, characters: list[dict]) -> list[dict]:
        facts = []
        for char in characters:
            name = char.get("name")
            if not name:
                continue
            names = _unique_names([name, *(char.get("aliases") or []), *(char.get("names") or [])])
            count = sum(len(re.findall(re.escape(candidate_name), chapter.content or "")) for candidate_name in names)
            if count > 0:
                facts.append({
                    "type": "character_presence",
                    "subject": name,
                    "subject_ref": char.get("ref"),
                    "attribute": "mentioned",
                    "new_value": count,
                    "chapter_index": chapter.chapter_index,
                    "matched_names": names,
                })
        return facts

    def extract_locations(self, chapter: ChapterContent) -> list[dict]:
        facts = []
        return facts


def _unique_names(raw_names: list[str]) -> list[str]:
    names = []
    seen = set()
    for raw_name in raw_names:
        name = str(raw_name or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names
