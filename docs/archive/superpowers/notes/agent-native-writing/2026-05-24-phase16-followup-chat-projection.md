# Phase16 Report: Follow-up Chat Projection

## 本阶段目标

让 `plan_recommended_followups` 成为对话层可识别的 Agent run action，并在 action result view 中展示推荐后继的读写分离摘要。

## 实现内容

- `agentRunProjection.ts` 新增 `plan_recommended_followups` action type 和 descriptor。
- 新增推荐后继预览 action result view：
  - 推荐状态；
  - 自动后继工具数量；
  - 需确认修复工具数量；
  - 来源运行短 ID。
- 对话卡片不展示工具参数和具体写工具名，避免泄露内部细节。

## 设计取舍

- Drawer 展示具体工具名；对话卡片只展示数量和状态，保持聊天流简洁。
- `provenance_write_tools` 仍不生成执行入口，只作为“需确认修复”摘要。
- 保持未知 action type 过滤逻辑不变。

## 验证

- RED: `npm run test:unit -- agentRunProjection.test.ts -t recommended`
  - 初始失败：`plan_recommended_followups` 未注册，view 为 `undefined`。
- GREEN: `npm run test:unit -- agentRunProjection.test.ts -t recommended`
  - 结果：`1 passed, 36 skipped`
- T1: `npm run test:unit -- agentRunProjection.test.ts`
  - 结果：`37 passed`

## 后续建议

下一阶段应检查后端 action_result 是否已经把 `plan_recommended_followups` 类型和 run id 透传到 Hermes 对话消息。如果没有，需要补一条端到端投影测试，确保用户实际聊天流能看到该卡片。
