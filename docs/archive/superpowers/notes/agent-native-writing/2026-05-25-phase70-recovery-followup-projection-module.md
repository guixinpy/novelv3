# Phase70 Recovery Followup Projection Module Report

## Scope

拆分前端 Agent run 投影中的 recovery/followup 卡片与执行反馈逻辑，让 `agentRunProjection.ts` 更接近纯聚合入口。

本阶段覆盖 4 个 action type：

- `plan_recovery_tools`
- `plan_recommended_followups`
- `ui_recovery_execute`
- `ui_recommended_followup_execute`

## Changes

- 新增 `frontend/src/components/chat/recoveryAgentRunProjection.ts`
  - 导出 `RECOVERY_AGENT_RUN_ACTION_TYPES`
  - 导出 `RECOVERY_AGENT_RUN_ACTION_DESCRIPTORS`
  - 导出 `buildAgentRunExecutionFeedback`
  - 导出 `buildRecommendedFollowupExecutionFeedback`
  - 内聚 recovery/followup 视图构建、执行反馈、Agent 身份/工具面/控制平面摘要展示逻辑。
- 更新 `frontend/src/components/chat/agentRunProjection.ts`
  - 通过 spread 聚合 recovery action types/descriptors。
  - 重导出原有执行反馈函数与 `AgentRunFeedbackMessage` 类型，保持调用方 API 不变。
  - 保留 `getAgentRunIdFromMessage`、`isAgentRunActionType`、`getAgentRunActionDescriptor`、`buildAgentRunActionResultView` 作为聚合层职责。
- 更新 `frontend/src/components/chat/agentRunProjection.test.ts`
  - 新增 recovery 模块边界测试，验证 descriptors 与 feedback builder 均来自专门模块。

## TDD Evidence

RED:

```powershell
npm run test:unit -- agentRunProjection
```

结果：失败，原因是 `./recoveryAgentRunProjection` 不存在。

GREEN:

```powershell
npm run test:unit -- agentRunProjection
```

结果：`60 passed`。

## Verification

```powershell
npm run test:unit -- ChatMessage
```

结果：`29 passed`。

```powershell
npm run build
```

结果：TypeScript 与 Vite build 成功，`249 modules transformed`。

```powershell
git diff --check
```

结果：退出码 0；仅出现既有提示 `backend/tests/test_writing_agent_runs.py` 的 CRLF 将来会被 LF 替换。

## Size Impact

- `frontend/src/components/chat/agentRunProjection.ts`: 93 行。
- `frontend/src/components/chat/recoveryAgentRunProjection.ts`: 434 行。
- `frontend/src/components/chat/routeOptInAgentRunProjection.ts`: 125 行。
- `frontend/src/components/chat/agentDiagnosticRunProjection.ts`: 414 行。
- `frontend/src/components/chat/writingToolAgentRunProjection.ts`: 645 行。

## Remaining Risk

- `agentRunProjection.test.ts` 已变成主要大型文件。生产代码聚合入口已降到可维护范围，下一步更适合把测试拆到模块级测试文件，降低后续新增 Agent 工具卡片时的测试冲突和阅读成本。
- `recoveryAgentRunProjection.ts` 自身包含较多 Agent discovery 展示 helper。当前它们只服务 recovery/followup 卡片，暂不抽共享模块，避免过早引入跨模块耦合。

## Next Suggested Phase

Phase71 建议拆分前端 projection 测试，把 recovery、route opt-in、diagnostic、writing tool 的细节断言迁到模块测试文件，`agentRunProjection.test.ts` 只保留聚合入口和 run id 提取 smoke test。
