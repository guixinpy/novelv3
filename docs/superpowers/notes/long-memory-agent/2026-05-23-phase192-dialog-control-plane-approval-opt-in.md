# Phase192 Dialog Control Plane Approval Opt-In Report

## Scope

为 dialog pending action 增加显式 opt-in 路由，使 setup/storyline/outline 可以选择先进入 Agent approval prepare wrapper，同时保持默认 runtime 行为不变。

## Implementation

- 新增 `APPROVAL_CHAIN_OPT_IN_PARAM = "use_agent_approval_chain"`。
- 将 `use_agent_approval_chain` 加入 `CONTROL_PLANE_PARAM_KEYS`，确保该控制字段不透传到底层工具。
- 调整 `_tool_request_for_action` 的顺序：
  - 先基于原始 params 选择 tool。
  - 再剥离 control-plane params。
- 调整 `_tool_name_for_action`：
  - `generate_chapter` 的审批契约 execute 路径优先级不变。
  - setup/storyline/outline 仅在 `use_agent_approval_chain is True` 时切到 recommended prepare wrapper。
  - 默认仍返回 legacy action tool。

## Behavior

- 默认 setup confirmation 仍 dispatch 到 `generate_setup`。
- opt-in setup dispatch 到 `prepare_generate_setup_execution`。
- opt-in storyline dispatch 到 `prepare_generate_storyline_execution`。
- opt-in outline dispatch 到 `prepare_generate_outline_execution`。
- `project_id`、`agent_route`、`use_agent_approval_chain` 均不会进入 tool params。
- chapter prepare/execute 路径未改变。

## Validation

RED:

```powershell
pytest backend/tests/test_dialogs.py -k "approval_chain_opt_in" -q
# 4 failed, 79 deselected
# failure reasons:
# - use_agent_approval_chain was still present in params
# - opt-in setup/storyline/outline still routed to legacy tools
```

GREEN / T1:

```powershell
pytest backend/tests/test_dialogs.py -k "approval_chain_opt_in" -q
# 4 passed, 79 deselected

pytest backend/tests/test_dialogs.py -k "agent_control_plane_routes_confirmed_setup_through_writing_agent_run or resolve_chapter_action_confirm_dispatches_prepare_tool or chapter_approval_followup_dispatches_execute_tool" -q
# 3 passed, 80 deselected

python -m compileall backend/app/services/writing_agent
# exit 0
```

T2:

```powershell
pytest backend/tests/test_dialogs.py -q
# 83 passed

pytest backend/tests/test_writing_agent_tool_executor.py -k "dialog_control_plane_projection or route_preference_projection or prepare_generate_setup_execution or prepare_generate_storyline_execution or prepare_generate_outline_execution" -q
# 7 passed, 111 deselected
```

Hygiene:

```powershell
git diff --check
# exit 0

rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
# exit 1, no matches
```

## Novel Progress

本阶段未推进小说正文生成。原因：Phase192 是对话入口的低风险 guarded migration 阶段，重点是让 Agent 能在显式 opt-in 下调用审批包装工具链，而不是扩大创作内容。

## Next Phase

建议 Phase193 做 dialog pending action 的 opt-in 来源接入：

- 让内部 Agent route metadata 可以安全设置 `use_agent_approval_chain`。
- 仍保持用户普通确认路径默认 legacy。
- 先从命令或 route metadata 的只读/显式入口开始，不直接改所有文本意图。
