# Phase56 Continuation State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lightweight continuation state to Writing Agent run output so long-running writing workflows can be resumed and audited after blocks, failures, recovery chains, or context compaction.

**Architecture:** Do not add a database migration in this phase. Derive `continuation_state` from the existing `WritingAgentRun.input`, run status, and persisted `WritingAgentStep` rows inside `run.output`. The state records the active task, target chapter, last successful tool, next expected tool, recovery recommendation, failure reason, and which generation/review/memory/world-model outputs have been consumed.

**Tech Stack:** FastAPI backend, SQLAlchemy models, Writing Agent run service, pytest.

---

## Reference Assimilation

This phase translates prior reference findings into novelv3 without importing external runtime complexity:

- `openclaw`: continuation state should be derived from canonical execution records, not UI projection.
- `hermes-agent`: resumed work needs a compact handoff checkpoint with active task, completed actions, blocked reason, and remaining work.
- `openhuman`: long-running plans should expose bounded state and the next expected action instead of requiring the parent context to remember everything.

novelv3 adaptation:

- Use existing run and step rows as canonical state.
- Store the computed checkpoint in `run.output.continuation_state`.
- Keep this as a read model; no new table or queue worker yet.
- Use it first for Writing Agent run/recovery flows before generalizing to task queue batches.

## Files

- Modify: `backend/app/services/writing_agent/run_service.py`
  - Extend `_run_output()` to include `continuation_state`.
  - Add small helper functions to infer target chapter, last successful tool, next expected tool, latest recovery, consumed outputs, and resume hints.
- Modify: `backend/tests/test_writing_agent_runs.py`
  - Assert blocked context runs expose a recovery-ready continuation state.
  - Assert confirmed context recovery chains expose a completed generation state.
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-20-phase56-continuation-state.md`
  - Record implementation, reference absorption, verification, and next phase.

## Task 1: RED for Blocked Continuation State

- [x] **Step 1: Add failing assertions**

In `test_agent_auto_plan_longform_context_blocks_stale_maintenance_before_generation`, assert:

```python
state = payload["output"]["continuation_state"]
assert state["version"] == "phase56.continuation_state.v1"
assert state["status"] == "blocked"
assert state["target_chapter_index"] == 2
assert state["last_successful_tool"]["tool_name"] == "summarize_longform_context"
assert state["blocked_tool"]["tool_name"] == "summarize_longform_context"
assert state["next_expected_tool"] == "repair_longform_maintenance"
assert state["recovery"]["status"] == "recommended"
assert state["recovery"]["next_tool"] == "repair_longform_maintenance"
assert state["consumed"]["longform_context"] is True
assert state["consumed"]["generated_chapter"] is False
```

- [x] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_blocks_stale"
```

Expected: fail because `run.output` has no `continuation_state`.

## Task 2: RED for Completed Recovery Chain State

- [x] **Step 1: Add failing assertions**

In `test_agent_run_executes_longform_context_recovery_chain_after_confirmation`, assert:

```python
state = payload["output"]["continuation_state"]
assert state["status"] == "completed"
assert state["target_chapter_index"] == 2
assert state["last_successful_tool"]["tool_name"] == "generate_chapter"
assert state["next_expected_tool"] is None
assert state["consumed"]["longform_maintenance"] is True
assert state["consumed"]["longform_context"] is True
assert state["consumed"]["preflight"] is True
assert state["consumed"]["generated_chapter"] is True
assert state["consumed"]["world_model_proposals"] is False
```

- [x] **Step 2: Run RED**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_recovery_chain"
```

Expected: fail because completed runs do not expose continuation state.

## Task 3: GREEN for Derived Continuation State

- [x] **Step 1: Implement `_run_output()` enrichment**

In `run_service.py`, query run and ordered steps in `_run_output()`. Preserve existing counts and add:

```python
"continuation_state": _continuation_state(run, steps)
```

- [x] **Step 2: Implement state helpers**

Add helpers that derive:

- `target_chapter_index`;
- `last_successful_tool`;
- `blocked_tool`;
- `next_expected_tool`;
- `recovery`;
- `failure`;
- `consumed`.

Use only existing run/step data.

- [x] **Step 3: Run focused GREEN**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py -q -k "longform_context_blocks_stale or longform_context_recovery_chain"
```

Expected: pass.

## Task 4: Verification and Report

- [x] **Step 1: Run T1 Agent verification**

Run:

```powershell
cd backend
.venv\Scripts\python.exe -m pytest tests\test_writing_agent_runs.py tests\test_writing_agent_planner.py tests\test_writing_agent_tool_executor.py tests\test_writing_agent_tool_registry.py -q
```

- [x] **Step 2: Run static checks**

Run:

```powershell
git diff --check
rg "sk-[A-Za-z0-9]{20,}" -n docs backend frontend references --glob "!.git"
```

- [x] **Step 3: Write phase report**

Create `docs/superpowers/notes/long-memory-agent/2026-05-20-phase56-continuation-state.md`.

- [ ] **Step 4: Commit and push**

Run:

```powershell
git status --short
git add backend docs
git commit -m "feat: expose writing agent continuation state"
git push origin main
```
