# Phase59 报告：Job Projection 前端动作视图

## 目标

让 `inspect_agent_job_projection` 成为 Hermes 对话中可识别、可展示的 Agent action result，补齐任务队列观察工具的前端反馈层。

## 变更

1. `frontend/src/components/chat/agentRunProjection.ts`
   - 注册 `inspect_agent_job_projection` action type 与 descriptor。
   - 新增 `buildJobProjectionActionResultView()`。
   - 新增 `jobProjectionDetailItems()`。
   - 抽出 `controlPlaneReadinessDetailItems()`，让 run detail 与 job projection 复用控制面摘要展示。
   - 复用 `commandContractDetailItems()` 展示命令契约摘要，避免泄漏 raw command。
2. `frontend/src/components/chat/agentRunProjection.test.ts`
   - 覆盖 action type 识别。
   - 覆盖 descriptor 注册。
   - 覆盖 job projection action card 的队列、任务、控制面、命令契约与推荐工具摘要。

## 验证

TDD RED：

```powershell
npm run test:unit -- agentRunProjection
# failed: inspect_agent_job_projection 未注册，action view 为 undefined
```

GREEN / 回归：

```powershell
npm run test:unit -- agentRunProjection
# 38 passed

npm run test:unit -- ChatMessage
# 29 passed

npm run build
# vue-tsc --noEmit && vite build succeeded

git diff --check
# pass; existing warning only: backend/tests/test_writing_agent_runs.py CRLF will be replaced by LF
```

## 结论

Phase59 补齐了任务队列投影工具的对话展示入口。Agent 调用 `inspect_agent_job_projection` 后，用户能直接看到队列深度、活跃任务、下一章、关联运行、控制面缺口、命令契约缺口和推荐工具数量。
