# Longform Batch Post Generation Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a post-generation review gate for Phase62 longform batch execution so the Agent can audit generated chapters before continuing.

**Architecture:** Add an internal Writing Agent tool named `review_longform_chapter_batch_execution`. It consumes a Phase62 `batch_execution_result`, validates the generated chapter, runs quality and continuity reviews, conditionally runs Athena world-model proposal analysis only when blockers are absent, and persists review evidence to `BackgroundTask.result`. It does not generate prose or advance to the next chapter.

**Tech Stack:** FastAPI backend, SQLAlchemy models, existing Writing Agent tool registry/executor, chapter review services, Athena longform analyzer, pytest.

---

## File Structure

- Create `backend/app/services/writing_agent/batch_post_generation_review.py`
  - Validate project/task, Phase62 execution evidence, single chapter, and chapter content existence.
  - Run `review_chapter_quality` and `review_chapter_continuity`.
  - If blockers exist, skip world-model analysis and return `status: "blocked"`.
  - If no blockers exist, run `analyze_chapter_to_world_proposals`.
  - Persist `post_generation_review_result` and append a bounded `post_generation_review` checkpoint.
- Modify `backend/app/services/writing_agent/tool_registry.py`
  - Register `review_longform_chapter_batch_execution`.
- Modify `backend/app/services/writing_agent/tool_executor.py`
  - Add adapter and parameter normalization.
- Modify `backend/app/services/writing_agent/batch_queue_inspector.py`
  - Expose persisted `post_generation_review_result`.
  - Report execution readiness after review evidence.
- Modify backend tests:
  - `backend/tests/test_writing_agent_tool_registry.py`
  - `backend/tests/test_writing_agent_tool_executor.py`
  - `backend/tests/test_writing_agent_runs.py`

## Task 1: Registry And Adapter Contract

- [ ] Add failing registry test for `review_longform_chapter_batch_execution`.
- [ ] Add failing adapter metadata and dispatch tests.
- [ ] Verify RED with focused pytest.
- [ ] Register descriptor and adapter.
- [ ] Verify GREEN.

## Task 2: Review Gate Service

- [ ] Add failing happy-path API test:
  - enqueue chapter 2;
  - preflight;
  - prepare;
  - execute approved single chapter;
  - run `review_longform_chapter_batch_execution`;
  - assert quality, continuity, and world-model analysis are called;
  - assert review evidence is persisted and inspector exposes it.
- [ ] Add failing blocked-path test for missing Phase62 execution evidence.
- [ ] Add failing blocker-gate test where quality review returns blockers and world-model analysis is skipped.
- [ ] Implement the service.
- [ ] Verify focused tests pass.

## Task 3: Phase Report And Verification

- [ ] Run T0 focused tests for the new review gate.
- [ ] Run T1 related regression for Writing Agent batch, tool registry, executor, run service, and background task tests.
- [ ] Run static checks and secret scan.
- [ ] Write Phase63 report under `docs/superpowers/notes/long-memory-agent/`.
- [ ] Commit and push to `main`.

## Boundaries

Do:

- consume only persisted Phase62 execution evidence;
- support only one generated chapter per review in this phase;
- stop world-model proposal analysis when quality or continuity blockers exist;
- persist review results and checkpoints;
- recommend revision planning when blockers exist.

Do not:

- generate or revise chapter prose;
- start `LocalTaskRunner`;
- auto-resume the next chapter;
- apply world-model proposal decisions;
- create a generic multi-chapter review runner;
- treat missing world-model profile as a generation failure.
