# Phase30 Report: `/status` 返回 Agent Health Projection

## 完成内容

- `/status` 不再转译为普通文本意图“接下来做什么”。
- 新增 `_handle_status_command()`，直接调用现有 `inspect_agent_health_projection()`。
- `/status` 响应现在包含：
  - `message_type="command"`
  - `meta.command_name="status"`
  - `meta.agent_health_projection`
  - `ui_hint.active_action.reason="Agent 状态"`
- 响应正文包含 Agent 状态、诊断项数量、重点问题和建议工具。

## RED 证据

- `pytest backend/tests/test_dialogs.py -k "status_command_routes_through_agent_health_projection" -q` 初始失败：
  - 期望 `message_type == "command"`，实际为 `None`。
  - 说明 `/status` 仍走普通诊断路径。

## 修复说明

- 在 command 分支中，命令可用性检查之后优先处理 `/status`。
- health projection 复用既有服务：
  - `inspect_agent_health_projection`
  - `writing_agent_tool_adapter_metadata_by_name`
  - `static_writing_agent_tool_adapter_names`
  - `SUPPORTED_ACTION_EXECUTION_TYPES`
- 未创建 pending action，未改变写作数据。

## 验证证据

- `pytest backend/tests/test_dialogs.py -k "status_command_routes_through_agent_health_projection" -q`
  - `1 passed, 102 deselected`
- `pytest backend/tests/test_dialogs.py -k "status_command or chat_command or continue_command_routes_through_low_detail_agent_continue or unavailable_agent_command" -q`
  - `5 passed, 98 deselected`
- `pytest backend/tests/test_agent_command_catalog.py -q`
  - `3 passed`
- `git diff --check`
  - passed with existing warning: `backend/tests/test_writing_agent_runs.py` CRLF will be replaced by LF.

## 下一阶段建议

Phase31 可以继续把 `meta.agent_health_projection` 做成前端可读卡片，包括：

1. 状态标签：就绪、部分降级、需要处理。
2. 诊断项列表。
3. 推荐下一步工具列表。

这样 `/status` 才会从“文本命令”进一步变成 Agent 控制台入口。
