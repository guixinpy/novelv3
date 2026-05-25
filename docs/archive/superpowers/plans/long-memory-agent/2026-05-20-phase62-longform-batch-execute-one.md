# Longform Batch Execute One Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first true execution step for longform chapter batches by consuming a Phase61 approval contract and generating exactly one approved chapter.

**Architecture:** Add an internal Writing Agent tool named `execute_longform_chapter_batch`. It must validate the persisted `attempt_manifest` and `approval_contract`, reject drift, call the existing `generate_chapter` action once, and persist execution evidence to the selected `BackgroundTask.result`. It is not a general batch runner.

**Reference Assimilation:**

- `openclaw`: keep high-risk execution approval-bound and deny by default when the approval contract does not match current state.
- `hermes-agent`: treat checkpoint writes as durable resume/evidence points and keep checkpoint history bounded.
- `openhuman`: keep the parent Agent loop responsible for tool orchestration; the batch executor remains a tool, not a hidden autonomous runtime.

**Tech Stack:** FastAPI backend, SQLAlchemy models, existing Writing Agent tool registry/executor, `ActionExecutionService`, pytest.

---

## File Structure

- Create `backend/app/services/writing_agent/batch_execution.py`
  - Validate selected task, Phase61 manifest, approval contract, task payload bindings, preflight checkpoint, and chapter-content absence.
  - Execute exactly one `generate_chapter` action.
  - Persist `batch_execution_result`, progress, and an execution checkpoint.
- Modify `backend/app/services/writing_agent/tool_registry.py`
  - Register `execute_longform_chapter_batch`.
- Modify `backend/app/services/writing_agent/tool_executor.py`
  - Add async-capable static adapter dispatch.
  - Add adapter and parameter normalization for the executor.
- Modify `backend/app/services/writing_agent/batch_queue_inspector.py`
  - Expose persisted `batch_execution_result`.
  - Report execution readiness after approval and execution evidence.
- Modify backend tests:
  - `backend/tests/test_writing_agent_tool_registry.py`
  - `backend/tests/test_writing_agent_tool_executor.py`
  - `backend/tests/test_writing_agent_runs.py`

## Task 1: Registry And Adapter Contract

- [ ] Add failing registry test for `execute_longform_chapter_batch`.
- [ ] Add failing adapter metadata and async dispatch tests.
- [ ] Verify RED with focused pytest.
- [ ] Register descriptor and async adapter.
- [ ] Verify GREEN.

## Task 2: Approval-Consuming Execution Service

- [ ] Add failing happy-path API test:
  - enqueue chapter 2;
  - run Phase60 preflight;
  - run Phase61 prepare;
  - call `execute_longform_chapter_batch` with all required confirmation fields;
  - assert exactly chapter 2 is generated;
  - assert task result records execution evidence and progress;
  - assert inspector exposes `batch_execution_result`.
- [ ] Add failing blocked-path tests:
  - missing/false confirmation;
  - hash mismatch;
  - chapter-content drift after prepare.
- [ ] Implement validation and execution service.
- [ ] Verify focused tests pass.

## Task 3: Phase Report And Verification

- [ ] Run T0 focused tests for the new executor.
- [ ] Run T1 related regression for Writing Agent batch, tool registry, executor, run service, and background task tests.
- [ ] Run static checks and secret scan.
- [ ] Write Phase62 report under `docs/superpowers/notes/long-memory-agent/`.
- [ ] Commit and push to `main`.

## Boundaries

Do:

- consume only a persisted Phase61 `attempt_manifest` and `approval_contract`;
- require explicit confirmation fields;
- support only one chapter per execution in this phase;
- call existing `generate_chapter` once;
- mark range progress for the generated chapter;
- record inherited `generate_chapter` side effects honestly.

Do not:

- start `LocalTaskRunner`;
- auto-resume the next chapter;
- execute quality review, continuity review, world-model resolution, or revision steps;
- accept caller-provided `chapter_index` overrides;
- execute a manifest whose task payload, preflight checkpoint, hashes, or chapter state drifted;
- claim that Athena/retrieval/longform-memory side effects are skipped if they are inherited from `generate_chapter`.
