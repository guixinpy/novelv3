# Longform Scale Phase 86: Scoped Snapshot Projection Source

## Goal

Avoid loading future world-model event and fact rows when building a chapter snapshot. For long projects, snapshot views should only read rows that can affect the requested chapter.

## Change

- Added a SQL-level regression test for chapter snapshot source loading.
- Passed `chapter_index` as `max_chapter_index` into the projection source loader for `chapter_snapshot`.
- Filtered `WorldEvent` rows to `chapter_index <= max_chapter_index`.
- Filtered `WorldFactClaim` rows to timeless claims or `chapter_index <= max_chapter_index`.
- Kept anchors unbounded so facts with future `valid_to_anchor_id` can still evaluate active windows correctly.

## Verification

- Red: `python -m pytest backend/tests/test_world_projection_service.py -k "filters_future_event_and_fact_rows" -q --basetemp .tmp/pytest`
- Green: `python -m pytest backend/tests/test_world_projection_service.py -k "filters_future_event_and_fact_rows" -q --basetemp .tmp/pytest`
- Projection service suite: `python -m pytest backend/tests/test_world_projection_service.py -q --basetemp .tmp/pytest`
- Frontend API suite: `python -m pytest backend/tests/test_world_frontend_api.py -q --basetemp .tmp/pytest`
