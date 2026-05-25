# Phase 1 Runtime Loop Contract Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first Agent loop contract to current writing-agent runs so each run exposes budget, progress, exit reason, and next action diagnostics.

**Architecture:** Keep the existing `WritingAgentRunService` sequential executor intact. Add a small pure projection inside `run_service.py` that derives loop state from persisted run and steps, then expose it through `run.output.continuation_state.agent_loop`.

**Tech Stack:** FastAPI backend, SQLAlchemy models, pytest API tests.

---

## Context

Current novelv3 already has a large Agent tool surface, but the runtime still behaves mostly as a static plan followed by sequential tool execution. Compared with `hermes-agent`, the missing primitive is an explicit loop contract: budget, consumed iterations, exit reason, and whether a follow-up action is needed.

This phase deliberately does not replace the executor. It creates the observable contract that later phases can evolve into a true autonomous loop.

## Tasks

### Task 1: Add failing tests for Agent loop diagnostics

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] Add a test that a successful auto-plan run exposes `continuation_state.agent_loop`.
- [x] Add a test that a blocked run exposes `exit_reason = "blocked"` and `requires_user_action = true`.
- [x] Add a test that an unsupported tool failure exposes `exit_reason = "tool_failed"`.

**Verification command:**

```powershell
cd backend
pytest tests/test_writing_agent_runs.py -k "agent_loop" -q
```

Expected before implementation: tests fail because `agent_loop` is missing.

### Task 2: Implement minimal run loop projection

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] Add a helper that derives:
  - `version`
  - `loop_kind`
  - `budget.max_iterations`
  - `budget.used_iterations`
  - `budget.remaining_iterations`
  - `exit_reason`
  - `requires_user_action`
  - `next_action`
  - `tool_call_sequence`
- [x] Attach it under `continuation_state.agent_loop`.
- [x] Keep the projection read-only and derived from existing persisted state.

**Verification command:**

```powershell
cd backend
pytest tests/test_writing_agent_runs.py -k "agent_loop" -q
```

Expected after implementation: targeted tests pass.

### Task 3: Update Phase 1 report

**Files:**

- Create: `docs/superpowers/notes/agent-native-writing/2026-05-24-phase1-runtime-loop-contract.md`

- [x] Record reference project lessons.
- [x] Record current novelv3 gap.
- [x] Record implemented code and tests.
- [x] Record next stage recommendation.

### Task 4: Layered verification

**Commands:**

```powershell
cd backend
pytest tests/test_writing_agent_runs.py -k "agent_loop or agent_run_detail_exposes_agent_profile_projection_for_auto_plan" -q
```

Expected: targeted run-service tests pass.

Full T2/T3 validation is deferred until the next runtime-loop milestone or before merging, because this phase only adds a read-only output projection.
