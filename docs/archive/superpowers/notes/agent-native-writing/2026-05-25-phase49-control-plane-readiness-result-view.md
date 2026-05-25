# Phase49 报告：控制平面就绪度结果视图

## 目标

把 `agent_control_plane_readiness` 接入后端对话结果视图和前端 Agent run 反馈，让用户直接看到 Agent 控制平面状态，而不是只看到命令契约的底层计数。

## 变更

- 后端 `action_result_view` 新增控制平面 detail items：
  - `控制平面`
  - `控制面缺口`
  - `工具缺口`
  - `命令缺口`
  - `建议检查`
- 前端 `agentRunProjection` 同步新增同语义 detail items。
- 状态已中文化：
  - `ready` -> `可继续编排`
  - `degraded` -> `需检查`
  - `needs_attention` -> `需处理`
- 结果视图只展示状态和数量，不暴露 `source` 或内部工具 ID。

## 验证

- `pytest backend/tests/test_dialogs.py -k "agent_control_plane_readiness_detail_items" -q`
  - 结果：`1 passed, 104 deselected`
- `npm run test:unit -- --run src/components/chat/agentRunProjection.test.ts -t "recovery execution feedback without leaking plan hash"`
  - 结果：`1 passed, 36 skipped`
- `pytest backend/tests/test_dialogs.py -k "agent_control_plane_readiness_detail_items or agent_command_contract_detail_items" -q`
  - 结果：`2 passed, 103 deselected`
- `npm run test:unit -- --run src/components/chat/agentRunProjection.test.ts`
  - 结果：`37 passed`
- `npm run build`
  - 结果：通过，`vue-tsc --noEmit && vite build` 完成。
- `git diff --check`
  - 结果：通过；保留既有 CRLF 提示：`backend/tests/test_writing_agent_runs.py` 下次 Git 触碰时会从 CRLF 转 LF。

## 下一步建议

下一阶段可以把控制平面就绪度接入 AgentRunDrawer，形成“运行详情 -> 控制面状态 -> 推荐检查”的稳定调试入口。
