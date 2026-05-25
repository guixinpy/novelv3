# Phase73 Route Opt-In Projection Tests Report

## Scope

拆分前端 Agent run 投影测试中的 route opt-in 细节用例，继续降低 `agentRunProjection.test.ts` 的模块细节负担。

## Changes

- 新增 `frontend/src/components/chat/routeOptInAgentRunProjection.test.ts`
  - 覆盖 route opt-in action descriptors。
  - 覆盖 route opt-in contract preview card。
  - 覆盖 route opt-in apply result card。
- 更新 `frontend/src/components/chat/agentRunProjection.test.ts`
  - 移除 route opt-in 细节用例。
  - 保留 aggregate registry 与跨模块 smoke 检查。
  - 扩展结构约束：聚合测试不得重新引入 route opt-in 细节 spec。

## TDD Evidence

RED:

```powershell
npm run test:unit -- agentRunProjection
```

结果：失败，结构测试捕获到聚合测试仍包含 `builds route opt-in contract preview fallback views without leaking approval hashes`。

GREEN:

```powershell
npm run test:unit -- agentRunProjection routeOptInAgentRunProjection
```

结果：`62 passed`，其中 `agentRunProjection.test.ts` 51 个测试，`routeOptInAgentRunProjection.test.ts` 3 个测试，`recoveryAgentRunProjection.test.ts` 8 个测试。

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

- `frontend/src/components/chat/agentRunProjection.test.ts`: 1232 行。
- `frontend/src/components/chat/recoveryAgentRunProjection.test.ts`: 255 行。
- `frontend/src/components/chat/routeOptInAgentRunProjection.test.ts`: 57 行。

## Remaining Risk

- `agentRunProjection.test.ts` 仍然包含 diagnostic、writing tool、longform 细节测试。
- 下一步应继续拆 diagnostic tests；它覆盖 Trace、job、health、command contracts、control plane、memory route、knowledge route，是 Agent 自审计和控制面的关键前端投影。

## Next Suggested Phase

Phase74 建议拆分 diagnostic projection tests，保持当前结构测试模式，继续把聚合测试收敛为 registry/runtime smoke。
