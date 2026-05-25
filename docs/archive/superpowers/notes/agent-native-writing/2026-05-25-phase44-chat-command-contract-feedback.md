# Phase44: Chat Command Contract Feedback Report

## 目标

让聊天侧 Agent run feedback 卡片复用 `agent_command_contracts` 摘要，减少用户打开运行抽屉查看命令控制面健康的成本。

## 变更

- `agentRunProjection.ts` 的共享 Agent 摘要入口新增命令契约 detail items：
  - `命令契约: 已投影`
  - `控制命令: N 个`
  - `契约缺口: N 个`
- `buildAgentRunExecutionFeedback(...)` 可在 run 详情包含 `agent_command_contracts` 时展示该摘要。
- 不把 `source` 或完整命令清单写入聊天卡片，避免泄露内部 trace 路径和冗长列表。

## RED 证据

- `cd frontend; .\node_modules\.bin\vitest run src/components/chat/agentRunProjection.test.ts -t "builds recovery execution feedback without leaking plan hash"`
  - 失败原因：`detail_items` 缺少 `{ label: '命令契约', value: '已投影' }`。

## GREEN 证据

- `cd frontend; .\node_modules\.bin\vitest run src/components/chat/agentRunProjection.test.ts -t "builds recovery execution feedback without leaking plan hash"`
  - `1 passed, 36 skipped`
- `cd frontend; .\node_modules\.bin\vitest run src/components/chat/agentRunProjection.test.ts`
  - `37 passed`
- `cd frontend; .\node_modules\.bin\vue-tsc --noEmit`
  - 通过
- `git diff --check`
  - 通过；仅保留既有提示：`backend/tests/test_writing_agent_runs.py` CRLF 将被 Git 转为 LF。

## 下一阶段建议

下一步可以做服务端 `action_result_view` 的同类摘要投影，使历史消息从后端重建时也能保持命令契约 detail items 一致。
