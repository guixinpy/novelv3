"""章节相关工具函数。"""
from __future__ import annotations

import re


def parse_chapter_index(text: str | None) -> int | None:
    """从自然语言文本中解析章节序号，如「第3章」→ 3。"""
    value = (text or "").strip().lower()
    leading_digit_match = re.search(r"^\s*(?:第\s*)?(\d{1,3})(?:\s*章|\s|$)", value)
    if leading_digit_match:
        return int(leading_digit_match.group(1))

    leading_chinese_match = re.search(r"^\s*(?:第\s*)?([零〇一二两三四五六七八九十]{1,4})\s*章", value)
    if leading_chinese_match:
        return _parse_chinese_chapter_number(leading_chinese_match.group(1))

    matches: list[tuple[int, int]] = []
    for m in re.finditer(r"(?:第\s*)?(\d{1,3})\s*章", value):
        matches.append((m.start(), int(m.group(1))))
    if matches:
        matches.sort()
        return matches[-1][1]

    chinese_matches: list[tuple[int, int]] = []
    for m in re.finditer(r"(?:第\s*)?([零〇一二两三四五六七八九十]{1,4})\s*章", value):
        chinese_matches.append((m.start(), _parse_chinese_chapter_number(m.group(1))))
    if chinese_matches:
        chinese_matches.sort()
        return chinese_matches[-1][1]

    return None


_CHINESE_DIGITS: dict[str, int] = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
}


def _parse_chinese_chapter_number(text: str) -> int:
    total = 0
    for ch in text:
        if ch in _CHINESE_DIGITS:
            total = total * 10 + _CHINESE_DIGITS[ch]
    return total


def project_chapter_word_range(project) -> tuple[int, int] | None:
    """项目目标字数/章数 → 每章建议字数范围（v1 绞杀：从 prompting 迁出）。"""
    target_words = int(project.target_word_count or 0)
    target_chapters = int(project.target_chapter_count or 0)
    if target_words <= 0 or target_chapters <= 0:
        return None
    average = max(1, round(target_words / target_chapters))
    if average >= 2000:
        return average, max(average, round(average * 1.5))
    target_min = round(average * 0.85)
    return max(1, target_min), max(1, round(average * 1.15))
