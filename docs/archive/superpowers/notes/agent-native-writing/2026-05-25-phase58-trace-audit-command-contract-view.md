# Phase58 报告：Trace Audit 命令契约前端视图

## 目标

让 Hermes 对话里的 `inspect_agent_trace_audit` action card 能直接展示后端新增的 `command_contracts` 摘要，避免命令契约健康度只存在于原始 API 输出中。

## 变更

1. `frontend/src/components/chat/agentRunProjection.test.ts`
   - 扩展 Trace audit action result view 测试。
   - 覆盖 `command_contracts.summary.agent_control_commands` 与 `gap_count` 展示。
   - 验证不会泄漏原始 `commands` 列表内容。
2. `frontend/src/components/chat/agentRunProjection.ts`
   - 抽出 `commandContractDetailItems()`，复用 run detail 已有命令契约展示语义。
   - Trace audit detail items 追加命令契约摘要。

## 验证

TDD RED：

```powershell
npm run test:unit -- agentRunProjection
# failed: expected detail_items to contain 命令契约
```

GREEN / 回归：

```powershell
npm run test:unit -- agentRunProjection
# 37 passed

npm run test:unit -- AgentRunDrawer
# 14 passed

npm run build
# vue-tsc --noEmit && vite build succeeded

git diff --check
# pass; existing warning only: backend/tests/test_writing_agent_runs.py CRLF will be replaced by LF
```

## 结论

Phase58 打通了 Trace audit 命令契约摘要的前端展示。用户现在可以在对话 action card 里直接看到命令契约已投影、控制命令数量与契约缺口数量，且不会暴露底层 raw command 数据。
