# Phase157 Recovery Execute CTA Report

## Summary

本阶段把 Phase153-156 的恢复预览链路推进到受控执行入口：Agent 运行详情抽屉现在会在后端预览明确满足 `can_execute === true`、`execution_policy.status === "ready"`、`source_run_id` 和 `plan_hash` 都存在时显示 `确认执行恢复`。

点击该按钮不会直接绕过策略执行工具，而是创建新的 Writing Agent run：

- `entrypoint: "ui_recovery_execute"`
- `input.auto_plan: true`
- `input.recovery_run_id`
- `input.execute_recovery: true`
- `input.confirm_execute: true`
- `input.recovery_plan_hash`

后端仍由既有 hash + confirmation 门禁决定是否执行恢复计划。

## Changes

- `frontend/src/api/types.ts`
  - Added `WritingAgentToolRequest` and `WritingAgentRunCreate`.
- `frontend/src/api/client.ts`
  - Added `api.createAgentRun(projectId, data)`.
- `frontend/src/components/writingAgent/AgentRunDrawer.vue`
  - Added executable recovery readiness detection.
  - Added `executeRecovery` emit.
  - Added `确认执行恢复` CTA only for executable previews.
- `frontend/src/views/HermesView.vue`
  - Added `executeRecoveryFromRun`.
  - Creates a confirmed recovery execution run and switches the drawer to returned run detail.
- Tests
  - Added drawer CTA emit coverage.
  - Added Hermes execution payload coverage.

## TDD Evidence

RED command:

```powershell
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Initial root-level run failed because `package.json` lives under `frontend/`; reran from `frontend/`.

Expected failing assertions:

- `AgentRunDrawer`: expected `[data-testid="execute-recovery"]` not to be null.
- `HermesView`: expected `api.createAgentRun` to have been called, received 0 calls.

GREEN command:

```powershell
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Result:

- 2 test files passed.
- 8 tests passed.

## Validation

Targeted frontend:

```powershell
cd frontend
npm run test:unit -- src/components/writingAgent/AgentRunDrawer.test.ts src/views/HermesView.test.ts
```

Result: 8 passed.

Targeted backend recovery contract:

```powershell
backend\.venv\Scripts\python.exe -m pytest backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_previews_recovery_tool_plan_by_default backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_executes_recovery_after_hash_confirmation backend\tests\test_writing_agent_runs.py::test_agent_run_auto_plan_rejects_recovery_execute_hash_mismatch -q
```

Result: 3 passed.

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

下一阶段可以继续收紧恢复执行后的用户反馈：

1. 在 drawer 中区分“预览 run”和“执行 run”，避免用户误以为原预览已被原地执行。
2. 为执行失败的 run 增加更明确的中文错误摘要和下一步建议。
3. 在 Hermes 消息流中追加一条轻量系统消息，记录用户触发了恢复执行入口，便于长会话追踪。
