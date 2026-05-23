# Phase194 Route Preference Opt-In Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 route preference projection 能显示 approval-chain opt-in metadata 是否已经声明，便于 Agent 在不改变默认路由的前提下审查迁移状态。

**Architecture:** 在 `inspect_agent_dialog_route_projection` / `inspect_agent_route_preference_projection` 增加可选 `approval_chain_opt_in_action_types` 输入，仅用于投影中给匹配 action route 加上 `use_agent_approval_chain=True`。`_route_preference` 输出 opt-in 可观测字段，并将已声明 opt-in 的路由标记为 `opt_in_declared`。

**Tech Stack:** Python 3、pytest、Writing Agent route projection、Agent tool adapter metadata。

---

## Files

- Modify: `backend/app/services/writing_agent/slash_command_route.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
- Modify: `backend/tests/test_writing_agent_route_preference.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase194-route-preference-opt-in-observability.md`

## Success Criteria

- Default `inspect_agent_route_preference_projection(...)` still reports setup/storyline/outline/chapter as `recommended_not_applied`.
- `inspect_agent_route_preference_projection(..., approval_chain_opt_in_action_types=["preview_setup"])` marks the setup route:
  - `approval_chain_opt_in_declared is True`
  - `approval_chain_opt_in_available is True`
  - `approval_chain_opt_in_param_name == "use_agent_approval_chain"`
  - `migration_status == "opt_in_declared"`
- Summary includes `opt_in_declared_count`.
- Trace includes normalized `approval_chain_opt_in_action_types`.
- Writing Agent tool adapter forwards `approval_chain_opt_in_action_types`.
- No default runtime route changes.

## Non-Scope

- Do not default slash/text/button routes to opt-in.
- Do not change pending action dispatch.
- Do not execute generation tools.

## Tasks

### Task 1: RED Projection Tests

- [x] Add route preference tests in `backend/tests/test_writing_agent_route_preference.py` for default fields and opt-in-declared fields.
- [x] Add tool executor adapter test in `backend/tests/test_writing_agent_tool_executor.py` proving params are forwarded.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -k "opt_in" -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection and opt_in" -q
```

Expected: projection lacks `approval_chain_opt_in_*` fields and adapter does not forward the new parameter.

### Task 2: Implement Projection Fields

- [x] Import `DIALOG_AGENT_ROUTE_APPROVAL_CHAIN_OPT_IN_KEY`.
- [x] Add helper to normalize `approval_chain_opt_in_action_types`.
- [x] Add helper to copy routes and attach `use_agent_approval_chain=True` for selected action types.
- [x] Update `_route_preference` to emit:
  - `approval_chain_opt_in_param_name`
  - `approval_chain_opt_in_declared`
  - `approval_chain_opt_in_available`
  - `migration_status`.
- [x] Update summary and trace.

### Task 3: Wire Descriptor And Adapter

- [x] Add `approval_chain_opt_in_action_types` to `inspect_agent_route_preference_projection` descriptor input schema.
- [x] Pass `tool.params.get("approval_chain_opt_in_action_types")` through adapter to service function.

### Task 4: GREEN/T2 Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_route_preference.py -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_preference_projection" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "route_preference" -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase194-route-preference-opt-in-observability.md
```

- [ ] Commit and push:

```powershell
git add backend/app/services/writing_agent/slash_command_route.py backend/app/services/writing_agent/agent_core_tool_descriptors.py backend/app/services/writing_agent/agent_core_tool_adapters.py backend/tests/test_writing_agent_route_preference.py backend/tests/test_writing_agent_tool_executor.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase194-route-preference-opt-in-observability.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase194-route-preference-opt-in-observability.md
git commit -m "feat: expose route approval opt in state"
git push origin main
```
