# Phase219 Planner Health Trace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Keep this phase read-only and non-blocking: planner output may include health evidence, but must not change selected tools, route behavior, profile filtering, or approval requirements.

**Goal:** Attach compact `inspect_agent_health_projection` evidence to `build_writing_agent_run_plan().trace` so every Agent plan can see current tool/profile/route/write-gate health before execution.

**Architecture:** Reuse Phase218 `inspect_agent_health_projection`. Pass the already-built `tool_plan` into the health service to avoid recomputing the Agent tool plan. Keep health data as compact trace evidence only:

- `trace.agent_health_projection.status`
- `trace.agent_health_projection.diagnostic_count`
- `trace.agent_health_projection.diagnostics`
- `trace.agent_health_projection.recommended_tools`

Do not add risk flags from health projection in this phase.

**Tech Stack:** Python, pytest.

---

## Reference Project Inputs

- OpenClaw: planner traces should include health/policy evidence but enforcement remains separate.
- Hermes Agent: plan state and execution state should remain distinct; health projection is planning evidence, not execution.
- OpenHuman: high-level planner output should carry compact diagnostics, not raw internal graph details.

## Files

- Modify: `backend/app/services/writing_agent/agent_health_projection.py`
- Modify: `backend/app/services/writing_agent/planner.py`
- Modify: `backend/tests/test_writing_agent_planner.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase219-planner-health-trace.md`

## Tasks

### Task 1: RED Planner Test

- [x] Add planner assertion that `plan["trace"]["agent_health_projection"]` exists and is compact.
- [x] Assert selected tool chain remains unchanged for a normal next-chapter plan.

Expected before implementation: fails because planner trace lacks `agent_health_projection`.

### Task 2: Service Reuse

- [x] Let `inspect_agent_health_projection()` accept optional `tool_plan`.
- [x] Use supplied `tool_plan` when present, otherwise build as before.

### Task 3: Planner Integration

- [x] Add `_planner_health_projection(...)`.
- [x] Attach compact health trace.
- [x] Do not copy health diagnostics into `risk_flags`.

### Task 4: Validation, Report

- [x] Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_planner.py backend\tests\test_writing_agent_health_projection.py -k "health_projection or ready_next_chapter" -q
```

- [x] Run:

```powershell
backend\.venv\Scripts\python.exe -m compileall backend\app\services\writing_agent
git diff --check
```

- [x] Run DeepSeek key prefix scan without embedding a key in files:

```powershell
$pat='sk-'+'f6aa'; rg -n $pat backend frontend docs --glob '!frontend/node_modules/**'
```

- [x] Write phase report.
