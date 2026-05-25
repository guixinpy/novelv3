# Phase37: Command Runtime Projection Meta Report

## 目标

让命令运行时响应也暴露 `control_projection_type`，使目录、前端候选、响应 meta、pending action params 和 Trace 使用同一契约字段。

## 变更

- `/continue` 响应 `meta.control_projection_type` 现在为 `continue_agent_control`。
- `/continue` 生成的 pending action params 现在包含 `control_projection_type: "continue_agent_control"`。
- `/status` 响应 `meta.control_projection_type` 现在为 `agent_health_projection`。
- `agent_control` 和 `agent_health_projection` 原有结构不变。

## RED 证据

- `pytest backend/tests/test_dialogs.py -k "continue_command_routes_through_low_detail_agent_continue or status_command_routes_through_agent_health_projection" -q`
  - 失败原因：响应 meta 中缺少 `control_projection_type`

## GREEN 证据

- `pytest backend/tests/test_dialogs.py -k "continue_command_routes_through_low_detail_agent_continue or status_command_routes_through_agent_health_projection" -q`
  - `2 passed, 101 deselected`
- `git diff --check`
  - passed；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

下一阶段可以把 `control_projection_type` 用于前端消息卡片的 data-testid 或内部分支判断，减少靠结构存在性推断卡片类型的逻辑。
