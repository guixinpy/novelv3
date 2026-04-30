"""Text mention helpers shared by deterministic extractors."""

from __future__ import annotations


def count_non_overlapping_mentions(*, text: str, names: list[str]) -> int:
    normalized_text = text or ""
    if not normalized_text:
        return 0
    ordered_names = sorted(unique_non_empty(names), key=lambda item: (-len(item), item))
    occupied = [False] * len(normalized_text)
    count = 0
    for name in ordered_names:
        start = normalized_text.find(name)
        while start >= 0:
            end = start + len(name)
            if not any(occupied[start:end]):
                for index in range(start, end):
                    occupied[index] = True
                count += 1
            start = normalized_text.find(name, start + 1)
    return count


def unique_non_empty(raw_names: list[object]) -> list[str]:
    names: list[str] = []
    seen: set[str] = set()
    for raw_name in raw_names:
        name = str(raw_name or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names
