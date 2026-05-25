# Phase60: Job Projection 运行详情关联

## 背景

Phase59 已让 `inspect_agent_job_projection` 具备前端 action card，但 `getAgentRunIdFromMessage()` 只支持 `agent_run_id` 和 `data.run.id`。Job projection 的关联运行位于 `data.selected_task.agent_runs[]`，因此卡片可能无法关联打开 Agent run 详情。

## 目标

让 job projection action message 能从 `selected_task.agent_runs[0].id` 提取最新关联 Agent run ID。

## 范围

1. 扩展 `frontend/src/components/chat/agentRunProjection.test.ts`。
2. 扩展 `frontend/src/components/chat/agentRunProjection.ts` 的 run id 提取逻辑。

## 非目标

- 不改变 action card 展示内容。
- 不改变后端 job projection 输出顺序。
- 不新增多 run 选择 UI；当前只提取列表中的第一个 run。

## 验证

- TDD RED: `npm run test:unit -- agentRunProjection`
- T0: `npm run test:unit -- agentRunProjection`
- T0: `git diff --check`
