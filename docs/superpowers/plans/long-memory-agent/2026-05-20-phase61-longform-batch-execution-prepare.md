# Longform Batch Execution Prepare Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert a Phase60 ready preflight checkpoint into a stable attempt manifest and approval contract for future longform batch execution.

**Architecture:** Add a narrow Writing Agent task-queue tool named `prepare_longform_chapter_batch_execution`. It validates a project-scoped `longform_chapter_batch` task and its `preflight_checkpoint`, writes only manifest/approval metadata to `BackgroundTask.result`, and keeps true chapter generation behind a later confirmation-consuming executor.

**Tech Stack:** FastAPI backend, SQLAlchemy models, existing Writing Agent tool registry/executor, pytest.

---

## File Structure

- Create `backend/app/services/writing_agent/batch_execution_prepare.py`
  - Validate task, payload, Phase60 checkpoint, and no generated chapter drift.
  - Build canonical attempt manifest and stable hashes.
  - Persist `attempt_manifest`, `approval_contract`, and bounded `execution_checkpoints`.
- Modify `backend/app/services/writing_agent/tool_registry.py`
  - Register `prepare_longform_chapter_batch_execution`.
- Modify `backend/app/services/writing_agent/tool_executor.py`
  - Add adapter and parameter normalization.
- Modify `backend/app/services/writing_agent/batch_queue_inspector.py`
  - Expose persisted `attempt_manifest` and `approval_contract`.
- Modify backend tests:
  - `backend/tests/test_writing_agent_tool_registry.py`
  - `backend/tests/test_writing_agent_tool_executor.py`
  - `backend/tests/test_writing_agent_runs.py`

## Task 1: Registry And Adapter Contract

- [ ] Add failing registry test for `prepare_longform_chapter_batch_execution`.
- [ ] Add failing adapter metadata and dispatch tests.
- [ ] Verify RED with focused pytest.
- [ ] Register descriptor and adapter.
- [ ] Verify GREEN.

## Task 2: Execution Prepare Service

- [ ] Add failing API happy-path test:
  - enqueue chapter 2;
  - run Phase60 preflight;
  - run `prepare_longform_chapter_batch_execution`;
  - assert `status == "approval_required"`;
  - assert `attempt_manifest_hash` and `approval_contract_hash`;
  - assert task remains `pending`;
  - assert no chapter content is created;
  - assert inspector shows manifest and contract.
- [ ] Add failing blocked-path test for missing preflight checkpoint.
- [ ] Implement service with stable hash and bounded checkpoint append.
- [ ] Verify focused tests pass.

## Task 3: Phase Report And Verification

- [ ] Run T0 focused tests.
- [ ] Run T1 related regression for Writing Agent batch and background task tests.
- [ ] Run static checks and secret scan.
- [ ] Write Phase61 report under `docs/superpowers/notes/long-memory-agent/`.
- [ ] Commit and push to `main`.

## Boundaries

Do not:

- call `LocalTaskRunner`;
- call `ActionExecutionService.execute("generate_chapter")`;
- create or update `ChapterContent`;
- write chapter-generation traces;
- mutate world model, longform memory, retrieval index, or `WritingState`;
- call `mark_running`, `mark_completed`, or range progress methods;
- consume approval.

The only intended side effect is writing manifest/approval metadata into the selected background task result.
