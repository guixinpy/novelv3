from dataclasses import dataclass
from typing import Any, Iterable


_CHINESE_DAY_OFFSETS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
}


@dataclass(frozen=True)
class StoryTimePoint:
    chapter_index: int
    intra_chapter_seq: int = 0
    day_offset: int = 0

    def sort_key(self) -> tuple[int, int, int]:
        return (self.chapter_index, self.day_offset, self.intra_chapter_seq)


@dataclass(frozen=True)
class AnchorRecord:
    anchor_id: str
    chapter_index: int | None
    intra_chapter_seq: int = 0
    world_time_label: str = ""
    relative_to_anchor_ref: str | None = None


def normalize_story_time(
    *,
    chapter_index: int | None = None,
    intra_chapter_seq: int = 0,
    reference: StoryTimePoint | None = None,
    expression: str | None = None,
) -> StoryTimePoint:
    if expression is None:
        if chapter_index is None:
            if reference is None:
                raise ValueError("chapter_index or reference is required")
            return reference
        return StoryTimePoint(
            chapter_index=chapter_index,
            intra_chapter_seq=intra_chapter_seq,
            day_offset=0,
        )

    if not isinstance(expression, str):
        raise TypeError("expression must be a string")
    if reference is None:
        raise ValueError("reference is required for relative expressions")

    normalized_expression = expression.strip()
    if normalized_expression == "同章稍后":
        return StoryTimePoint(
            chapter_index=reference.chapter_index,
            intra_chapter_seq=reference.intra_chapter_seq + 1,
            day_offset=reference.day_offset,
        )
    if normalized_expression == "次日":
        return StoryTimePoint(
            chapter_index=reference.chapter_index,
            intra_chapter_seq=reference.intra_chapter_seq,
            day_offset=reference.day_offset + 1,
        )
    if normalized_expression.endswith("天后"):
        raw_days = normalized_expression[:-2]
        if raw_days.isdigit():
            day_offset = int(raw_days)
        else:
            day_offset = _CHINESE_DAY_OFFSETS.get(raw_days, 0)
        if day_offset <= 0:
            raise ValueError(f"unsupported time expression: {expression}")
        return StoryTimePoint(
            chapter_index=reference.chapter_index,
            intra_chapter_seq=reference.intra_chapter_seq,
            day_offset=reference.day_offset + day_offset,
        )

    raise ValueError(f"unsupported time expression: {expression}")


def compare_story_time(left: StoryTimePoint, right: StoryTimePoint) -> int:
    if not isinstance(left, StoryTimePoint) or not isinstance(right, StoryTimePoint):
        raise TypeError("hard comparisons require normalized StoryTimePoint inputs")
    if left.sort_key() < right.sort_key():
        return -1
    if left.sort_key() > right.sort_key():
        return 1
    return 0


def build_anchor_time_index(anchors: Iterable[AnchorRecord | Any]) -> dict[str, StoryTimePoint]:
    pending = {
        record.anchor_id: record
        for record in (_coerce_anchor_record(anchor) for anchor in anchors)
    }
    resolved: dict[str, StoryTimePoint] = {}

    while pending:
        progressed = False
        for anchor_id, anchor in sorted(pending.items()):
            if anchor.relative_to_anchor_ref:
                reference = resolved.get(anchor.relative_to_anchor_ref)
                if reference is None:
                    continue
                expression = anchor.world_time_label.strip()
                if expression:
                    resolved[anchor_id] = normalize_story_time(
                        reference=reference,
                        expression=expression,
                    )
                elif anchor.chapter_index is not None:
                    resolved[anchor_id] = normalize_story_time(
                        chapter_index=anchor.chapter_index,
                        intra_chapter_seq=anchor.intra_chapter_seq,
                    )
                else:
                    resolved[anchor_id] = reference
            else:
                if anchor.chapter_index is None:
                    raise ValueError(f"anchor {anchor_id} is missing chapter_index")
                resolved[anchor_id] = normalize_story_time(
                    chapter_index=anchor.chapter_index,
                    intra_chapter_seq=anchor.intra_chapter_seq,
                )
            del pending[anchor_id]
            progressed = True
            break
        if not progressed:
            unresolved = ", ".join(sorted(pending))
            raise ValueError(f"unresolved anchor references: {unresolved}")
    return resolved


def _coerce_anchor_record(anchor: AnchorRecord | Any) -> AnchorRecord:
    if isinstance(anchor, AnchorRecord):
        return anchor
    return AnchorRecord(
        anchor_id=getattr(anchor, "anchor_id"),
        chapter_index=getattr(anchor, "chapter_index"),
        intra_chapter_seq=getattr(anchor, "intra_chapter_seq", 0),
        world_time_label=getattr(anchor, "world_time_label", "") or "",
        relative_to_anchor_ref=getattr(anchor, "relative_to_anchor_ref", None),
    )
