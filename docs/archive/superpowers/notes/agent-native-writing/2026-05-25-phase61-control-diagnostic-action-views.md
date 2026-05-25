# Phase61 报告：控制面诊断工具前端动作视图

## 目标

让 `inspect_agent_command_contracts` 与 `inspect_agent_control_plane_readiness` 两个 Agent 控制面诊断工具在 Hermes 对话中具备可读 action card，避免 Agent 调用后只留下原始/通用反馈。

## 变更

1. `frontend/src/components/chat/agentRunProjection.ts`
   - 注册 `inspect_agent_command_contracts`。
   - 注册 `inspect_agent_control_plane_readiness`。
   - 新增命令契约诊断 action view。
   - 新增控制平面诊断 action view。
   - 复用现有命令契约与控制面摘要 helper，只展示有界摘要。
2. `frontend/src/components/chat/agentRunProjection.test.ts`
   - 覆盖 action type 识别。
   - 覆盖 descriptor 注册。
   - 覆盖命令契约诊断卡片展示。
   - 覆盖控制平面诊断卡片展示。
   - 验证不会泄漏 raw `commands` 或 diagnostics 细节。

## 验证

TDD RED：

```powershell
npm run test:unit -- agentRunProjection
# failed: inspect_agent_command_contracts / inspect_agent_control_plane_readiness 未注册，action view 为 undefined
```

GREEN / 回归：

```powershell
npm run test:unit -- agentRunProjection
# 41 passed

npm run test:unit -- ChatMessage
# 29 passed

npm run build
# vue-tsc --noEmit && vite build succeeded

git diff --check
# pass; existing warning only: backend/tests/test_writing_agent_runs.py CRLF will be replaced by LF
```

## 结论

Phase61 补齐了 Agent 控制面诊断工具的对话展示链路。现在 Agent 调用命令契约诊断或控制平面就绪度诊断后，用户可以直接看到契约缺口、控制平面状态、工具/命令缺口和建议检查数量。
