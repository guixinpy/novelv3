# Phase36: Command Projection Trace Report

## 目标

把命令目录中的 `control_projection_type` 接入 slash `/continue` 的后端审计链路，使命令目录、前端候选、运行时控制投影和 Trace 能用同一个字段串起来。

## 变更

- `chat_commands.py` 新增 `command_control_projection_type(command_name)`。
- `dialogs.py` 在记录 `dialog_route_decision` Trace 时：
  - 保留原有 `dialog_route_decision`
  - 保留原有 `agent_control`
  - 当 `agent_control.command_name` 能解析到投影类型时写入 `control_projection_type`
- 普通文本低细节继续不会写入 `control_projection_type`。

## RED 证据

- `pytest backend/tests/test_dialogs.py -k "continue_command_routes_through_low_detail_agent_continue or chat_text_low_detail_continue_creates_pending_chapter_action" -q`
  - 失败原因：slash `/continue` 的 route trace 缺少 `control_projection_type`

## GREEN 证据

- `pytest backend/tests/test_dialogs.py -k "continue_command_routes_through_low_detail_agent_continue or chat_text_low_detail_continue_creates_pending_chapter_action" -q`
  - `2 passed, 101 deselected`
- `git diff --check`
  - passed；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

下一阶段可以把命令控制契约用于 Agent 运行输入或后续工具推荐，让 `/continue` 的选择依据不只存在于对话层，也能进入 Agent run 的可复盘输入。
