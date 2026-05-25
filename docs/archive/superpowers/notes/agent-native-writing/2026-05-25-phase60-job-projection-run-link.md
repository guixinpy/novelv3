# Phase60 报告：Job Projection 运行详情关联

## 目标

让 `inspect_agent_job_projection` action message 能从 `selected_task.agent_runs[0].id` 提取关联 Agent run ID，便于前端继续打开运行详情。

## 变更

1. `frontend/src/components/chat/agentRunProjection.test.ts`
   - 新增 job projection 嵌套 run id 提取测试。
2. `frontend/src/components/chat/agentRunProjection.ts`
   - `getAgentRunIdFromMessage()` 在 `agent_run_id` 与 `data.run.id` 之后，增加 `data.selected_task.agent_runs[0].id` 提取路径。

## 验证

TDD RED：

```powershell
npm run test:unit -- agentRunProjection
# failed: expected '' to be 'run-job-1'
```

GREEN / 回归：

```powershell
npm run test:unit -- agentRunProjection
# 39 passed

npm run test:unit -- ChatMessage
# 29 passed

npm run build
# vue-tsc --noEmit && vite build succeeded

git diff --check
# pass; existing warning only: backend/tests/test_writing_agent_runs.py CRLF will be replaced by LF
```

## 结论

Phase60 补齐了 job projection 卡片和 Agent run 详情之间的关联路径。后续 Agent 调用任务队列投影后，前端可以从选中任务的最新关联 run 打开执行详情。
