# Phase62 报告：Agent 健康投影前端动作视图

## 目标

让 `inspect_agent_health_projection` 在 Hermes 对话中具备可读 action card，使 Agent 总体健康状态、控制面、命令契约、profile policy 与推荐工具能被用户直接观察。

## 变更

1. `frontend/src/components/chat/agentRunProjection.ts`
   - 注册 `inspect_agent_health_projection`。
   - 新增 `buildAgentHealthProjectionActionResultView()`。
   - 新增 `agentHealthProjectionDetailItems()`。
   - 复用控制面与命令契约摘要 helper。
   - 只展示聚合摘要，不泄漏 raw diagnostics、profile policy issues、delegate edges 或 raw commands。
2. `frontend/src/components/chat/agentRunProjection.test.ts`
   - 覆盖 action type 识别。
   - 覆盖 descriptor 注册。
   - 覆盖健康投影 action card 展示。
   - 验证不会泄漏原始命令和 profile policy issue 细节。

## 验证

TDD RED：

```powershell
npm run test:unit -- agentRunProjection
# failed: inspect_agent_health_projection 未注册，action view 为 undefined
```

GREEN / 回归：

```powershell
npm run test:unit -- agentRunProjection
# 42 passed

npm run test:unit -- ChatMessage
# 29 passed

npm run build
# vue-tsc --noEmit && vite build succeeded

git diff --check
# pass; existing warning only: backend/tests/test_writing_agent_runs.py CRLF will be replaced by LF
```

## 结论

Phase62 补齐了 Agent 健康投影工具的对话展示层。现在 Agent 可以在对话中调用健康投影，并给用户展示可读的总体健康状态、控制面缺口、命令契约缺口、策略问题、诊断项和推荐工具数量。
