# Phase72 Recovery Projection Tests Report

## Scope

拆分前端 Agent run 投影测试中的 recovery/followup 细节用例，避免 `agentRunProjection.test.ts` 继续承担模块级细节断言。

## Changes

- 新增 `frontend/src/components/chat/recoveryAgentRunProjection.test.ts`
  - 覆盖 recovery action descriptors。
  - 覆盖 recovery preview、recommended followup preview。
  - 覆盖 delegate profile targets、profile policy audit。
  - 覆盖 recovery execution action view。
  - 覆盖 recovery execution feedback builder。
- 更新 `frontend/src/components/chat/agentRunProjection.test.ts`
  - 移除 recovery/followup 细节用例。
  - 保留 aggregate registry、run id extraction、unknown action result、跨模块 action type/descriptor smoke 测试。
  - 新增结构约束：聚合测试文件不得重新引入 recovery/followup 细节 spec。

## TDD Evidence

RED:

```powershell
npm run test:unit -- agentRunProjection
```

结果：失败，`keeps recovery detail specs in the recovery projection test module` 捕获到聚合测试仍包含 `builds fallback views for recovery preview action results`。

GREEN:

```powershell
npm run test:unit -- agentRunProjection recoveryAgentRunProjection
```

结果：`62 passed`，其中 `agentRunProjection.test.ts` 54 个测试，`recoveryAgentRunProjection.test.ts` 8 个测试。

## Debug Note

首次 build 失败：

```text
src/components/chat/agentRunProjection.test.ts(1,30): error TS2307: Cannot find module 'node:fs'
src/components/chat/agentRunProjection.test.ts(2,31): error TS2307: Cannot find module 'node:url'
```

根因：结构测试使用了 Node 内置模块，但前端 `vue-tsc` 没有 Node 类型声明。修复：改用 Vite `?raw` 导入读取当前测试源文本，保持结构约束不变。

## Verification

```powershell
npm run test:unit -- agentRunProjection recoveryAgentRunProjection
```

结果：`62 passed`。

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

- `frontend/src/components/chat/agentRunProjection.test.ts`: 1281 行。
- `frontend/src/components/chat/recoveryAgentRunProjection.test.ts`: 255 行。

## Remaining Risk

- `agentRunProjection.test.ts` 仍然较大，主要因为 diagnostic、writing tool、route opt-in、longform 细节用例还集中在聚合测试。
- 结构约束目前只针对 recovery/followup，后续应按同样模式继续拆出 route opt-in、diagnostic、writing tool、longform 模块测试。

## Next Suggested Phase

Phase73 建议拆分 route opt-in projection tests。该模块范围小、风险低，适合作为第二个测试拆分样板。
