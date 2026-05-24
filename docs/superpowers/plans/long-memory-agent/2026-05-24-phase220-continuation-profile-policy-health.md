# Phase220 Continuation Profile Policy Health Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development. Keep this phase read-only and compact. Do not change run execution, planner selection, profile filtering, or recovery behavior.

**Goal:** Expose compact profile policy health in `output.continuation_state` so run detail/result consumers can see whether a Writing Agent run's profile/tool policy evidence passed, needs attention, or is missing.

**Architecture:** Reuse `_agent_profile_policy_audit_from_steps(steps)` in `run_service.py`. Add a small `_profile_policy_health(steps)` projection:

- `status`: `passed`, `needs_attention`, or `unknown`
- `issue_count`
- `reason`
- `recommended_tools`

Do not include raw `delegate_edges`, full audit `rules`, or detailed profile definitions in continuation state.

**Tech Stack:** Python, pytest.

---

## Reference Project Inputs

- OpenClaw: continuation/run status should include compact health state, while raw policy evidence remains in inspection tools.
- Hermes Agent: run summaries expose progress and status, not full internal worker/delegation internals.
- OpenHuman: long-memory Agent state should surface health and next actions without mixing it into domain memory.

## Files

- Modify: `backend/app/services/writing_agent/run_service.py`
- Modify: `backend/tests/test_writing_agent_runs.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase220-continuation-profile-policy-health.md`

## Tasks

### Task 1: RED Test

- [x] Extend run detail/auto-plan test to assert `output.continuation_state.profile_policy_health`.
- [x] Assert compact output does not include `delegate_edges`.

Expected before implementation: fails because continuation state lacks `profile_policy_health`.

### Task 2: Implementation

- [x] Add `_profile_policy_health(steps)`.
- [x] Attach it to `_continuation_state(...)`.
- [x] Keep `agent_profile_policy_audit` full payload only in run detail top-level, not in continuation state.

### Task 3: Validation, Report

- [x] Run:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py -k "agent_profile_projection_for_auto_plan or continuation_state_exposes_recommended_followups" -q
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
