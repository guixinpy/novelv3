# Phase193 Agent Route Approval Opt-In Metadata Report

## Scope

把 Phase192 的 `use_agent_approval_chain` opt-in 接到 `agent_route` metadata 上，使内部 Agent route 能显式选择 approval prepare wrapper，同时普通 slash/text/button 路由默认不变。

## Implementation

- 在 `dialog_agent_routes.py` 增加：
  - `DIALOG_AGENT_ROUTE_APPROVAL_CHAIN_OPT_IN_KEY`
  - `build_dialog_agent_route(..., use_agent_approval_chain=False)`
- `build_dialog_agent_route` 只有在显式 `use_agent_approval_chain is True` 时才写入 route metadata。
- `command_agent_route("setup")` 等默认输出保持不变。
- 在 `dialog_control_plane.py` 增加 `_agent_route_requests_approval_chain`。
- `_tool_request_for_action` 在顶层 `use_agent_approval_chain` 不存在时，才从 `agent_route.use_agent_approval_chain=True` 派生 opt-in。
- 顶层 `use_agent_approval_chain=False` 保持最高优先级，可覆盖 route metadata。
- `agent_route` 与派生控制字段继续从最终 tool params 剥离。

## Subagent Review

Explorer `019e543b-6871-70e1-ae03-3a38da84013c` 做了只读链路检查，结论与实现一致：

- `agent_route` 的真实构造点是 `build_dialog_agent_route` 与 `command_agent_route`。
- pending action 持久化在 `backend/app/api/dialogs.py::chat` 的 command/text/button 分支。
- resolve-action 原样把 `pending.params` 传给 `prepare_dialog_agent_run_dispatch`。
- 安全接入点应在 `dialog_control_plane.py`，只从显式 metadata 派生，不能从 route 存在本身推断。

## Behavior

- 默认 `build_dialog_agent_route("preview_setup", source="slash_command", command_name="setup")` 不包含 `use_agent_approval_chain`。
- 显式 `build_dialog_agent_route(..., use_agent_approval_chain=True)` 会写入 `use_agent_approval_chain=True`。
- route metadata opt-in 的 setup dispatch 到 `prepare_generate_setup_execution`。
- 顶层 `use_agent_approval_chain=False` 覆盖 route metadata，setup 仍 dispatch 到 `generate_setup`。

## Validation

RED:

```powershell
pytest backend/tests/test_dialogs.py -k "agent_route_approval_opt_in" -q
# 3 failed, 83 deselected
# failure reason: build_dialog_agent_route did not accept use_agent_approval_chain
```

GREEN / T1:

```powershell
pytest backend/tests/test_dialogs.py -k "agent_route_approval_opt_in" -q
# 3 passed, 83 deselected

pytest backend/tests/test_dialogs.py -k "approval_chain_opt_in or agent_control_plane_routes_confirmed_setup_through_writing_agent_run" -q
# 5 passed, 81 deselected

python -m compileall backend/app/core backend/app/services/writing_agent
# exit 0
```

T2:

```powershell
pytest backend/tests/test_dialogs.py -q
# 86 passed

pytest backend/tests/test_writing_agent_route_preference.py -q
# 5 passed

pytest backend/tests/test_writing_agent_tool_executor.py -k "dialog_control_plane_projection or route_preference_projection" -q
# 4 passed, 114 deselected
```

Hygiene:

```powershell
git diff --check
# exit 0

rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
# exit 1, no matches
```

## Novel Progress

本阶段未推进小说正文生成。原因：Phase193 是 Agent route metadata 到 control plane 的接入阶段，目标是把旧模块逐步工具化并提供可控迁移入口。

## Next Phase

建议 Phase194 增加 route projection 对 opt-in metadata 的可观测能力：

- `inspect_agent_route_preference_projection` 能展示某条 route 是否已经声明 approval-chain opt-in。
- 区分 `recommended_not_applied` 与 `opt_in_available` / `opt_in_declared`。
- 仍不默认改变 runtime route。

## Git

- Main commit: `59d15948 feat: route dialog approval opt in metadata`
- Remote: pushed to `origin/main`
