# Longform Batch Post Review Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a post-review routing tool that turns Phase63 review evidence into an explicit next-step route for revision or the next chapter batch.

**Architecture:** Add an internal Writing Agent tool named `route_longform_chapter_batch_after_review`. It consumes `post_generation_review_result`, validates the Phase62/63 evidence chain, and writes a durable `post_generation_route_result` to `BackgroundTask.result`. It does not revise prose, enqueue tasks, or start a runner.

**Tech Stack:** FastAPI backend, SQLAlchemy models, existing Writing Agent tool registry/executor, batch enqueue preview, chapter revision planner, pytest.

---

## File Structure

- Create `backend/app/services/writing_agent/batch_post_review_router.py`
  - Validate project/task, Phase62 `batch_execution_result`, Phase63 `post_generation_review_result`, chapter-content existence, and task batch bindings.
  - If review status is `needs_revision`, call `plan_chapter_revision` and build a recovery route.
  - If review status is `passed`, call `build_longform_chapter_batch_plan` for the next chapter batch preview.
  - Persist `post_generation_route_result` and append a bounded `post_generation_route` checkpoint.
  - Idempotently return an existing route when the underlying review hash has not changed.
- Modify `backend/app/services/writing_agent/tool_registry.py`
  - Register `route_longform_chapter_batch_after_review`.
- Modify `backend/app/services/writing_agent/tool_executor.py`
  - Add adapter and parameter normalization.
- Modify `backend/app/services/writing_agent/batch_queue_inspector.py`
  - Expose persisted `post_generation_route_result`.
  - Report execution readiness status `phase64_routed`.
- Modify backend tests:
  - `backend/tests/test_writing_agent_tool_registry.py`
  - `backend/tests/test_writing_agent_tool_executor.py`
  - `backend/tests/test_writing_agent_runs.py`

## Task 1: Registry And Adapter Contract

- [x] Add failing registry test for `route_longform_chapter_batch_after_review`.
- [x] Add failing adapter metadata and dispatch tests.
- [x] Verify RED with focused pytest.
- [x] Register descriptor and adapter.
- [x] Verify GREEN.

## Task 2: Routing Service

- [x] Add failing API test for the `needs_revision` branch:
  - create Phase62 execution and Phase63 blocker review;
  - route after review;
  - assert a revision route is persisted and no next batch is enqueued.
- [x] Add failing API test for the `passed` branch:
  - create Phase62 execution and Phase63 passing review;
  - route after review;
  - assert a next batch enqueue preview is produced with confirmation required.
- [x] Add failing blocked-path test for missing Phase63 review evidence.
- [x] Add failing idempotence test for repeated routing.
- [x] Implement the service.
- [x] Verify focused tests pass.

## Task 3: Phase Report And Verification

- [x] Run T0 focused tests for the new routing tool.
- [x] Run T1 related regression for Writing Agent batch, tool registry, executor, run service, and background task tests.
- [x] Run static checks and secret scan.
- [x] Write Phase64 report under `docs/superpowers/notes/long-memory-agent/`.
- [ ] Commit and push to `main`.

## Boundaries

Do:

- consume only persisted Phase63 review evidence;
- keep revision and next-batch paths explicit;
- call `plan_chapter_revision` for recovery planning;
- call enqueue preview without confirmation for the next chapter path;
- persist route evidence for later Agent planning and UI inspection.

Do not:

- create revision drafts;
- apply revision patches;
- enqueue the next batch;
- start `LocalTaskRunner`;
- auto-generate the next chapter;
- apply world-model proposal decisions;
- treat missing next chapter outline as a silent success.
