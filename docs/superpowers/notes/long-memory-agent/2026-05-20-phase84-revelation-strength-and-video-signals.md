# Phase84 Report: Revelation Strength and Video Signals

## Summary

Phase84 converted two Chapter 26 dogfood findings into Agent-visible review and Athena world-model signals.

Implemented:

- `review_chapter_quality` now emits `revelation_strength_overreach` as a non-blocking warning when a chapter phrases major mystery evidence as hard final truth.
- Athena chapter analysis now extracts five Chapter 26-style high-value plot signals:
  - `historical_video_evidence`
  - `memory_erasure_hypothesis`
  - `parental_involvement_hypothesis`
  - `fog_disaster_cause_hypothesis`
  - `unknown_operator_intervention`
- The proposal review queue treats those predicates as high risk.
- The high-value proposal draft tool treats those predicates conservatively with `mark_uncertain`.

## Files Changed

- `backend/app/core/chapter_quality_review.py`
- `backend/app/core/athena_chapter_candidates.py`
- `backend/app/core/world_proposal_review_queue.py`
- `backend/app/core/high_value_world_proposal_resolution_draft.py`
- `backend/tests/test_writing_agent_runs.py`
- `backend/tests/test_athena_longform.py`
- `backend/tests/test_world_frontend_api.py`
- `docs/superpowers/plans/long-memory-agent/2026-05-20-phase84-revelation-strength-and-video-signals.md`

## Dogfood Target

Live project:

- project id: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- title: `雾港回声`
- chapter: `26`
- chapter title: `深处的回响`
- word count: `2924`

No Chapter 27 generation was performed in this phase.

## Runtime Result

Quality review for Chapter 26:

- status: `warning`
- finding:
  - `revelation_strength_overreach`

Athena analysis after the first implementation created four new high-value items:

- `historical_video_evidence`
- `parental_involvement_hypothesis`
- `fog_disaster_cause_hypothesis`
- `unknown_operator_intervention`

The first live pass did not extract `memory_erasure_hypothesis`. The real Chapter 26 phrased this across adjacent sentences:

- memory fragments surfaced;
- several sentences later everything became blurred;
- then the text said it felt as if something had been erased.

The extractor was adjusted from single-sentence matching to a bounded short-window match. A second live analysis then created:

- `memory_erasure_hypothesis`

All five new high-value Chapter 26 items were processed through guarded proposal handling:

- draft action: `mark_uncertain`
- preview invalid decisions: `0`
- final actionable proposal pressure: `0`

## Validation

Focused red/green tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py::test_agent_review_chapter_quality_warns_on_revelation_strength_overreach backend/tests/test_writing_agent_runs.py::test_agent_review_chapter_quality_allows_hypothesis_framed_revelation backend/tests/test_writing_agent_runs.py::test_agent_draft_high_value_world_proposal_resolution_decisions_reports_without_writes -q
```

Result: `3 passed`

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_longform.py::test_analyze_chapter_creates_historical_video_high_value_candidates -q
```

Result: `1 passed`

Related T1/T2 slices:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_writing_agent_runs.py -k "review_chapter_quality or draft_high_value_world_proposal_resolution_decisions" -q
```

Result: `16 passed, 146 deselected`

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_athena_longform.py -q
```

Result: `17 passed`

```powershell
backend\.venv\Scripts\python.exe -m pytest backend/tests/test_world_frontend_api.py -k "proposal_review_queue" -q
```

Result: `6 passed, 41 deselected`

## Findings

Fixed:

1. Chapter 26's hard revelation wording is now visible as a quality warning rather than silently passing.
2. Historical video evidence and related high-value clues now enter Athena's proposal mechanism.
3. High-value plot signals are kept as uncertain instead of being confirmed into world truth.
4. Memory-erasure phrasing now supports short-window evidence instead of exact single-sentence matching.

Remaining known issues:

- `N-07` and `EV-2045-0812-07` semantic drift warnings still exist from Phase81.
- Chapter 24 -> 25 historical location jump remains a known older continuity issue.

## Next Phase Recommendation

Phase85 should continue the low-detail dogfood loop to Chapter 27:

```text
继续写下一章
```

Before generation, verify Chapter 27 only blocks on missing outline. During review, check whether the new `revelation_strength_overreach` warning affects generation feedback or revision planning enough; if not, add a planner-level revision action such as `soften_revelation_strength`.
