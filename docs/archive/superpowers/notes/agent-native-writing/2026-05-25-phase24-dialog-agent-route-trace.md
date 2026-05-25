# Phase24: 文本意图与 Slash Command 路由 Trace 报告

## 目标

把普通文本意图与 slash command 创建 pending action 的 Agent 路由写入 Trace，避免旧对话入口继续游离在 Agent 审计链之外。

## 参考项目取舍

- 采纳 `openhuman` 的“用户输入到领域动作需要显式事件”的思路，但没有引入事件总线。
- 采纳 `hermes-agent` 对 tool usage 可统计的思路，把 route-to-tool 的选择也变成可统计 Trace。
- 采纳 `openclaw` 对用户命令、工具调用、使用痕迹关联的方向，但本阶段只补后端 Trace，不做前端可视化。

## 改动

1. `backend/app/api/dialogs.py`
   - 新增 `_record_dialog_agent_route_trace`。
   - Slash command pending action 会写入 `dialog_agent_route` Trace。
   - 普通文本意图 pending action 会写入 `dialog_agent_route` Trace。
   - 低细节“继续”仍使用 Phase23 的 `dialog_route_decision` Trace，避免重复记录。

2. `backend/tests/test_dialogs.py`
   - `/setup` 命令路径断言 `dialog_agent_route` Trace。
   - 文本意图“创建主角设定”路径断言 `dialog_agent_route` Trace。

## 验证

- RED：`pytest backend/tests/test_dialogs.py -k "agent_control_plane_routes_confirmed_setup_through_writing_agent_run or chat_text_that_matches_action_intent_creates_pending_action" -q`
  - 失败原因：两条路径均查不到 `dialog_agent_route` Trace。
- GREEN：同一命令通过，`2 passed`。
- T1：`pytest backend/tests/test_dialogs.py -k "chat_command_registry_helpers or agent_route_approval_opt_in or chapter_command_leading_index or agent_control_plane_routes_confirmed_setup_through_writing_agent_run or chat_text_that_matches_action_intent_creates_pending_action or low_detail_continue" -q`
  - `12 passed`
- T2：`pytest backend/tests/test_model_call_traces.py -k "create_trace_sanitizes_context_blocks_and_trace_metadata or list_model_call_traces_filters_by_trace_type" -q`
  - `2 passed`

## 后续调整

用户提醒 `/` 命令不应再以显式模块调用为主。Phase25 将执行兼容迁移：新 `/` 命令面向 Agent 控制面；旧 `setup/storyline/outline/chapter` 保留兼容别名，但不作为推荐入口。
