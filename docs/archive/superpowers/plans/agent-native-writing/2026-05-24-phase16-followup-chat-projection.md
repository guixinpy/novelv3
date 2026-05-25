# Phase16: Follow-up Chat Projection

## 背景

Phase15 已在 Agent run drawer 中展示推荐后继的读写分离信息。但 novelv3 的目标是对话驱动 Agent，用户不应必须打开 drawer 才知道 Agent 的下一步边界。`plan_recommended_followups` 作为 Agent 编排工具，应在 chat action result projection 中具备一等展示。

## 假设

- `plan_recommended_followups` 是只读 preview 工具。
- chat projection 只展示摘要，不暴露 params 和 plan hash。
- 写工具仍只作为“需确认修复”计数展示，不提供执行入口。

## 目标

1. `plan_recommended_followups` 成为受支持的 Agent run action type。
2. 对话 action result view 展示：
   - 推荐状态；
   - 自动后继工具数量；
   - 需确认修复工具数量。
3. 未知 action type 的过滤逻辑保持不变。

## 验证

- T0: `npm run test:unit -- agentRunProjection.test.ts -t recommended`
- T1: `npm run test:unit -- agentRunProjection.test.ts`

## 风险控制

- 只改投影层，不改 API、不改执行流程。
- 不展示工具参数，避免对话卡片泄露内部细节。
