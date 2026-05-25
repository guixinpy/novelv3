# Phase197 Pending Action Route Opt-In Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `plan_agent_route_approval_opt_in` 能按 `pending_action_id` 读取真实待确认操作的 route metadata，并生成只读 opt-in patch 计划。

**Architecture:** 在 Agent tool adapter 层解析 `pending_action_id`。若提供该字段，则从 `PendingAction.params["agent_route"]` 读取 route，并把 pending action 的基础信息写入输出 trace；随后复用 Phase196 的纯函数 `plan_agent_route_approval_opt_in`。该阶段不写入 `PendingAction`。

**Tech Stack:** Python 3、pytest、SQLAlchemy test session、Writing Agent preflight tools。

---

## Files

- Modify: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase197-pending-action-route-opt-in-plan.md`

## Success Criteria

- `plan_agent_route_approval_opt_in` descriptor exposes `pending_action_id`.
- Executor can pass `pending_action_id` and receive a ready plan from the pending action's `agent_route`.
- Output trace includes:
  - `pending_action_id`
  - `pending_action_type`
  - `pending_action_route_source == "pending_action"`
- The tool remains read-only:
  - `write_performed is False`
  - database `PendingAction.params` is unchanged.
- Missing pending action id returns blocked plan with `risk.codes` containing `pending_action_not_found`.

## Non-Scope

- Do not mutate `PendingAction.params`.
- Do not change resolve-action behavior.
- Do not add an apply tool.

## Tasks

### Task 1: RED Pending Action Tests

- [x] Add executor tests in `backend/tests/test_writing_agent_tool_executor.py`:
  - pending action id route generates ready plan and does not mutate params
  - missing pending action id returns blocked plan.
- [x] Add registry assertion for descriptor input schema.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "pending_action_route_opt_in_plan" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "route_approval_opt_in_plan" -q
```

Expected: adapter ignores `pending_action_id`, descriptor lacks the field, and missing id is not reported as pending_action_not_found.

### Task 2: Implement Adapter Pending Action Lookup

- [x] Add `pending_action_id` input schema to descriptor.
- [x] In `_plan_agent_route_approval_opt_in`, read `PendingAction` when `pending_action_id` is present.
- [x] If missing, return blocked plan with:
  - `status="blocked"`
  - `can_apply=False`
  - `risk.codes=["pending_action_not_found"]`
  - `trace.pending_action_id=<id>`.
- [x] If found, pass `pending.params["agent_route"]` to service function.
- [x] Append pending action metadata to output trace without mutating DB.

### Task 3: GREEN/T2 Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "pending_action_route_opt_in_plan or route_approval_opt_in_plan" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "route_approval_opt_in_plan" -q
python -m compileall backend/app/services/writing_agent
```

### Task 4: Report, Hygiene, Commit, Push

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] Write report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase197-pending-action-route-opt-in-plan.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/agent_core_tool_adapters.py backend/app/services/writing_agent/agent_core_tool_descriptors.py backend/tests/test_writing_agent_tool_registry.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase197-pending-action-route-opt-in-plan.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase197-pending-action-route-opt-in-plan.md
git commit -m "feat: plan pending action route opt in"
git push origin main
```
