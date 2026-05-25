# Phase36: Command Projection Trace

## 背景

Phase34 和 Phase35 已经让命令目录与前端候选知道 `/continue` 会产生 `continue_agent_control`。但后端 Trace 当前只记录 `dialog_route_decision` 和 `agent_control` 本体，缺少目录契约字段，审计时无法直接按“控制投影类型”检索或聚合命令执行。

本阶段把 `control_projection_type` 写入 slash `/continue` 的路由决策 Trace。

## 成功标准

1. slash `/continue` 触发章节生成路由时，`dialog_route_decision` Trace 包含 `control_projection_type: "continue_agent_control"`。
2. Trace 仍保留原有 `dialog_route_decision` 和 `agent_control`。
3. 普通文本“继续吧”不产生该字段，避免把 slash 命令契约误套到自然语言路由。

## TDD 计划

1. 后端 RED：扩展 `/continue` 命令测试，断言最新 `dialog_route_decision` Trace 含 `control_projection_type`。
2. 后端实现：在 `_record_dialog_route_decision_trace` 写入 `agent_control["control_projection_type"]` 或由 `agent_control` 推导的固定值。
3. 运行相关测试：
   - `pytest backend/tests/test_dialogs.py -k "continue_command_routes_through_low_detail_agent_continue or chat_text_low_detail_continue_creates_pending_chapter_action" -q`
   - `git diff --check`

## 非目标

- 不新增 Trace 类型。
- 不改变 `/status` 响应；它没有 `dialog_route_decision` Trace。
- 不改变 pending action 结构。
