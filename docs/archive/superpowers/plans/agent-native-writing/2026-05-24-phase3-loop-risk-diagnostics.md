# Phase 3 Loop Risk Diagnostics Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add read-only tool loop risk diagnostics to the Writing Agent loop contract.

**Architecture:** Keep execution behavior unchanged. Add a deterministic projection that inspects the current run's tool sequence, detects repeated identical adjacent calls, and reports warning/critical risk metadata under `continuation_state.agent_loop.loop_risk`.

**Tech Stack:** FastAPI backend, SQLAlchemy models, pytest API tests.

---

## Context

`openclaw` includes tool loop detection to prevent Agents from repeatedly calling tools without progress. novelv3 does not yet have an autonomous LLM tool loop, but it already executes multi-step tool plans. Adding read-only risk diagnostics now creates the contract needed before future phases allow dynamic tool selection.

This phase should not block execution. It only makes loop risk visible.

## Tasks

### Task 1: Add failing tests

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] Add a test that three adjacent identical tool calls produce `loop_risk.status = "warning"`.
- [x] Assert the repeated tool name, count, and stable signature are exposed.
- [x] Assert ordinary successful runs keep `loop_risk.status = "clear"`.

**Verification command:**

```powershell
cd backend
pytest tests/test_writing_agent_runs.py -k "loop_risk" -q
```

Expected before implementation: tests fail because `loop_risk` is missing.

### Task 2: Implement read-only detector

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] Add a stable signature from tool name and params.
- [x] Detect adjacent repeated calls.
- [x] Use thresholds:
  - `clear`: max repeat count < 3;
  - `warning`: 3-4 repeats;
  - `critical`: 5+ repeats.

### Task 3: Verification and report

**Files:**

- Create: `docs/superpowers/notes/agent-native-writing/2026-05-24-phase3-loop-risk-diagnostics.md`

**Commands:**

```powershell
cd backend
pytest tests/test_writing_agent_runs.py -k "loop_risk or agent_loop or tool_input_validation" -q
```

Expected: targeted runtime tests pass.
