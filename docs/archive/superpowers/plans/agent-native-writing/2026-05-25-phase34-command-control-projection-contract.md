# Phase34: Command Control Projection Contract

## 背景

Phase30 到 Phase33 已经让 `/status` 产生 `agent_health_projection`、让 slash `/continue` 产生 `agent_control`，并在前端展示对应卡片。但命令目录目前只描述能力、依赖工具和可用性，调用方无法从目录层面知道某条 Agent 命令执行后会返回哪类结构化投影。

本阶段把控制投影类型上移到命令目录，作为 Agent 命令控制面的可发现契约。

## 成功标准

1. 后端 `/api/v1/dialog/chat-commands` 的每个命令条目包含 `control_projection_type` 字段。
2. `/continue` 暴露 `control_projection_type: "continue_agent_control"`。
3. `/status` 暴露 `control_projection_type: "agent_health_projection"`。
4. 会话命令和 legacy alias 使用空字符串，保持稳定字段而不暗示结构化控制投影。
5. 前端 `ChatCommandDefinition` 和后端目录规范化逻辑保留该字段为 `controlProjectionType`。

## TDD 计划

1. 后端 RED：扩展 `test_agent_command_catalog.py` 和 `test_dialogs.py` 中的命令目录断言，确认 `control_projection_type` 尚未出现时失败。
2. 前端 RED：扩展 `chatCommands.test.ts`，确认 normalize 后缺少 `controlProjectionType` 时失败。
3. 后端实现：在 `ChatCommandSpec` 增加 `control_projection_type`，并由 `_chat_command_catalog_item` 输出稳定字段。
4. 前端实现：在 API 类型、workspace 命令类型和 normalize 映射中加入 `controlProjectionType`。
5. 验证：
   - `pytest backend/tests/test_agent_command_catalog.py backend/tests/test_dialogs.py -k "agent_command_catalog or chat_command_catalog_endpoint_returns_agent_control_surface" -q`
   - `.\node_modules\.bin\vitest.cmd run src/components/workspace/chatCommands.test.ts`
   - `.\node_modules\.bin\vue-tsc.cmd --noEmit`
   - `git diff --check`

## 非目标

- 不改变 `/continue` 或 `/status` 的执行逻辑。
- 不新增新的 slash 命令。
- 不改聊天卡片 UI。
