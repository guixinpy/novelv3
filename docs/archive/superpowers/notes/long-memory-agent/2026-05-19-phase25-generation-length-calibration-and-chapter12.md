# Phase 25 Generation Length Calibration and Chapter 12 Report

## Summary

Phase25 fixed a Writing Agent length calibration issue and continued the dogfood novel to Chapter 12.

Completed:

- Split recent length drift from historical length debt.
- Kept historical over/under target counts visible in `length_policy`.
- Stopped old chapter length debt from injecting misleading "recent drift" generation feedback.
- Added regression coverage for old over-target and old under-target debt.
- Generated Chapter 12 `旧军牌的回声`.
- Repaired Chapter 12 after dogfood quality review found hard continuity issues.
- Refreshed longform memory/retrieval after manual content repairs.
- Re-reviewed and re-analyzed Chapter 12 with no remaining blockers or pending world-model proposals.

## Code Changes

- Modified `backend/app/services/writing_agent/run_service.py`.
  - Added `LENGTH_POLICY_RECENT_WINDOW = 5`.
  - Added `LENGTH_POLICY_REPEATED_DRIFT_THRESHOLD = 3`.
  - Added `_length_drift_snapshot`.
  - `_length_drift_policy` now uses only the recent window for repeated-drift decisions.
  - `_length_policy_check` now returns both recent drift counts and historical debt counts.
- Modified `backend/tests/test_writing_agent_runs.py`.
  - Added coverage that old over-target history does not trigger preflight drift warnings when recent chapters are clean.
  - Added coverage that old over-target history does not inject generation feedback.
  - Added coverage that old under-target history does not inject generation feedback.

## RED/GREEN Evidence

RED:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preflight_keeps_historical_length_debt_out_of_recent_drift_warning tests\test_writing_agent_runs.py::test_agent_generate_chapter_ignores_old_over_target_debt_when_recent_window_is_clean -q
```

Result: `2 failed`; preflight still returned `review_required`, and generation command args still contained `近期章节连续偏长`.

GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preflight_keeps_historical_length_debt_out_of_recent_drift_warning tests\test_writing_agent_runs.py::test_agent_generate_chapter_ignores_old_over_target_debt_when_recent_window_is_clean -q
```

Result: `2 passed in 0.30s`.

Recent-drift regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_chapter_length_decision_flags_repeated_over_target_drift tests\test_writing_agent_runs.py::test_agent_preflight_warns_when_repeated_over_target_drift_requires_review tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_over_target_drift tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_under_target_drift -q
```

Result: `4 passed in 0.46s`.

Post-review symmetric debt coverage:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py::test_agent_preflight_keeps_historical_length_debt_out_of_recent_drift_warning tests\test_writing_agent_runs.py::test_agent_generate_chapter_ignores_old_over_target_debt_when_recent_window_is_clean tests\test_writing_agent_runs.py::test_agent_generate_chapter_ignores_old_under_target_debt_when_recent_window_is_clean tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_over_target_drift tests\test_writing_agent_runs.py::test_agent_generate_chapter_appends_length_feedback_after_repeated_under_target_drift -q
```

Result: `5 passed in 0.48s`.

T2 backend verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_world_proposals.py -q
```

Result: `146 passed in 10.48s`.

## Dogfood Evidence

Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`.

### Preflight and Outline

- Preflight run: `9edd185e-c71f-47c0-a4ba-c9fb1462c7c6`.
- Result: blocked because Chapter 12 outline was missing.
- Length policy in preflight:
  - `status=ready`.
  - `recent_chapter_indexes=[7,8,9,10,11]`.
  - `recent_over_target_count=0`.
  - `recent_under_target_count=0`.
  - `historical_over_target_count=4`.
  - `historical_under_target_count=1`.
- Outline expansion run: `9eaf4140-f261-405c-bbeb-39fae4e9dd5d`.
- Result: added Chapter 12 outline.

### Chapter 12 Generation

- Generation/review/analyze run: `87c09b64-ce56-4757-a751-e4196f7c992f`.
- Generated Chapter 12 at 2739 words.
- Length decision: `over`, `accept_with_warning`.
- Athena same-run analysis created 5 proposal items.
- Quality review found no blockers, but warned about over-target length and pending world-model proposals.

### World-Model Proposal Closure

- Draft decisions run: `015edf71-e941-4b7b-b24b-2b95fc326487`.
- Drafted 5 guarded decisions:
  - 1 `event_summary` marked uncertain.
  - 2 `mentioned_in_chapter` rejected as textual mention metadata.
  - 2 `presence_count` rejected as diagnostic extraction metadata.
- Apply run: `56bc48e5-6409-4f9a-82df-10f29e0cb4d9`.
- Result: applied 5 decisions, queue ready for next writing step.

### Compression and Review

- Compression/review run: `79f45380-a704-4ab4-98cd-2251ff00188a`.
- Chapter 12 compressed from 2739 to 2298 words.
- `deterministic_trim_applied=True`.
- Revision: `54c13f79-116f-4de0-a305-48e4e22357f3`.
- Review after compression: ready, 0 findings.

### Subagent Dogfood Quality Review

Quality-review subagent found hard continuity issues after compression:

- Chapter 4 used Gu Yan's military tag as `N-017`, while Chapter 12 treated `N-07` as the tag number.
- Fog-disaster date references were inconsistent.
- Chapter 11 ending to Chapter 12 opening lacked a trust/positioning bridge.
- Chapter 12 ending SMS sent Lin Shen back to an unsafe warehouse.

Repairs applied:

- Canonicalized the "three days before fog disaster" date to `2045年8月9日` in Chapters 5, 11, and 12.
- Kept Gu Yan's military tag number as `N-017`.
- Reframed `N-07` as a fog-crystal-revealed experiment code, not the military tag number.
- Added a short Chapter 12 opening bridge that makes Lin Shen's location message a deliberate test.
- Changed the ending SMS to warn Lin Shen not to come to the unsafe warehouse.
- Tightened Chapter 12 back to 2300 words.

Post-repair checks:

- Chapter 12 review run: `08e4e68c-7cac-4851-8b01-3d97e2233334`.
- Result: ready, 0 findings, 0 blockers.
- Re-analysis run: `fd8b4a85-3914-4a81-8550-f66ebe7154db`.
- Result: completed, 0 new proposal items, 4 duplicates skipped.
- Pending world-model proposals: 0.
- Longform maintenance repair refreshed Chapters 5-12; remaining issue count: 0.

## Current Novel State

Fresh database check after repairs:

- Project current word count: 29893.
- Pending actionable world-model proposals: 0.
- Longform maintenance: current.
- Chapter 1 `雾中回声`: 3735.
- Chapter 2 `第2章`: 3511.
- Chapter 3 `雾中童谣`: 3080.
- Chapter 4 `顾衍的警告`: 1861.
- Chapter 5 `空白信的秘密`: 2482.
- Chapter 6 `黑市雾晶`: 2165.
- Chapter 7 `苏晚晴的梦境`: 2025.
- Chapter 8 `废弃实验室`: 2142.
- Chapter 9 `暗河引路`: 2015.
- Chapter 10 `空白信纸`: 2292.
- Chapter 11 `隐形墨水`: 2285.
- Chapter 12 `旧军牌的回声`: 2300.

## Code Review

Code-review subagent reviewed only the Phase25 diff and reported no blocking issues.

Non-blocking suggestion addressed during the phase:

- Added symmetric coverage for old under-target debt not polluting a clean recent window.

## Decisions

- Recent repeated drift is defined as at least 3 drifted chapters in the latest 5 generated chapters.
- Historical debt remains visible in the agent output but does not trigger generation feedback by itself.
- Old over-target Chapters 1-3 and 5 remain a known cleanup debt and were not compressed in this phase.
- Chapter content repairs were recorded through version snapshots and followed by longform memory repair.

## Phase26 Recommendation

Continue with Chapter 13 only after one small continuity improvement:

- Add an automated or semi-automated continuity review pass that can compare high-salience anchors across chapters, especially dates, identifiers, and named-item meanings.

Then proceed with:

- Chapter 13 preflight and generation.
- Continue monitoring recent-window length drift after Chapter 12 landed exactly at the upper bound.
- Plan a separate cleanup phase for older length debt in Chapters 1-5.
