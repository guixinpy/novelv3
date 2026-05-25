# Phase 2 Tool Call Validation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a minimal pre-execution validation gate for Writing Agent tool calls.

**Architecture:** Keep the existing tool registry and executor. Add a small validator that reads each tool descriptor's `input_schema`, checks required fields and basic JSON types before execution, and fails the run with structured validation output when the call is malformed.

**Tech Stack:** FastAPI backend, SQLAlchemy models, pytest API tests.

---

## Context

`hermes-agent` validates malformed tool calls before execution. novelv3 currently checks whether a tool name is allowed, but a known tool can still receive malformed params and reach adapter code. For an autonomous Agent, this should be a runtime contract, not ad hoc defensive code inside every adapter.

This phase is intentionally minimal: no new dependency and no full JSON Schema engine. The goal is to catch the common failure classes that matter for Agent-generated tool calls:

- missing required params;
- wrong top-level param type;
- integer/number minimum violations;
- structured failure output that appears in run output and `agent_loop`.

## Tasks

### Task 1: Add failing tests

**Files:**

- Modify: `backend/tests/test_writing_agent_runs.py`

- [x] Add a test that `preview_agent_plan_approval_contract` fails before execution when required `plan` is missing.
- [x] Add a test that `preflight_writing` fails before execution when `chapter_index` has the wrong type.
- [x] Assert validation output contains stable issue codes.

**Verification command:**

```powershell
cd backend
pytest tests/test_writing_agent_runs.py -k "tool_input_validation" -q
```

Expected before implementation: tests fail.

### Task 2: Add validator module

**Files:**

- Create: `backend/app/services/writing_agent/tool_request_validation.py`

- [x] Implement `validate_tool_request(tool_name, params)` returning a structured dict.
- [x] Validate descriptor presence defensively, although `run_service` already checks allowed tools.
- [x] Support top-level object schemas, `required`, `type`, and `minimum`.

### Task 3: Gate execution in run service

**Files:**

- Modify: `backend/app/services/writing_agent/run_service.py`

- [x] Call validation after allowlist check and before `_execute_tool`.
- [x] Fail the step/run with structured output when validation fails.
- [x] Preserve `agent_loop.exit_reason = "tool_failed"` for malformed calls.

### Task 4: Verification and report

**Files:**

- Create: `docs/superpowers/notes/agent-native-writing/2026-05-24-phase2-tool-call-validation.md`

**Commands:**

```powershell
cd backend
pytest tests/test_writing_agent_runs.py -k "tool_input_validation or agent_loop or recovery" -q
```

Expected: targeted runtime and recovery tests pass.
