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
            count = len(re.findall(re.escape(name), chapter.content or ""))
            if count > 0:
                facts.append({
                    "type": "character_presence",
                    "subject": name,
                    "attribute": "mentioned",
                    "new_value": count,
                    "chapter_index": chapter.chapter_index,
                })
        return facts

    def extract_locations(self, chapter: ChapterContent) -> list[dict]:
        facts = []
        return facts
