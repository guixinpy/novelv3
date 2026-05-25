# Phase50: AgentRunDrawer 展示控制平面就绪度

## 背景

Phase49 已让对话结果视图展示控制平面摘要，但运行详情抽屉仍只显示命令契约。用户进入 run 详情时无法直接确认 Agent 控制面是否适合继续自主编排。

## 目标

在 AgentRunDrawer 的 Agent 概览区域展示 `agent_control_plane_readiness` 的中文摘要。

## 范围

1. 新增控制平面状态、总缺口、工具缺口、命令缺口、建议检查数量。
2. 与 Phase49 使用同一中文状态口径。
3. 不展示内部 source 或具体工具 ID。

## 非目标

- 不改布局结构。
- 不新增 API 字段。
- 不改 Agent 执行逻辑。

## 验证

- T0: `npm run test:unit -- --run src/components/writingAgent/AgentRunDrawer.test.ts -t "command contract summary"`
- T1: `npm run test:unit -- --run src/components/writingAgent/AgentRunDrawer.test.ts`
- T1: `npm run build`
