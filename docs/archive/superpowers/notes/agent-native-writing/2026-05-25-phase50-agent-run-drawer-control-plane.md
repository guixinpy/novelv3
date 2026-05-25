# Phase50 报告：AgentRunDrawer 展示控制平面就绪度

## 目标

在 AgentRunDrawer 的 Agent 概览区展示 `agent_control_plane_readiness`，让用户查看运行详情时能直接确认 Agent 控制面是否可继续编排。

## 变更

- AgentRunDrawer 新增控制平面计算属性：
  - 状态
  - 总缺口
  - 工具缺口
  - 命令缺口
  - 建议检查数量
- 概览区新增对应中文展示。
- 状态口径与 Phase49 保持一致：
  - `ready` -> `可继续编排`
  - `degraded` -> `需检查`
  - `needs_attention` -> `需处理`
- 抽屉不展示内部 `source` 或具体工具 ID。

## 验证

- `npm run test:unit -- --run src/components/writingAgent/AgentRunDrawer.test.ts -t "command contract summary"`
  - 结果：`1 passed, 13 skipped`
- `npm run test:unit -- --run src/components/writingAgent/AgentRunDrawer.test.ts`
  - 结果：`14 passed`
- `npm run build`
  - 结果：通过，`vue-tsc --noEmit && vite build` 完成。
- `git diff --check`
  - 结果：通过；保留既有 CRLF 提示：`backend/tests/test_writing_agent_runs.py` 下次 Git 触碰时会从 CRLF 转 LF。

## 下一步建议

下一阶段可以进入“自检消费”方向：让后续推荐工具或恢复策略优先读取 `agent_control_plane_readiness.total_gap_count`，在控制平面有缺口时主动建议检查工具契约或命令契约。
