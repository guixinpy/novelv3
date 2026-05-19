# Phase31 Elastic Length Policy and Chapter 17

## Goal

Phase31 applied the user's clarification that `2000+` is an elastic writing target, not a narrow hard cap. For longform projects whose per-chapter average is at least 2000 words, the backend now treats the average as the lower bound and allows a soft upper range of about 1.5x. The current Dogfood project therefore uses `2000-3000` instead of `2000-2300`.

The phase then continued the real Dogfood loop through Chapter 17.

## Code Change

- Updated `project_chapter_word_range()` in `backend/app/prompting/providers/chapter.py`.
- Longform projects with average chapter length `>= 2000` now return:
  - `target_min_word_count = average`
  - `target_max_word_count = round(average * 1.5)`
- Small synthetic projects keep the prior `0.85x / 1.15x` range so short-unit tests remain useful.
- Updated length diagnostics, review tests, repeated-over-target tests, and stale hand-written trace fixtures to use the new `3000` upper bound where they represent longform `2000+` projects.

## TDD Evidence

RED command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_longform_scale.py::test_longform_maintenance_diagnostics_uses_2000_floor_for_longform_projects tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_accepts_elastic_2000_plus_length -q
```

Observed failure before implementation:

- diagnostics still returned `target_max_word_count == 2300`;
- a 2482-word chapter still produced `chapter_over_target`.

GREEN command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_longform_scale.py::test_longform_maintenance_diagnostics_uses_2000_floor_for_longform_projects tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_accepts_elastic_2000_plus_length -q
```

Result:

- `2 passed in 0.24s`

Focused regression command:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_word_target_drift tests\test_longform_scale.py::test_longform_maintenance_diagnostics_uses_2000_floor_for_longform_projects tests\test_writing_agent_runs.py -q -k "length_decision or length_policy or review_chapter_quality"
```

Initial result after implementation:

- `11 passed, 97 deselected in 0.86s`

Final focused verification after stale trace-fixture cleanup:

- `tests/test_writing_agent_runs.py::test_agent_run_records_chapter_length_and_world_model_diagnostics`
- `tests/test_writing_agent_runs.py::test_agent_skips_analyze_when_generate_step_already_auto_analyzed_same_chapter`
- `tests/test_writing_agent_runs.py::test_agent_chapter_length_decision_flags_repeated_over_target_drift`

Result:

- `3 passed in 0.62s`

Final Phase31 regression:

- `11 passed, 97 deselected in 0.85s`

## Dogfood Chapter 17

Project:

- `25fa2b20-5b9f-473b-918b-f4ea491cbb60`

Length policy check:

- `project_chapter_word_range(project)` returned `[2000, 3000]`.
- Generation prompt guidance includes `本章正文建议控制在2000-3000字`.
- Maintenance diagnostics after Chapter 17:
  - average `2000`
  - min `2000`
  - max `3000`
  - chapter count `17`
  - under-target indexes `[4]`
  - over-target indexes `[1, 2, 3]`
  - within-target count `13`

Chapter 17 outline:

- Outline expansion run: `c4666829-f853-4893-a05d-ee1be5643400`
- Trace: `25de9e42-33e4-47b4-b325-e9c6ca5b928b`
- Title: `废弃医院`
- Manual outline correction kept the N-07 clue uncertain: 苏晚晴 is related to the 7th experiment, not confirmed as N-07.

Preflight:

- Run: `a52b19a2-87ca-4fac-a678-4e27aa0805d5`
- Status: ready
- Checks: previous chapter state card ready, longform maintenance ready, retrieval ready, length policy ready.

Generation and review:

- Generate/review run: `25319a84-dc82-4fe0-8d02-4153e67debb4`
- Generation trace: `3c0a4733-4cdc-4317-8439-f715141e5d60`
- Initial word count: `2575`
- Length decision: `within`, target max `3000`, decision `accept`.
- No length warning was generated.

Content correction:

- Removed over-confirming wording around 苏晚晴 and N-07.
- Base version: `6f5556f9-960c-4606-9624-27c15863b9a8`
- Result version: `4d5376b1-8523-4986-8c64-5bc235b91fcc`
- Final Chapter 17 word count after correction: `2580`

Post-fix review:

- Review run: `9ab4778e-71ce-4e69-9065-b18d3833b82e`
- Remaining quality warning was only pending world-model proposals.

World-model proposal handling:

- Draft run: `5f913492-4be7-4e08-8b58-b2ad678eab63`
- Apply run: `848fd35d-511b-49be-9cf8-241236e096be`
- Applied decisions: `8`
- Pending proposals after apply: `0`

Final review:

- Run: `1ee8d6a8-f036-4ea3-b15d-e3321dba2016`
- `review_chapter_quality`: ready, `finding_count=0`
- `review_chapter_continuity`: ready, `finding_count=0`
- `analyze_chapter_world_model`: created `0`, updated `0`, skipped duplicates `8`
- Pending proposals: `0`
- Longform maintenance: current
- `latest_synced_chapter_index=17`
- Current total word count: `41190`

Longform memory:

- Chapter 17 memory is current.
- Source: `reviewed_event_summary`
- Item: `4cb66cd3-27be-483f-b194-52499086708f`
- Item status: `uncertain`
- Word count: `2580`

## Independent Review

Read-only subagent review: `019e3fb9-76ee-7460-9cf8-241236e096be`

Conclusion:

- No blocking issue found.
- Elastic policy is reflected in diagnostics and quality review.
- Chapter 17 correctly continues Chapter 16.
- N-07 and N-017 remain distinct.
- Pending world-model proposals are cleared.
- Longform memory and maintenance are current.

Non-blocking cleanup from the review:

- Old hand-written trace fixtures in `backend/tests/test_writing_agent_runs.py` still used `target_max_word_count: 2300`. These were updated to `3000` before final verification.

## Next Phase Recommendation

Phase32 should continue the real writing loop from Chapter 18:

- expand Chapter 18 outline;
- preflight before generation;
- generate and review with the elastic `2000-3000` length policy;
- continue treating event summaries as reviewed writing memory, not automatically confirmed world truth;
- keep using targeted T0/T1 verification unless a broad API or frontend contract changes.
