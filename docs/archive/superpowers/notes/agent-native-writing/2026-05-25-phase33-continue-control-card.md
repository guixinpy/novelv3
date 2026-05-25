# Phase33 Report: `/continue` Agent Control Card

## 完成内容

- `ChatMessage.vue` 现在会在 `msg.meta.agent_control` 存在时展示 Agent control card。
- card 展示：
  - 命令名，例如 `/continue`
  - 决策中文标签：恢复阻塞、推荐后继、生成下一章
  - 原因中文标签：发现可恢复运行、存在推荐后继、无恢复或推荐后继
  - 最多 4 个 required Agent tools
- 样式沿用现有聊天气泡 token，使用紧凑工作台风格，不新增组件。

## RED 证据

- `.\node_modules\.bin\vitest.cmd run src/components/chat/ChatMessage.test.ts` 初始失败：
  - 找不到 `[data-testid="agent-control-card"]`。
  - 说明前端未消费 `agent_control`。

## 验证证据

- `.\node_modules\.bin\vitest.cmd run src/components/chat/ChatMessage.test.ts`
  - `26 passed`
- `.\node_modules\.bin\vue-tsc.cmd --noEmit`
  - passed
- `git diff --check`
  - passed with existing warning: `backend/tests/test_writing_agent_runs.py` CRLF will be replaced by LF.

## 下一阶段建议

Phase34 可以把 control projection 进一步泛化：

1. 抽象通用 command control projection 类型，不只服务 `/continue`。
2. 为后续 Agent-native 命令预留 `/plan`、`/review`、`/memory` 的统一控制面。
3. 后端 command catalog 可增加 `control_projection_type`，前端根据类型复用 control card。
