# Phase198 Pending Action Route Opt-In Apply Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增只读 apply-preview 工具，给定 pending action id 后返回如果应用 route approval opt-in patch 会产生的 `PendingAction.params` diff，但不写数据库。

**Architecture:** 在 `slash_command_route.py` 新增纯函数 `preview_pending_action_route_approval_opt_in_apply`，接收 pending params 和 Phase197 prewrite plan，生成 `params_before`、`params_after`、`params_diff`。Adapter 负责按 `pending_action_id` 读取数据库、调用 `plan_agent_route_approval_opt_in`，再调用 preview 函数；descriptor 暴露为内部 preflight 工具。

**Tech Stack:** Python 3、pytest、SQLAlchemy test session、Writing Agent preflight tools。

---

## Files

- Modify: `backend/app/services/writing_agent/slash_command_route.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_adapters.py`
- Modify: `backend/app/services/writing_agent/agent_core_tool_descriptors.py`
- Modify: `backend/tests/test_writing_agent_tool_executor.py`
- Modify: `backend/tests/test_writing_agent_tool_registry.py`
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase198-pending-action-route-opt-in-apply-preview.md`

## Success Criteria

- New tool `preview_pending_action_route_approval_opt_in_apply` is internal, preflight, non-blocking, read-only.
- Given a pending action with legacy `agent_route`, output includes:
  - `status == "ready"`
  - `write_performed is False`
  - `params_before` equals current DB params
  - `params_after["agent_route"]["use_agent_approval_chain"] is True`
  - `params_diff["agent_route"]["before"]` and `params_diff["agent_route"]["after"]`
  - `route_plan.status == "ready"`.
- DB `PendingAction.params` remains unchanged.
- Already-declared route returns `status == "already_declared"` and empty `params_diff`.
- Missing pending action returns `status == "blocked"` and `risk.codes == ["pending_action_not_found"]`.
- Missing `PendingAction.params["agent_route"]` returns blocked and does not synthesize a route.
- Top-level `PendingAction.params["use_agent_approval_chain"] is False` returns blocked because nested route patch would be ineffective.

## Non-Scope

- Do not write `PendingAction.params`.
- Do not execute route opt-in.
- Do not change resolve-action or dispatch behavior.

## Tasks

### Task 1: RED Apply Preview Tests

- [x] Add executor tests in `backend/tests/test_writing_agent_tool_executor.py`:
  - ready preview returns params diff and does not mutate DB
  - already-declared route returns no diff
  - missing pending action returns blocked.
  - missing `agent_route` and top-level false override return blocked.
- [x] Add registry and adapter metadata assertions.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply_preview" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "route_opt_in_apply_preview" -q
```

Expected: tool and descriptor are missing.

### Task 2: Implement Pure Preview Function

- [x] Add `PENDING_ACTION_ROUTE_OPT_IN_APPLY_PREVIEW_VERSION`.
- [x] Add `preview_pending_action_route_approval_opt_in_apply(...)`.
- [x] If route plan is ready, produce params diff for `agent_route`.
- [x] If route plan is already_declared/noop, produce empty diff.
- [x] Use deep copies so nested params cannot be mutated by preview generation.
- [x] Preserve `write_performed=False`.

### Task 3: Wire Adapter And Descriptor

- [x] Add descriptor `preview_pending_action_route_approval_opt_in_apply`.
- [x] Add adapter map entry and handler.
- [x] Handler reads `PendingAction` and `Dialog` by `pending_action_id`, checks project ownership, then calls Phase197 plan function and pure preview.
- [x] Handler blocks missing `agent_route` and top-level false override instead of synthesizing an ineffective patch.
- [x] Add static adapter expected names and metadata tests.

### Task 4: GREEN/T2 Verification

- [x] Run:

```powershell
pytest backend/tests/test_writing_agent_tool_executor.py -k "route_opt_in_apply_preview or pending_action_route_opt_in_plan or route_approval_opt_in_plan" -q
pytest backend/tests/test_writing_agent_tool_registry.py -k "route_opt_in_apply_preview or route_approval_opt_in_plan" -q
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
docs/superpowers/notes/long-memory-agent/2026-05-23-phase198-pending-action-route-opt-in-apply-preview.md
```

- [x] Commit and push:

```powershell
git add backend/app/services/writing_agent/slash_command_route.py backend/app/services/writing_agent/agent_core_tool_adapters.py backend/app/services/writing_agent/agent_core_tool_descriptors.py backend/tests/test_writing_agent_tool_executor.py backend/tests/test_writing_agent_tool_registry.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase198-pending-action-route-opt-in-apply-preview.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase198-pending-action-route-opt-in-apply-preview.md
git commit -m "feat: preview pending route opt in apply"
git push origin main
```
