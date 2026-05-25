# Phase33: `/continue` Agent Control Card

## 背景

Phase32 已经让 slash `/continue` 在后端产生 `meta.agent_control`，但前端仍不会展示这个控制投影。用户只能看到普通待确认动作，无法知道 Agent 为什么选择“恢复阻塞 / 推荐后继 / 生成下一章”。

本阶段把 `agent_control` 作为聊天消息的结构化状态块展示，继续保持现有 Hermes 聊天气泡的紧凑工作台风格。

## 成功标准

1. `ChatMessage.vue` 在 `msg.meta.agent_control` 存在时展示 `agent-control-card`。
2. 展示：
   - 命令名，例如 `/continue`
   - 决策：恢复阻塞、推荐后继、生成下一章
   - 原因：可恢复运行、存在推荐后继、无恢复或后继
3. 展示最多 4 个 required Agent tools。
4. 不影响已有 command feedback、Agent health card、ActionCard。

## TDD 计划

1. 前端 RED：在 `ChatMessage.test.ts` 中新增 agent control card 测试。
2. 实现 computed：
   - `agentControlProjection`
   - `agentControlCommandLabel`
   - `agentControlRouteLabel`
   - `agentControlReasonLabel`
   - `agentControlRequiredTools`
3. 添加小块模板和 CSS。
4. 运行 `ChatMessage.test.ts`、`vue-tsc`、`git diff --check`。

## 非目标

- 不新增点击执行工具。
- 不改后端响应结构。
- 不改变 `/continue` 的 pending action。
