# Phase63 Report: Longform Batch Post Generation Review

## Summary

Phase63 added `review_longform_chapter_batch_execution`, an internal Writing Agent tool that reviews a Phase62-generated batch chapter before the system proceeds.

The tool consumes persisted Phase62 execution evidence, validates that exactly one generated chapter exists, runs quality and continuity reviews, and only runs Athena world-model proposal analysis when no review blocker is present. It writes `post_generation_review_result` and a `post_generation_review` checkpoint to the selected `BackgroundTask.result`.

This is still not a multi-chapter runner. It is the review gate after one approved chapter generation.

## Reference Assimilation

Adopted:

- `openclaw` loop guards: the tool validates state before any side effect and denies drift.
- `hermes-agent` checkpointing: the tool records durable post-generation review evidence and bounded checkpoint history.
- `openhuman` provenance model: review findings and world-model analysis outputs are persisted with chapter and batch-execution provenance.

Not adopted:

- generic subagent runtime;
- external memory backend;
- autonomous retry loop;
- world-model proposal auto-apply;
- unattended multi-chapter batch execution.

## Changes

- Added `backend/app/services/writing_agent/batch_post_generation_review.py`.
- Registered `review_longform_chapter_batch_execution` as an internal task-queue write tool.
- Added executor adapter and parameter normalization.
- Extended `inspect_longform_chapter_batch` selected task details with:
  - `post_generation_review_result`;
  - execution readiness status `phase63_reviewed`.
- Added tests for:
  - registry contract;
  - executor metadata and dispatch;
  - happy-path post-generation review;
  - missing Phase62 execution evidence blocker;
  - quality blocker preventing world-model intake;
  - idempotent repeat review without duplicate side effects.

## Tool Contract

Input:

- `task_id`;
- optional `lookback`, defaulting to 20.

Success output:

- `status: "completed"`;
- `chapter_index`;
- `review_gate`;
- `reviews.quality`;
- `reviews.continuity`;
- `reviews.world_model`;
- `post_generation_review_result`;
- `execution_checkpoint`;
- `side_effects`.

Blocked output:

- `status: "blocked"`;
- `reason`;
- no world-model analysis when quality or continuity blockers exist.

Idempotent repeat output:

- `status: "skipped"`;
- `reason: "post_generation_review_already_recorded"`;
- existing `post_generation_review_result`.

## Side Effect Boundary

Allowed:

- run `review_chapter_quality`;
- run `review_chapter_continuity`;
- run `analyze_chapter_to_world_proposals` only after review blockers are absent;
- write `post_generation_review_result`;
- append a `post_generation_review` execution checkpoint.

Explicitly skipped:

- `LocalTaskRunner`;
- chapter generation or revision;
- auto-resume to next chapter;
- world-model proposal apply;
- duplicate review side effects when an identical review result already exists.

## Verification

RED focused tests:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "review_longform_chapter_batch_execution"
```

Result before implementation: `4 failed, 184 deselected`.

Focused GREEN:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "review_longform_chapter_batch_execution"
```

Result: `4 passed, 184 deselected in 0.87s`.

Idempotence check:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "review_longform_chapter_batch_is_idempotent"
```

Result: `1 passed, 148 deselected in 0.80s`.

Batch chain regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_tool_registry.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_runs.py -q -k "longform_chapter_batch"
```

Result: `40 passed, 148 deselected in 2.27s`.

T1 related regression:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py tests\test_background.py -q
```

Result: `228 passed in 14.22s`.

Static checks:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend docs --glob "!docs/archive/**"
```

Result:

- `git diff --check` passed; it reported only the existing line-ending normalization warning for `backend/tests/test_writing_agent_runs.py`.
- secret scan returned no matches.

## Novel Progress

No production novel chapter was generated in this phase. The review gate was verified with monkeypatched generation and review services so the task-queue orchestration could be stabilized before spending model calls.

## Discovered Issues

- Phase62 could generate one approved chapter, but the task queue had no durable post-generation review gate.
- A generated chapter could proceed toward future batches without quality/continuity evidence attached to the batch task.
- Running world-model analysis before quality blockers are known can pollute proposal queues with facts from a chapter that needs revision.
- Re-running a review could duplicate world-model proposal side effects.

## Fixed Issues

- Added a post-generation review tool that consumes Phase62 evidence.
- Added blocker-aware world-model analysis gating.
- Added persisted review evidence and inspector visibility.
- Added idempotent repeat behavior for the same Phase62 execution result.
- Added tests proving no duplicate review side effects on repeat calls.

## Remaining Boundary

The next phase should turn review results into recovery planning:

- when `post_generation_review_result.status == "needs_revision"`, generate a structured revision plan;
- when review passes, prepare the next chapter batch;
- keep both paths explicit and auditable before adding any unattended multi-chapter runner.
