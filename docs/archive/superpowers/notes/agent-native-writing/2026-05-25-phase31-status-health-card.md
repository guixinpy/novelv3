# Phase31 Report: `/status` Agent Health Card

## 完成内容

- `ChatMessage.vue` 会在 `meta.agent_health_projection` 存在时渲染 Agent health card。
- health card 展示：
  - 状态中文标签：就绪、部分降级、需要处理、未知。
  - 最多 3 条诊断信息。
  - 最多 5 个推荐工具。
- 正文摘要仍保留，卡片只作为结构化补充展示。
- 不可用命令 feedback 和普通消息渲染不受影响。

## RED 证据

- `.\node_modules\.bin\vitest.cmd run src/components/chat/ChatMessage.test.ts` 初始失败：
  - 找不到 `[data-testid="agent-health-card"]`。
  - 说明前端未消费 `agent_health_projection`。

## 验证证据

- `.\node_modules\.bin\vitest.cmd run src/components/chat/ChatMessage.test.ts`
  - `25 passed`
- `.\node_modules\.bin\vue-tsc.cmd --noEmit`
  - passed
- `git diff --check`
  - passed with existing warning: `backend/tests/test_writing_agent_runs.py` CRLF will be replaced by LF.

## 下一阶段建议

Phase32 可以转向 Agent 控制面更核心的部分：

1. 将 `/continue` 的文本意图路由进一步收束为显式 Agent control action。
2. 或者把 `CommandMenu` 增加灰态不可用项展示，用于解释命令为什么暂时不可用。
3. 优先建议推进 `/continue`，因为它是用户最高频的 Agent 主入口。
