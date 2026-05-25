# Phase71 Agent Run Action Registry Report

## Scope

拆分前端 Agent run action registry，让 `agentRunProjection.ts` 只负责运行时消息识别、run id 提取和 action result view 构建。

## Changes

- 新增 `frontend/src/components/chat/agentRunActionRegistry.ts`
  - 统一聚合 recovery、diagnostic、writing tool、route opt-in、longform projection 模块。
  - 导出 `AGENT_RUN_ACTION_TYPES`。
  - 导出 `AgentRunActionType`。
  - 导出 `AgentRunActionDescriptor`。
  - 导出 `AGENT_RUN_ACTION_DESCRIPTORS`。
- 更新 `frontend/src/components/chat/agentRunProjection.ts`
  - 从 registry 导入 descriptor map。
  - 重导出原有 `AGENT_RUN_ACTION_TYPES`、`AgentRunActionType`、`AgentRunActionDescriptor`，保持调用方 API 不变。
  - 保留 runtime helpers：`isAgentRunActionType`、`getAgentRunActionDescriptor`、`getAgentRunIdFromMessage`、`buildAgentRunActionResultView`。
- 更新 `frontend/src/components/chat/agentRunProjection.test.ts`
  - 新增 registry 边界测试，验证统一 action list 与模块 action list 顺序一致，并且每个 action 都有 descriptor。

## TDD Evidence

RED:

```powershell
npm run test:unit -- agentRunProjection
```

结果：失败，原因是 `./agentRunActionRegistry` 不存在。

GREEN:

```powershell
npm run test:unit -- agentRunProjection
```

结果：`61 passed`。

## Verification

```powershell
npm run test:unit -- ChatMessage
```

结果：`29 passed`。

```powershell
npm run build
```

结果：TypeScript 与 Vite build 成功，`250 modules transformed`。

```powershell
git diff --check
```

结果：退出码 0；仅出现既有提示 `backend/tests/test_writing_agent_runs.py` 的 CRLF 将来会被 LF 替换。

## Size Impact

- `frontend/src/components/chat/agentRunProjection.ts`: 66 行。
- `frontend/src/components/chat/agentRunActionRegistry.ts`: 40 行。

## Remaining Risk

- 生产代码的 projection 聚合边界已拆清楚，但 `agentRunProjection.test.ts` 仍集中承载大量模块细节断言。
- 下一步如果继续做前端规模化，应优先拆模块级测试文件，而不是继续压缩生产入口。

## Next Suggested Phase

Phase72 建议把 projection 测试按模块拆分：registry/aggregate tests 保留在 `agentRunProjection.test.ts`，recovery、route opt-in、diagnostic、writing tool、longform 的具体 view 断言迁到各自模块测试文件。
