# Phase30: `/status` 返回 Agent Health Projection

## 背景

Phase27 中 `/status` 已声明依赖 `inspect_agent_health_projection`，但实际 `chat` 执行路径仍把它转译为普通文本意图“接下来做什么”，最终得到项目诊断文本。这与命令目录的能力声明不一致。

Agent 化后，`/status` 应成为 Agent 自解释入口，而不是普通聊天诊断别名。

## 假设

- `/status` 是只读命令，不创建 pending action。
- `/status` 应直接调用现有 `inspect_agent_health_projection` service，而不是重新实现健康检查。
- 本阶段先返回文本摘要 + 结构化 `meta.agent_health_projection`，前端 health card 后续再做。

## 成功标准

1. `/status` 响应 `message_type="command"`。
2. 响应 `meta.command_name="status"`。
3. 响应 `meta.agent_health_projection.version == "phase218.agent_health_projection.v1"`。
4. 响应文本包含 Agent 状态、诊断项数量和必要的问题摘要。
5. 不创建 pending action，不改变项目内容。

## TDD 计划

1. 后端 RED：修改 `/status` 测试，期望 health projection meta，而不是普通项目诊断文本。
2. 实现 `_handle_status_command()`。
3. 在命令分支中优先处理 `/status`，早于 `agent_intent_text` 转译。
4. T0/T1 验证 dialog status、command catalog 和 typecheck。

## 验证

- T0: `pytest backend/tests/test_dialogs.py -k "status_command_routes_through_agent_health_projection" -q`
- T1: `pytest backend/tests/test_dialogs.py -k "status_command or chat_command" -q`
- T0: `pytest backend/tests/test_agent_command_catalog.py -q`
- T0: `git diff --check`

## 非目标

- 不做前端 Agent health card。
- 不改变 `/continue` 路由。
- 不新增 Agent 工具。
