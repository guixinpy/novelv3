# Phase35: Command Menu Agent Contracts Report

## 目标

把 Phase34 的命令目录契约转成 Hermes `/` 命令候选中的可见信息，让用户在执行前知道命令的 Agent 角色、结果类型和能力依赖规模。

## 变更

- 新增 `CommandMenu.test.ts`，覆盖 Agent 命令候选标签。
- `CommandMenu.vue` 新增命令元信息行：
  - 分类：`Agent 控制`、`会话`、`兼容`
  - 结果：`继续控制`、`状态诊断`
  - 能力依赖数量：例如 `4 项能力`
- UI 不显示 raw projection id，例如 `continue_agent_control`。
- 未改变 ChatInput 的命令过滤、选择、键盘导航和 pending action 限制。

## RED 证据

- `.\node_modules\.bin\vitest.cmd run src/components/chat/CommandMenu.test.ts`
  - 失败原因：候选文本中缺少 `Agent 控制`

## GREEN 证据

- `.\node_modules\.bin\vitest.cmd run src/components/chat/CommandMenu.test.ts src/components/workspace/chatCommands.test.ts`
  - `10 passed`
- `.\node_modules\.bin\vue-tsc.cmd --noEmit`
  - passed
- `git diff --check`
  - passed；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

下一步可以把 `control_projection_type` 写入命令执行 Trace，让命令目录、运行时投影和审计链路形成同一个 Agent 控制面契约。
