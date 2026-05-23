# Phase193 Agent Route Approval Opt-In Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 `agent_route` metadata 可以显式声明使用 Agent approval chain，并由 dialog control plane 安全派生 Phase192 的 `use_agent_approval_chain` opt-in。

**Architecture:** 在 `build_dialog_agent_route` 增加可选参数 `use_agent_approval_chain=False`，默认不写入 route，保持现有 slash/text/button pending action 输出不变。`dialog_control_plane.py` 在 dispatch 前读取 `agent_route["use_agent_approval_chain"] is True`，仅当顶层控制参数不存在时派生 opt-in，并继续剥离所有控制字段。

**Tech Stack:** Python 3、pytest、dialog route metadata、Writing Agent service layer。

---

## Files

- Modify: `backend/app/core/dialog_agent_routes.py`
- Modify: `backend/app/services/writing_agent/dialog_control_plane.py`
- Modify: `backend/tests/test_dialogs.py`
- Add: `docs/superpowers/notes/long-memory-agent/2026-05-23-phase193-agent-route-approval-opt-in-metadata.md`

## Success Criteria

- `build_dialog_agent_route(..., use_agent_approval_chain=True)` emits `{"use_agent_approval_chain": True}`.
- Default `build_dialog_agent_route(...)` output remains unchanged.
- `command_agent_route("setup")` remains unchanged.
- A pending action with `agent_route.use_agent_approval_chain=True` dispatches setup to `prepare_generate_setup_execution`.
- `agent_route` and derived `use_agent_approval_chain` are stripped from final tool params.
- If top-level `use_agent_approval_chain=False` is present, it overrides route metadata and keeps legacy dispatch.

## Non-Scope

- Do not enable approval-chain metadata by default for slash commands, text intent, or button actions.
- Do not change frontend pending action rendering.
- Do not execute generation tools.

## Tasks

### Task 1: RED Route Metadata Tests

- [x] Add tests in `backend/tests/test_dialogs.py` asserting:
  - default route output remains unchanged
  - explicit route metadata can request approval chain
  - dialog control plane consumes route metadata and routes setup to prepare wrapper
  - top-level false override keeps legacy route.
- [x] Run expected RED:

```powershell
pytest backend/tests/test_dialogs.py -k "agent_route_approval_opt_in" -q
```

Expected: route builder does not accept or emit metadata yet, and dispatch cannot derive opt-in from route metadata.

### Task 2: Implement Route Metadata Support

- [x] Update `build_dialog_agent_route` signature:

```python
def build_dialog_agent_route(
    action_type: str | None,
    *,
    source: DialogAgentRouteSource,
    command_name: str | None = None,
    use_agent_approval_chain: bool = False,
) -> dict[str, str | bool] | None:
```

- [x] Only include `route["use_agent_approval_chain"] = True` when the argument is exactly true.
- [x] Add helper in `dialog_control_plane.py`:

```python
def _agent_route_requests_approval_chain(params: dict[str, Any]) -> bool:
    route = params.get("agent_route")
    return isinstance(route, dict) and route.get(APPROVAL_CHAIN_OPT_IN_PARAM) is True
```

- [x] Before choosing tool name, derive `params[APPROVAL_CHAIN_OPT_IN_PARAM] = True` from route metadata only if the top-level key is absent.

### Task 3: GREEN Targeted Verification

- [x] Run:

```powershell
pytest backend/tests/test_dialogs.py -k "agent_route_approval_opt_in" -q
pytest backend/tests/test_dialogs.py -k "approval_chain_opt_in or agent_control_plane_routes_confirmed_setup_through_writing_agent_run" -q
python -m compileall backend/app/core backend/app/services/writing_agent
```

### Task 4: T2 Regression Slice

- [x] Run:

```powershell
pytest backend/tests/test_dialogs.py -q
pytest backend/tests/test_writing_agent_route_preference.py -q
pytest backend/tests/test_writing_agent_tool_executor.py -k "dialog_control_plane_projection or route_preference_projection" -q
```

### Task 5: Report, Hygiene, Commit, Push

- [x] Run:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

- [x] Write report:

```text
docs/superpowers/notes/long-memory-agent/2026-05-23-phase193-agent-route-approval-opt-in-metadata.md
```

- [ ] Commit and push:

```powershell
git add backend/app/core/dialog_agent_routes.py backend/app/services/writing_agent/dialog_control_plane.py backend/tests/test_dialogs.py docs/superpowers/plans/long-memory-agent/2026-05-23-phase193-agent-route-approval-opt-in-metadata.md docs/superpowers/notes/long-memory-agent/2026-05-23-phase193-agent-route-approval-opt-in-metadata.md
git commit -m "feat: route dialog approval opt in metadata"
git push origin main
```
