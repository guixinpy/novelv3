# Phase 250 - Query-Aware Evidence Guard in Scale Smoke

## Goal

Make the million-word smoke test prove that query-aware retrieval produced
usable, explainable evidence. The previous report only showed that the
`query_aware_retrieval` section existed, which could hide empty or unexplained
retrieval results.

## TDD Evidence

- RED:
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q -k "smoke_reports_memory_retrieval_and_resume_progress or without_query_aware_retrieval_evidence"`
  - Failed because the smoke report had no `query_aware_retrieval_item_count`
    and the CLI returned `0` for an empty query-aware retrieval section.
- GREEN:
  - Same focused command passed with `2 passed`.
  - `backend\.venv\Scripts\python.exe -m pytest backend/tests/test_longform_scale.py -q`
    passed with `43 passed`.

## Changes

- Compacted longform context smoke output now reports:
  - query-aware retrieval item count,
  - source types,
  - max returned chapter index,
  - explanation availability,
  - future/out-of-range evidence count.
- The smoke CLI now fails when query-aware retrieval returns no items, lacks
  explanations, or includes future/out-of-range items.

## Scale Smoke

- Command:
  - `backend\.venv\Scripts\python.exe scripts\longform_scale_smoke.py --chapters 1000 --words-per-chapter 1000 --cleanup`
- Result:
  - `total_words`: 1,000,000
  - `elapsed_ms`: 8,634
  - `query_aware_retrieval_item_count`: 6
  - `query_aware_retrieval_source_types`: `chapter`
  - `query_aware_retrieval_max_chapter_index`: 232
  - `query_aware_retrieval_has_explanations`: true
  - `query_aware_retrieval_out_of_range_count`: 0

## Verification Evidence

Fresh verification before committing this phase:

- `backend\.venv\Scripts\python.exe -m pytest backend/tests -q` passed with `647 passed`.
- `npm run build` passed.
- `npm run test:unit -- --run` passed with `415 passed`.
- `git diff --check` passed.
- DeepSeek key scan returned `NO_MATCH`.
