# Phase37: Command Runtime Projection Meta

## 背景

Phase34 到 Phase36 已经让 `control_projection_type` 出现在命令目录、前端候选和 `/continue` Trace 中。但运行时响应 `meta` 仍需要通过 `agent_control` 或 `agent_health_projection` 推断投影类型，前端消息层和 pending action 层没有同一个稳定字段。

本阶段把 `control_projection_type` 写入命令响应 meta，并在 `/continue` pending action params 中保留同一字段。

## 成功标准

1. `/continue` 响应 `meta.control_projection_type` 为 `continue_agent_control`。
2. `/continue` 生成的 pending action params 包含 `control_projection_type: "continue_agent_control"`。
3. `/status` 响应 `meta.control_projection_type` 为 `agent_health_projection`。
4. 不改变 `agent_control` 和 `agent_health_projection` 的既有结构。

## TDD 计划

1. 后端 RED：扩展 `/continue` 和 `/status` 测试，断言响应 meta 与 pending action params 中的投影类型。
2. 后端实现：
   - `_assistant_continue_meta` 从 `agent_control.command_name` 查询 `command_control_projection_type`
   - `/continue` pending action params 同步写入该字段
   - `_handle_status_command` 写入 `command_control_projection_type("status")`
3. 验证：
   - `pytest backend/tests/test_dialogs.py -k "continue_command_routes_through_low_detail_agent_continue or status_command_routes_through_agent_health_projection" -q`
   - `git diff --check`

## 非目标

- 不调整前端卡片。
- 不改命令目录字段名。
- 不改 Agent 工具选择逻辑。
