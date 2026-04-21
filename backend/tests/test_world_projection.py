import pytest

from app.core.world_projection import FactRecord, project_snapshot, project_subject_knowledge, project_world_truth
from app.core.world_replay import LedgerEvent
from app.core.world_time_normalizer import AnchorRecord, StoryTimePoint, compare_story_time, normalize_story_time


def test_projection_returns_truth_subject_knowledge_and_chapter_snapshot():
    events = [
        LedgerEvent(
            event_id="evt.hero.introduced",
            event_type="entity_introduced",
            chapter_index=1,
            intra_chapter_seq=1,
            payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"status": "alive"},
            },
            idempotency_key="projection-idem-1",
            timeline_anchor_id="anchor.ch1.s1",
        ),
        LedgerEvent(
            event_id="evt.hero.presence",
            event_type="presence_shifted",
            chapter_index=2,
            intra_chapter_seq=1,
            payload={
                "entity_ref": "char.hero",
                "location_ref": "loc.safehouse",
                "presence_status": "hidden",
                "known_by_refs": ["char.detective"],
            },
            idempotency_key="projection-idem-2",
            timeline_anchor_id="anchor.ch2.s1",
        ),
        LedgerEvent(
            event_id="evt.hero.status",
            event_type="attribute_mutated",
            chapter_index=2,
            intra_chapter_seq=2,
            payload={
                "entity_ref": "char.hero",
                "attribute": "status",
                "value": "wounded",
            },
            idempotency_key="projection-idem-3",
            timeline_anchor_id="anchor.ch2.s2",
        ),
    ]
    facts = [
        FactRecord(
            claim_id="claim.hero.rank.truth",
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="captain",
            claim_layer="truth",
            claim_status="confirmed",
            chapter_index=2,
            intra_chapter_seq=3,
            valid_from_anchor_id="anchor.ch2.s2",
        ),
        FactRecord(
            claim_id="claim.hero.rank.detective",
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="smuggler",
            claim_layer="belief",
            claim_status="confirmed",
            perspective_ref="char.detective",
            chapter_index=2,
            intra_chapter_seq=3,
            valid_from_anchor_id="anchor.ch2.s2",
        ),
    ]
    anchors = [
        AnchorRecord(anchor_id="anchor.ch1.s1", chapter_index=1, intra_chapter_seq=1),
        AnchorRecord(anchor_id="anchor.ch2.s1", chapter_index=2, intra_chapter_seq=1),
        AnchorRecord(anchor_id="anchor.ch2.s2", chapter_index=2, intra_chapter_seq=2),
    ]

    truth = project_world_truth(events=events, facts=facts, anchors=anchors)
    detective_view = project_subject_knowledge(
        subject_ref="char.detective",
        events=events,
        facts=facts,
        anchors=anchors,
    )
    chapter_one_snapshot = project_snapshot(
        events=events,
        facts=facts,
        chapter_index=1,
        anchors=anchors,
    )

    assert truth["entities"]["char.hero"]["attributes"]["status"] == "wounded"
    assert truth["presence"]["char.hero"]["location_ref"] == "loc.safehouse"
    assert truth["facts"]["char.hero"]["rank"] == "captain"

    assert detective_view["facts"]["char.hero"]["rank"] == "smuggler"
    assert detective_view["presence"]["char.hero"]["location_ref"] == "loc.safehouse"

    assert chapter_one_snapshot["entities"]["char.hero"]["attributes"]["status"] == "alive"
    assert "char.hero" not in chapter_one_snapshot["presence"]
    assert chapter_one_snapshot["facts"] == {}


def test_projection_uses_validity_windows_and_order_invariant_fact_priority():
    anchors = [
        AnchorRecord(anchor_id="anchor.ch2.s1", chapter_index=2, intra_chapter_seq=1),
        AnchorRecord(anchor_id="anchor.ch3.s1", chapter_index=3, intra_chapter_seq=1),
        AnchorRecord(anchor_id="anchor.ch4.s1", chapter_index=4, intra_chapter_seq=1),
    ]
    older_expired = FactRecord(
        claim_id="claim.rank.older",
        subject_ref="char.hero",
        predicate="rank",
        object_ref_or_value="cadet",
        claim_layer="truth",
        claim_status="confirmed",
        chapter_index=2,
        intra_chapter_seq=1,
        valid_from_anchor_id="anchor.ch2.s1",
        valid_to_anchor_id="anchor.ch3.s1",
    )
    tie_break_low = FactRecord(
        claim_id="claim.rank.010",
        subject_ref="char.hero",
        predicate="rank",
        object_ref_or_value="captain",
        claim_layer="truth",
        claim_status="confirmed",
        chapter_index=3,
        intra_chapter_seq=1,
        valid_from_anchor_id="anchor.ch3.s1",
    )
    tie_break_high = FactRecord(
        claim_id="claim.rank.011",
        subject_ref="char.hero",
        predicate="rank",
        object_ref_or_value="commander",
        claim_layer="truth",
        claim_status="confirmed",
        chapter_index=3,
        intra_chapter_seq=1,
        valid_from_anchor_id="anchor.ch3.s1",
    )

    first_order = project_world_truth(
        events=[],
        facts=[tie_break_high, older_expired, tie_break_low],
        anchors=anchors,
    )
    second_order = project_world_truth(
        events=[],
        facts=[tie_break_low, older_expired, tie_break_high],
        anchors=anchors,
    )

    assert first_order["facts"]["char.hero"]["rank"] == "commander"
    assert second_order["facts"]["char.hero"]["rank"] == "commander"


def test_snapshot_uses_normalized_anchor_time_for_relative_boundaries():
    anchors = [
        AnchorRecord(anchor_id="anchor.base", chapter_index=8, intra_chapter_seq=2),
        AnchorRecord(
            anchor_id="anchor.same-chapter-later",
            chapter_index=8,
            intra_chapter_seq=2,
            world_time_label="同章稍后",
            relative_to_anchor_ref="anchor.base",
        ),
        AnchorRecord(
            anchor_id="anchor.next-day",
            chapter_index=8,
            intra_chapter_seq=2,
            world_time_label="次日",
            relative_to_anchor_ref="anchor.same-chapter-later",
        ),
    ]
    events = [
        LedgerEvent(
            event_id="evt.hero.introduced",
            event_type="entity_introduced",
            chapter_index=8,
            intra_chapter_seq=2,
            timeline_anchor_id="anchor.base",
            payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"status": "alive"},
            },
            idempotency_key="anchor-idem-1",
        ),
        LedgerEvent(
            event_id="evt.hero.status.later",
            event_type="attribute_mutated",
            chapter_index=8,
            intra_chapter_seq=2,
            timeline_anchor_id="anchor.same-chapter-later",
            payload={
                "entity_ref": "char.hero",
                "attribute": "status",
                "value": "wounded",
            },
            idempotency_key="anchor-idem-2",
        ),
    ]
    facts = [
        FactRecord(
            claim_id="claim.secret.hidden",
            subject_ref="artifact.box",
            predicate="visibility",
            object_ref_or_value="hidden",
            claim_layer="truth",
            claim_status="confirmed",
            chapter_index=8,
            intra_chapter_seq=2,
            valid_from_anchor_id="anchor.base",
            valid_to_anchor_id="anchor.same-chapter-later",
        ),
        FactRecord(
            claim_id="claim.secret.revealed",
            subject_ref="artifact.box",
            predicate="visibility",
            object_ref_or_value="revealed",
            claim_layer="truth",
            claim_status="confirmed",
            chapter_index=8,
            intra_chapter_seq=2,
            valid_from_anchor_id="anchor.same-chapter-later",
        ),
    ]

    before_later = project_snapshot(
        events=events,
        facts=facts,
        chapter_index=8,
        intra_chapter_seq=2,
        as_of_anchor_id="anchor.base",
        anchors=anchors,
    )
    after_later = project_snapshot(
        events=events,
        facts=facts,
        chapter_index=8,
        intra_chapter_seq=2,
        as_of_anchor_id="anchor.same-chapter-later",
        anchors=anchors,
    )

    assert before_later["entities"]["char.hero"]["attributes"]["status"] == "alive"
    assert before_later["facts"]["artifact.box"]["visibility"] == "hidden"
    assert after_later["entities"]["char.hero"]["attributes"]["status"] == "wounded"
    assert after_later["facts"]["artifact.box"]["visibility"] == "revealed"


def test_projection_passes_anchor_story_time_into_replay_ordering():
    anchors = [
        AnchorRecord(anchor_id="anchor.base", chapter_index=6, intra_chapter_seq=1),
        AnchorRecord(
            anchor_id="anchor.later",
            chapter_index=6,
            intra_chapter_seq=1,
            world_time_label="同章稍后",
            relative_to_anchor_ref="anchor.base",
        ),
    ]
    events = [
        LedgerEvent(
            event_id="evt.hero.introduced",
            event_type="entity_introduced",
            chapter_index=6,
            intra_chapter_seq=0,
            timeline_anchor_id="anchor.base",
            payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"status": "alive"},
            },
            idempotency_key="anchor-order-intro",
        ),
        LedgerEvent(
            event_id="evt.a.later",
            event_type="attribute_mutated",
            chapter_index=6,
            intra_chapter_seq=1,
            timeline_anchor_id="anchor.later",
            payload={
                "entity_ref": "char.hero",
                "attribute": "status",
                "value": "wounded",
            },
            idempotency_key="anchor-order-later",
        ),
        LedgerEvent(
            event_id="evt.z.earlier",
            event_type="attribute_mutated",
            chapter_index=6,
            intra_chapter_seq=1,
            timeline_anchor_id="anchor.base",
            payload={
                "entity_ref": "char.hero",
                "attribute": "status",
                "value": "stable",
            },
            idempotency_key="anchor-order-earlier",
        ),
    ]

    truth = project_world_truth(events=events, facts=[], anchors=anchors)

    assert truth["entities"]["char.hero"]["attributes"]["status"] == "wounded"


def test_projection_rejects_missing_anchor_references_instead_of_silent_fallback():
    anchors = [AnchorRecord(anchor_id="anchor.base", chapter_index=7, intra_chapter_seq=1)]
    events = [
        LedgerEvent(
            event_id="evt.hero.introduced",
            event_type="entity_introduced",
            chapter_index=7,
            intra_chapter_seq=1,
            timeline_anchor_id="anchor.typo",
            payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"status": "alive"},
            },
            idempotency_key="anchor-missing-event",
        ),
    ]

    with pytest.raises(ValueError, match="anchor.typo"):
        project_world_truth(events=events, facts=[], anchors=anchors)


def test_projection_materializes_generator_inputs_before_reuse():
    anchors = [AnchorRecord(anchor_id="anchor.base", chapter_index=9, intra_chapter_seq=1)]

    def event_iter():
        yield LedgerEvent(
            event_id="evt.hero.introduced",
            event_type="entity_introduced",
            chapter_index=9,
            intra_chapter_seq=1,
            timeline_anchor_id="anchor.base",
            payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"status": "alive"},
            },
            idempotency_key="generator-event",
        )

    def fact_iter():
        yield FactRecord(
            claim_id="claim.hero.rank",
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="captain",
            claim_layer="truth",
            claim_status="confirmed",
            chapter_index=9,
            intra_chapter_seq=1,
            valid_from_anchor_id="anchor.base",
        )

    truth = project_world_truth(events=event_iter(), facts=fact_iter(), anchors=anchors)

    assert truth["entities"]["char.hero"]["attributes"]["status"] == "alive"
    assert truth["facts"]["char.hero"]["rank"] == "captain"


def test_subject_knowledge_allows_visible_retcon_when_original_event_is_hidden():
    anchors = [
        AnchorRecord(anchor_id="anchor.base", chapter_index=10, intra_chapter_seq=1),
        AnchorRecord(anchor_id="anchor.later", chapter_index=10, intra_chapter_seq=2),
    ]
    events = [
        LedgerEvent(
            event_id="evt.hero.introduced",
            event_type="entity_introduced",
            chapter_index=10,
            intra_chapter_seq=0,
            timeline_anchor_id="anchor.base",
            payload={
                "entity_ref": "char.hero",
                "entity_type": "character",
                "attributes": {"status": "alive"},
            },
            idempotency_key="subject-retcon-intro",
        ),
        LedgerEvent(
            event_id="evt.hero.rank.original",
            event_type="attribute_mutated",
            chapter_index=10,
            intra_chapter_seq=1,
            timeline_anchor_id="anchor.base",
            payload={
                "entity_ref": "char.hero",
                "attribute": "rank",
                "value": "captain",
                "known_by_refs": ["char.other"],
            },
            idempotency_key="subject-retcon-original",
        ),
        LedgerEvent(
            event_id="evt.hero.rank.retcon",
            event_type="retcon_applied",
            chapter_index=10,
            intra_chapter_seq=2,
            timeline_anchor_id="anchor.later",
            supersedes_event_ref="evt.hero.rank.original",
            payload={
                "replacement_event_type": "attribute_mutated",
                "entity_ref": "char.hero",
                "attribute": "rank",
                "value": "commander",
                "known_by_refs": ["char.detective"],
            },
            idempotency_key="subject-retcon-visible",
        ),
    ]

    detective_view = project_subject_knowledge(
        subject_ref="char.detective",
        events=events,
        facts=[],
        anchors=anchors,
    )

    assert detective_view["entities"]["char.hero"]["attributes"]["rank"] == "commander"


def test_subject_knowledge_rejects_bad_anchor_even_when_fact_is_invisible():
    anchors = [AnchorRecord(anchor_id="anchor.base", chapter_index=11, intra_chapter_seq=1)]
    facts = [
        FactRecord(
            claim_id="claim.visible",
            subject_ref="char.hero",
            predicate="rank",
            object_ref_or_value="captain",
            claim_layer="belief",
            claim_status="confirmed",
            perspective_ref="char.detective",
            chapter_index=11,
            intra_chapter_seq=1,
            valid_from_anchor_id="anchor.base",
        ),
        FactRecord(
            claim_id="claim.hidden.bad-anchor",
            subject_ref="char.hero",
            predicate="secret",
            object_ref_or_value="classified",
            claim_layer="belief",
            claim_status="confirmed",
            perspective_ref="char.other",
            chapter_index=11,
            intra_chapter_seq=1,
            valid_from_anchor_id="anchor.typo",
        ),
    ]

    with pytest.raises(ValueError, match="anchor.typo"):
        project_subject_knowledge(
            subject_ref="char.detective",
            events=[],
            facts=facts,
            anchors=anchors,
        )


def test_time_normalizer_supports_minimal_absolute_and_relative_expressions():
    absolute = normalize_story_time(chapter_index=8, intra_chapter_seq=2)
    later_same_chapter = normalize_story_time(reference=absolute, expression="同章稍后")
    next_day = normalize_story_time(reference=absolute, expression="次日")
    three_days_later = normalize_story_time(reference=absolute, expression="三天后")

    assert absolute == StoryTimePoint(chapter_index=8, intra_chapter_seq=2, day_offset=0)
    assert later_same_chapter == StoryTimePoint(chapter_index=8, intra_chapter_seq=3, day_offset=0)
    assert next_day == StoryTimePoint(chapter_index=8, intra_chapter_seq=2, day_offset=1)
    assert three_days_later == StoryTimePoint(chapter_index=8, intra_chapter_seq=2, day_offset=3)
    assert compare_story_time(absolute, later_same_chapter) < 0
    assert compare_story_time(next_day, three_days_later) < 0

    with pytest.raises(TypeError):
        compare_story_time("同章稍后", absolute)
