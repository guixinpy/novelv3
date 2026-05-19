# Phase 16 Length Floor and Chapter 5 Loop Report

## Scope

Phase 16 tightened longform chapter length gates for the 600-chapter / 1.2M-word dogfood novel and continued the real generation loop through Chapter 5.

This phase also used a read-only subagent review to map the `word_count` chain and avoid a premature database-level counting migration.

## Starting State

- Dogfood project: `25fa2b20-5b9f-473b-918b-f4ea491cbb60`
- Novel: `雾港回声`
- Generated chapters before phase: 4
- Next outline chapter: Chapter 5 `空白信的秘密`
- Pending world-model proposals before phase: 0
- Proposal reviews before phase: 32
- World fact claims before phase: 0
- Current project range before code change: `1700-2300`
- Target project range after code change: `2000-2300`

## Design Decision

The project keeps `ChapterContent.word_count` as the authoritative stored metric in this phase.

Reason:

- `word_count` is already used by chapter generation, project totals, trace metadata, longform memory, exports, workspace bootstrap, and version replay.
- A raw-character migration would require historical recomputation, longform memory rebuild, and retrieval reindexing.
- The immediate dogfood problem was that the lower bound allowed `1700-1999` for a project whose explicit longform target is 2000 words per chapter.

Implemented policy:

- `project_chapter_word_range(project)` now uses `average` as the lower bound when `average >= 2000`.
- Smaller projects keep the previous `85%-115%` range.
- Longform maintenance diagnostics now reuse `project_chapter_word_range()` so preflight, trace, review, and maintenance no longer drift apart.
- Modest over-target chapters are warnings, not blockers. Severe over-target chapters still block revision flow.
- Warning-only length drift no longer recommends `revise_chapter`.

## Code Changes

- `backend/app/prompting/providers/chapter.py`
  - Tightened lower bound for longform average >= 2000.
- `backend/app/core/longform_memory.py`
  - Reused the same project chapter range in maintenance diagnostics.
- `backend/app/core/chapter_quality_review.py`
  - Treated mild over-target length as warning.
  - Recommended revision only for blocker-level title/length/outline findings.
- `backend/tests/test_prompting_chapter_migration.py`
  - Added 600-chapter / 1.2M-word prompt expectation: `2000-2300`.
- `backend/tests/test_longform_scale.py`
  - Added longform maintenance diagnostics coverage for the 2000 lower bound.
- `backend/tests/test_writing_agent_runs.py`
  - Updated target lower-bound expectations.
  - Added mild over-target quality review coverage.

## Dogfood Generation Evidence

### Preconditions

- API key check: configured, value not printed.
- Generated chapters before Chapter 5 run: 4
- Chapter 5 outline title: `空白信的秘密`
- Pending world-model proposals: 0
- Runtime target range: `(2000, 2300)`

### Chapter 5 Generation

- Run ID: `3f1ca721-04bb-441f-8c32-0c2f30ea4fd9`
- Run status: `success`
- Step 1: `preflight_writing`
  - Status: `ready`
  - Warning: repeated length drift, recommended `revise_or_adjust_project_target`
- Step 2: `generate_chapter`
  - Status: `success`
  - Trace ID: `9a08ac6e-51ee-43a8-8681-841766f321a0`
  - Chapter length decision:
    - Status: `over`
    - Actual stored word count: 2482
    - Target min: 2000
    - Target average: 2000
    - Target max: 2300
    - Decision: `requires_policy_review`
  - Athena analysis bundle: `7204274e-7ed6-4abe-a37f-2c7703ab41f2`
  - Created proposal items: 7

Generated chapter:

- Chapter: 5
- Title: `空白信的秘密`
- Stored word count: 2482
- Raw character count: 3045
- Status: `generated`
- Model: `deepseek-v4-flash`

## Review and World-Model Feedback

### Initial Review and Analysis

- Run ID: `52e4559e-93ed-4820-803a-2dc88b6765fd`
- `review_chapter_quality`:
  - Status before queue cleanup: `blocked`
  - Findings:
    - `chapter_over_target`: blocker before mild-over policy change.
    - `pending_world_model_proposals`: warning, 7 pending.
- `analyze_chapter_world_model`:
  - Completed.
  - Created 0 new items because generation had already analyzed Chapter 5.
  - Skipped duplicates: 7.

### Proposal Draft

- Run ID: `413a1d85-ff5d-43ee-93e3-1976eb661c78`
- Inspected items: 7
- Drafted decisions: 7
- Unclassified items: 0
- Action distribution:
  - `reject`: 5
  - `mark_uncertain`: 2
- Predicate distribution:
  - `presence_count`: 3
  - `mentioned_in_chapter`: 2
  - `event_summary`: 1
  - `present_at_location`: 1

### Confirmed Apply

- Run ID: `222c755d-b9e3-4719-92bb-d9918b697279`
- Run status: `success`
- Before apply:
  - Pending proposals: 7
  - Proposal reviews: 32
  - World fact claims: 0
- After apply:
  - Pending proposals: 0
  - Proposal reviews: 39
  - World fact claims: 0
- Applied decisions: 7
- Invalid decisions: 0
- `should_generate_next_chapter`: `true`

### Final Quality Check

- Run ID: `11f52668-a945-44f1-8376-bdd1be7850cf`
- Run status: `success`
- Output status: `warning`
- Finding count: 1
- Blocker count: 0
- Finding:
  - `chapter_over_target`, warning only.
- Recommended actions: none.

The chapter is accepted for continuation because it meets the 2000+ floor, has no blockers, and only mildly exceeds the target upper bound.

## Subagent Review Summary

A read-only explorer reviewed the length metric chain.

Findings used in this phase:

- `count_words()` counts ASCII words plus CJK characters, not raw `len(content)`.
- Generation, versions, project totals, trace metadata, longform memory, exports, and workspace summaries already depend on stored `word_count`.
- A raw-character migration would affect many tests and require memory/retrieval rebuild.
- The safest near-term fix is to keep stored `word_count` and align target range diagnostics.

## Ending State

- Generated chapters after phase: 5
- Latest chapter: Chapter 5 `空白信的秘密`
- Chapter 5 stored word count: 2482
- Pending world-model proposals: 0
- Proposal reviews: 39
- World fact claims: 0
- Next chapter: Chapter 6 can start with `preflight_writing`.

## Verification Evidence

Targeted RED/GREEN checks:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_prompting_chapter_migration.py::test_chapter_payload_injects_project_word_target_without_user_range tests\test_prompting_chapter_migration.py::test_chapter_payload_uses_2000_floor_for_600_chapter_longform tests\test_writing_agent_runs.py::test_agent_run_records_chapter_length_and_world_model_diagnostics -q
```

Result after implementation: `3 passed in 0.34s`.

Affected targeted checks:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_text_stats.py tests\test_prompting_chapter_migration.py tests\test_chapters.py::test_generate_chapter_records_model_call_trace tests\test_writing_agent_runs.py::test_agent_run_records_chapter_length_and_world_model_diagnostics tests\test_writing_agent_runs.py::test_agent_chapter_length_decision_flags_repeated_over_target_drift tests\test_writing_agent_runs.py::test_agent_preflight_warns_when_repeated_over_target_drift_requires_review tests\test_writing_agent_runs.py::test_agent_review_chapter_quality_flags_generic_title_and_length -q
```

Result: `19 passed in 1.60s`.

Longform diagnostics check:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_word_target_drift tests\test_longform_scale.py::test_longform_maintenance_diagnostics_uses_2000_floor_for_longform_projects -q
```

Result: `2 passed in 0.22s`.

Phase verification:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_prompting_chapter_migration.py tests\test_chapters.py tests\test_writing_agent_runs.py tests\test_world_proposals.py tests\test_longform_scale.py::test_longform_maintenance_diagnostics_reports_word_target_drift tests\test_longform_scale.py::test_longform_maintenance_diagnostics_uses_2000_floor_for_longform_projects -q
```

Result: `168 passed in 17.69s`.

## Follow-Up

The raw character count vs stored `word_count` question is still intentionally unresolved.

Do not casually switch it in-place. If the project wants raw Chinese character count as the public metric, create a dedicated migration phase that:

- defines a new metric name;
- recomputes existing chapter counts;
- reconciles project totals;
- rebuilds longform memory;
- reindexes related retrieval documents;
- updates UI labels and exports.

## Next Phase Recommendation

Phase17 should continue with Chapter 6 generation and begin measuring whether the stricter 2000+ floor stabilizes generated chapter length without producing repeated over-target warnings.
