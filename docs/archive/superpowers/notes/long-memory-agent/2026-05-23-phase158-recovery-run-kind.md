# Phase158 Recovery Run Kind Report

## Summary

本阶段为 Agent 运行详情抽屉增加只读运行类型标识，解决 Phase157 后用户难以区分“恢复预览 run”和“恢复执行 run”的问题。

## Changes

- `frontend/src/components/writingAgent/AgentRunDrawer.vue`
  - Added `runKindLabel`.
  - Recovery preview runs show `运行类型: 恢复预览`.
  - Recovery execution runs show `运行类型: 恢复执行`.
  - When available, summary also shows `来源运行` and `计划哈希`.
- `frontend/src/components/writingAgent/AgentRunDrawer.test.ts`
  - Added assertions for preview-run kind.
  - Added a confirmed recovery execution run fixture and metadata assertions.

## TDD Evidence

RED command:

```powershell
cd frontend
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts
```

Expected failing assertions:

- Existing recovery policy fixture did not contain `运行类型`.
- New recovery execution fixture did not contain `运行类型`.

GREEN command:

```powershell
cd frontend
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts
```

Result:

- 1 test file passed.
- 5 tests passed.

## Validation

Targeted frontend regression:

```powershell
cd frontend
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Result:

- 2 test files passed.
- 9 tests passed.

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

下一阶段建议把恢复执行入口的结果反馈补到 Hermes 对话层：

1. 用户点击恢复执行后，在消息流中追加一条轻量系统反馈。
2. 反馈应包含新 run id、执行状态和“查看运行”入口。
3. 不要在前端推断执行成功的业务结果，只展示后端返回的 run 状态。
