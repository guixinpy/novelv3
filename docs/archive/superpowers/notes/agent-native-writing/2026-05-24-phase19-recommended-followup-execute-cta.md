# Phase19 报告：推荐后继确认执行入口

## 完成内容

1. `AgentRunDrawer` 在 `plan_recommended_followups` 预览包含可执行自动后继工具、`source_run_id` 和 `plan_hash` 时显示“确认执行后继”。
2. 点击后发出 `executeRecommendedFollowups`，payload 只包含 `sourceRunId` 和 `planHash`。
3. `HermesView` 接收该事件后创建 `ui_recommended_followup_execute` run，输入包含：
   - `auto_plan: true`
   - `recommended_followup_run_id`
   - `execute_recommended_followups: true`
   - `confirm_execute: true`
   - `recommended_followup_plan_hash`
4. 聊天系统增加推荐后继执行反馈：`ui_recommended_followup_execute`，文案不暴露 plan hash。

## 参考项目取舍记录

本阶段吸收参考 Agent 项目中的“建议与执行分离”模式：推荐后继只是可审计建议，执行必须经过显式确认。novelv3 的适配方式是复用现有 plan_hash 与 Agent run 审计链，而不是引入外部项目的独立权限系统。

## 验证

RED：

```powershell
npm run test:unit -- AgentRunDrawer.test.ts -t "confirmed recommended"
npm run test:unit -- HermesView.test.ts -t "recommended followup execution"
```

结果：

- Drawer 失败：找不到 `execute-recommended-followups` 按钮。
- HermesView 失败：`createAgentRun` 未被调用。

GREEN：

```powershell
npm run test:unit -- AgentRunDrawer.test.ts -t "confirmed recommended"
npm run test:unit -- HermesView.test.ts -t "recommended followup execution"
```

结果：

- `AgentRunDrawer.test.ts`: `1 passed, 12 skipped`
- `HermesView.test.ts`: `1 passed, 8 skipped`

T1：

```powershell
npm run test:unit -- AgentRunDrawer.test.ts HermesView.test.ts agentRunProjection.test.ts
```

结果：`3 passed`, `59 passed`。

T2：

```powershell
npm run build
```

结果：`vue-tsc --noEmit && vite build` 成功，245 modules transformed。

## 下一阶段建议

1. 给“继续”路由增加选择原因投影，用户能看到为什么当前走恢复、后继或章节生成。
2. 为 confirmation-only 后继工具设计独立确认流程，避免和自动诊断后继混在一个按钮中执行。
