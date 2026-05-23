# Phase196 Route Approval Opt-In Prewrite Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增加只读的 route approval opt-in 写入前计划工具，让 Agent 可以在真正修改 pending action / route metadata 前获得可审计的 patch、风险和 guardrails。

**Architecture:** 在 `slash_command_route.py` 新增 `plan_agent_route_approval_opt_in`。该函数接收 `agent_route` 或 `action_type/source/command_name`，复用现有 route preference / suggestion 逻辑生成 `route_before`、`route_after`、`metadata_patch`、`can_apply`、`write_performed=False`。通过 `agent_core_tool_descriptors.py` 和 `agent_core_tool_adapters.py` 暴露为内部 preflight 工具。

**Tech Stack:** Python 3、pytest、Writing Agent preflight tools、dialog route projection。

---

## Files

- Modify: `backend/app/services/writing_agent/slash_command_route.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
- Modify: `backend/tests/test_writing_agent_route_preference.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase196-route-approval-opt-in-prewrite-plan.md`

## Success Criteria

- `plan_agent_route_approval_opt_in(action_type="preview_setup", source="slash_command", command_name="setup")` returns:
  - `status == "ready"`
  - `can_apply is True`
  - `write_performed is False`
  - `metadata_patch == {"use_agent_approval_chain": True}`
  - `route_before` has no `use_agent_approval_chain`
  - `route_after` has `use_agent_approval_chain is True`.
- Plan output includes `risk.codes` and `risk.missing_preferred_tools`.
- Passing an already declared route returns `status == "already_declared"` and `can_apply is False`.
- Missing preferred tools returns `status == "blocked"` and `can_apply is False`.
- Non-gated route returns `status == "noop"` and `metadata_patch == {}`.
- New Agent tool `plan_agent_route_approval_opt_in` is internal, preflight, non-blocking, read-only adapter.
- `inspect_agent_route_preference_projection` descriptor input schema exposes `approval_chain_opt_in_action_types`.

## Non-Scope

- Do not write pending action params.
- Do not add an apply/mutation endpoint.
- Do not change default slash/text/button route generation.
- Do not execute generation tools.

## Tasks

### Task 1: RED Service, Registry, Adapter Tests

- [x] Add service tests in `backend/tests/test_writing_agent_route_preference.py`:
  - default setup route returns prewrite patch
  - already declared route returns no-write state
  - missing tools blocks plan
  - non-gated synthetic route is noop.
- [x] Add risk tests for explicit opt-in, already declared, missing tools, no-gate, and runtime action-type warnings.
- [x] Add registry test in `backend/tests/test_writing_agent_tool_registry.py`:
  - `plan_agent_route_approval_opt_in` descriptor exists
  - route preference descriptor exposes `approval_chain_opt_in_action_types`.
- [x] Add executor test in `backend/tests/test_writing_agent_tool_executor.py`:
  - tool executes and returns ready prewrite plan.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -k "prewrite_plan" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "route_preference_projection or route_approval_opt_in_plan" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_approval_opt_in_plan" -q
```

Expected: `plan_agent_route_approval_opt_in` missing and descriptor schema lacks the route preference opt-in parameter.

### Task 2: Implement Service Function

- [x] Add `ROUTE_APPROVAL_OPT_IN_PLAN_VERSION`.
- [x] Add `plan_agent_route_approval_opt_in(...)`.
- [x] Add `_route_from_plan_input(...)` helper:
  - use provided `agent_route` when dict
  - otherwise call `build_dialog_agent_route(action_type, source=source or "slash_command", command_name=command_name)`.
- [x] Reuse `_route_preference(...)`.
- [x] Return status mapping:
  - `available` -> `ready`
  - `already_declared` -> `already_declared`
  - `blocked_missing_tools` -> `blocked`
  - no suggestion -> `noop`.

### Task 3: Wire Descriptor And Adapter

- [x] Add `plan_agent_route_approval_opt_in` descriptor.
- [x] Add adapter with `static_adapter_tool_names_provider` and `SUPPORTED_ACTION_EXECUTION_TYPES`.
- [x] Add the tool to static adapter expected sets and metadata tests.
- [x] Fix `inspect_agent_route_preference_projection` descriptor input schema to expose `approval_chain_opt_in_action_types`.

### Task 4: GREEN/T2 Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "route_preference_projection or route_approval_opt_in_plan" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection or route_approval_opt_in_plan" -q
python -m compileall backend/app/services/writing_agent
```

### Task 5: Report, Hygiene, Commit, Push

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] Write report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase196-route-approval-opt-in-prewrite-plan.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/slash_command_route.py backend/app/services/writing_agent/agent_core_tool_descriptors.py backend/app/services/writing_agent/agent_core_tool_adapters.py backend/tests/test_writing_agent_route_preference.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase196-route-approval-opt-in-prewrite-plan.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase196-route-approval-opt-in-prewrite-plan.md
git commit -m "feat: plan route approval opt in patches"
git push origin main
```
