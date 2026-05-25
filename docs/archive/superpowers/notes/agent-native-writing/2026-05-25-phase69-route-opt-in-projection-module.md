# Phase69 Route Opt-In Projection Module Report

## Scope

拆分前端 Agent run 投影中的路由升级 opt-in 卡片逻辑，避免 `agentRunProjection.ts` 继续承载所有 action card 细节。

本阶段只处理 3 个 action type：

- `prepare_route_upgrade_contract`
- `preview_pending_action_route_approval_opt_in_apply_contract`
- `apply_pending_action_route_approval_opt_in`

## Changes

- 新增 `frontend/src/components/chat/routeOptInAgentRunProjection.ts`
  - 导出 `ROUTE_OPT_IN_AGENT_RUN_ACTION_TYPES`
  - 导出 `ROUTE_OPT_IN_AGENT_RUN_ACTION_DESCRIPTORS`
  - 内聚路由升级契约、应用结果、中文状态、详情条目构建逻辑。
- 更新 `frontend/src/components/chat/agentRunProjection.ts`
  - 通过 spread 聚合 route opt-in action types/descriptors。
  - 移除已迁出的 route opt-in 私有函数。
  - 聚合入口继续保持 `buildAgentRunActionResultView`、`getAgentRunActionDescriptor` 等外部 API 不变。
- 更新 `frontend/src/components/chat/agentRunProjection.test.ts`
  - 新增模块边界测试，要求 route opt-in descriptors 由专门模块导出。

## TDD Evidence

RED:

```powershell
npm run test:unit -- agentRunProjection
```

结果：失败，原因是 `./routeOptInAgentRunProjection` 不存在。

GREEN:

```powershell
npm run test:unit -- agentRunProjection
```

结果：`59 passed`。

## Verification

```powershell
npm run test:unit -- ChatMessage
```

结果：`29 passed`。

```powershell
npm run build
```

结果：TypeScript 与 Vite build 成功，`248 modules transformed`。

```powershell
git diff --check
```

结果：退出码 0；仅出现既有提示 `backend/tests/test_writing_agent_runs.py` 的 CRLF 将来会被 LF 替换。

## Size Impact

- `frontend/src/components/chat/agentRunProjection.ts`: 500 行。
- `frontend/src/components/chat/routeOptInAgentRunProjection.ts`: 125 行。

## Remaining Risk

- `agentRunProjection.ts` 仍保留恢复预览、推荐后继、执行反馈等逻辑。它们与 Agent run 聚合入口耦合更紧，后续应单独评估是否拆成 recovery/followup projection 模块。
- `agentRunProjection.test.ts` 仍然较大，后续可把新模块的细节测试拆到各自模块测试文件，只保留聚合入口 smoke test。

## Next Suggested Phase

Phase70 建议拆分 recovery/followup 投影模块，或者先拆分 projection tests，降低新增 Agent 工具卡片时的测试文件维护成本。
