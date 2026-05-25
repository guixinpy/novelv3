# Phase162 Recovery Execution Error Feedback Report

## Summary

本阶段补强恢复执行 run 的失败态聊天反馈。若后端返回的 execution run 带有 `error`，Hermes 本地反馈会在详情项中显示 `错误摘要`，帮助用户理解失败原因和后续恢复方向。

该阶段只扩展前端投影 helper，不读取 run input，不暴露 recovery plan hash。

## Changes

- `frontend/src/components/chat/agentRunProjection.ts`
  - `buildAgentRunExecutionFeedback` now trims `run.error`.
  - Non-empty error text is added as `{ label: "错误摘要", value: error }`.
- `frontend/src/components/chat/agentRunProjection.test.ts`
  - Added failed execution feedback coverage.
  - Verified `variant: "error"`.
  - Verified plan hash is not serialized into the feedback message.

## TDD Evidence

RED command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts
```

Expected failing assertion:

- Failed execution feedback did not include `{ label: "错误摘要", value: "工具执行失败：缺少章节上下文" }`.

GREEN command:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts
```

Result:

- 1 test file passed.
- 4 tests passed.

## Validation

Targeted frontend regression:

```powershell
cd frontend
npm run test:unit -- src/components/chat/agentRunProjection.test.ts src/components/chat/ChatMessage.test.ts src/views/HermesView.test.ts
```

Result:

- 3 test files passed.
- 23 tests passed.

Build:

```powershell
cd frontend
npm run build
```

Result: `vue-tsc --noEmit` and `vite build` passed.

Hygiene:

```powershell
git diff --check
rg -n "sk-[A-Za-z0-9]{20,}" backend frontend docs --glob "!backend/static/assets/**" --glob "!docs/archive/**"
```

Result:

- `git diff --check`: passed.
- secret scan: no matches.

## Next Recommendation

下一阶段建议把 `plan_recovery_tools` 预览反馈也迁入 `agentRunProjection`，形成统一的 Agent run action view 构造入口。这样后续审稿、检索、世界模型等工具事件可以按同一 contract 进入 Hermes 对话层。
