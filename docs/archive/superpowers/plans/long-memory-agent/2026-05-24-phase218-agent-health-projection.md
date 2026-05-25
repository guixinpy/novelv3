# Phase218 Agent Health Projection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Keep this phase read-only. Do not change planner execution behavior, runtime routes, profile filtering, or write gates.

**Goal:** Add an Agent-callable health projection tool that lets the Writing Agent inspect profile policy, route preference, tool contract, write gate, and optional latest run trace evidence from one compact read-only surface.

**Architecture:** Create `inspect_agent_health_projection` as an aggregation/report tool. It should reuse existing projection sources instead of recomputing policy logic ad hoc:

- profile policy: `build_agent_tool_plan(...).agent_profile_tool_projection.consistency_audit`
- route preference: `inspect_agent_route_preference_projection`
- tool contracts: `build_agent_tool_contract_snapshot(include_gap_details=False)`
- write gate: `inspect_agent_write_gate_coverage`
- optional run evidence: `inspect_agent_trace_audit(run_id=...)`

The output should remain compact and machine-readable. This phase must not introduce recovery execution, planner blocking, or profile delegation runtime.

**Tech Stack:** Python, pytest.

---

## Reference Project Inputs

- OpenClaw: health/status projections should be machine-readable and separate from enforcement.
- Hermes Agent: orchestration dashboards summarize child tool health without exposing all internals.
- OpenHuman: visible capability maps and memory/tool boundaries should be inspectable by the agent before action.

## Files

- Create: `backend/app/services/writing_agent/agent_health_projection.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Create or modify: `backend/tests/test_writing_agent_health_projection.py`
- Create: `docs/superpowers/notes/long-memory-agent/2026-05-24-phase218-agent-health-projection.md`

## Tasks

### Task 1: RED Service Test

- [x] Add a test proving `inspect_agent_health_projection()` surfaces profile policy issues as compact diagnostics and does not expose raw `delegate_edges`.
- [x] Add a test proving optional `run_id` imports compact profile policy status from `inspect_agent_trace_audit`.

Expected before implementation: import or assertion fails because no health projection service exists.

### Task 2: Service Implementation

- [x] Implement `inspect_agent_health_projection(...)`.
- [x] Build compact sections:
  - `profile_policy`
  - `route_preference`
  - `tool_contracts`
  - `write_gate`
  - optional `trace_audit`
- [x] Emit `diagnostics` and `recommended_tools`.
- [x] Keep status read-only: `ready`, `degraded`, or `needs_attention`.

### Task 3: Agent Tool Registration

- [x] Add descriptor for `inspect_agent_health_projection`.
- [x] Add static read adapter.
- [x] Add executor metadata/static name tests.

### Task 4: Validation, Report

- [x] Run targeted backend tests:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_health_projection.py backend\tests\test_writing_agent_tool_executor.py -k "agent_health_projection or static_adapter_names" -q
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
