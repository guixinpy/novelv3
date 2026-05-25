# Phase34: Command Control Projection Contract Report

## 目标

把 `/continue` 和 `/status` 的运行时结构化控制投影上移到命令目录，使前端和未来 Agent 控制面能在执行前发现命令会返回哪类投影。

## 变更

- 后端 `ChatCommandSpec` 增加 `control_projection_type`。
- 后端命令目录每条命令稳定输出 `control_projection_type`：
  - `/continue`: `continue_agent_control`
  - `/status`: `agent_health_projection`
  - session / legacy alias: 空字符串
- 前端 API 类型、workspace 命令定义和 normalize 逻辑增加 `controlProjectionType`。
- 前端静态 fallback 命令注册表同步声明 `/continue` 和 `/status` 的投影类型。

## RED 证据

- `pytest backend/tests/test_agent_command_catalog.py backend/tests/test_dialogs.py -k "agent_command_catalog or chat_command_catalog_endpoint_returns_agent_control_surface" -q`
  - 失败原因：`KeyError: 'control_projection_type'`
- `.\node_modules\.bin\vitest.cmd run src/components/workspace/chatCommands.test.ts`
  - 失败原因：normalize 结果缺少 `controlProjectionType`

## GREEN 证据

- `pytest backend/tests/test_agent_command_catalog.py backend/tests/test_dialogs.py -k "agent_command_catalog or chat_command_catalog_endpoint_returns_agent_control_surface" -q`
  - `4 passed, 102 deselected`
- `.\node_modules\.bin\vitest.cmd run src/components/workspace/chatCommands.test.ts`
  - `9 passed`
- `.\node_modules\.bin\vue-tsc.cmd --noEmit`
  - passed
- `git diff --check`
  - passed；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

命令目录现在已经能声明“命令依赖哪些 Agent 工具”和“命令会产生哪类控制投影”。下一阶段可以继续把这些契约用于运行时 Trace 或 Hermes 命令候选说明，让用户在输入 `/` 时直接看到 Agent 将如何编排工具与反馈结果。
