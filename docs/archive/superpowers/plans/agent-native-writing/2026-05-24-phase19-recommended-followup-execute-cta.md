# Phase19: 推荐后继确认执行入口

## 背景

Phase18 让 Hermes 能把低细节“继续”转换为 `plan_recommended_followups` 预览，但用户仍缺少从预览进入确认执行的前端入口。后端 `WritingAgentRunService` 已支持 `execute_recommended_followups + confirm_execute + recommended_followup_plan_hash`，本阶段只补用户可操作桥接。

## 目标

1. `AgentRunDrawer` 在推荐后继预览包含 `source_run_id`、`plan_hash` 和可自动执行工具时显示“确认执行后继”。
2. 点击后向父组件发出 `{ sourceRunId, planHash }`，不泄露 hash 到聊天文案。
3. `HermesView` 使用 `api.createAgentRun` 创建 `ui_recommended_followup_execute` run：
   - `auto_plan: true`
   - `recommended_followup_run_id`
   - `execute_recommended_followups: true`
   - `confirm_execute: true`
   - `recommended_followup_plan_hash`
4. 聊天窗口追加系统反馈，能从反馈打开对应 Agent run。

## 参考项目取舍

此处延续三个参考项目中“显式确认再执行”的安全边界，但落到 novelv3 的既有 plan_hash 契约上。不新增独立 permission 系统，也不把推荐后继变成自动执行，避免对写作状态产生不可审计副作用。

## 验证

1. RED：
   - `npm run test:unit -- AgentRunDrawer.test.ts -t recommended`
   - `npm run test:unit -- HermesView.test.ts -t recommended`
2. GREEN：
   - 目标测试通过。
3. T1：
   - `npm run test:unit -- AgentRunDrawer.test.ts HermesView.test.ts agentRunProjection.test.ts`

## 非目标

- 不改变后端执行确认策略。
- 不处理 confirmation-only 写入修复工具的批量确认。
- 不新增独立对话命令。
