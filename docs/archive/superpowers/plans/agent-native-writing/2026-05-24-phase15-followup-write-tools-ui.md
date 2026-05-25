# Phase15: Follow-up Write Tools UI Projection

## 背景

Phase14 已在 `plan_recommended_followups` 的 preview 输出中保留 `recommended_followups.provenance_write_tools`。但用户可见的 Agent 运行详情仍只展示恢复预览，不展示推荐后继中的“可自动诊断”和“需确认修复”区别。对于对话驱动 Agent，这会让用户无法判断 Agent 接下来为什么只自动诊断、为什么某些修复需要确认。

## 假设

- `plan_recommended_followups` preview 的 `tools` 表示安全自动候选。
- `recommended_followups.provenance_write_tools` 表示建议修复但需确认的写工具。
- 本阶段只做展示，不新增执行按钮，不改变现有 recovery 执行入口。

## 目标

1. Agent run drawer 在 `plan_recommended_followups` 步骤存在时展示推荐后继策略。
2. 展示自动诊断工具数量/名称，以及需确认修复工具数量/名称。
3. 不暴露内部哈希或审批契约细节。

## 验证

- T0: `npm run test -- AgentRunDrawer.test.ts -t provenance`
- T1: `npm run test -- AgentRunDrawer.test.ts`

## 风险控制

- 只读取已有 step output，不改变 API。
- 不新增写入执行按钮，避免绕过 approval contract。
- 复用 drawer 现有列表样式，避免大范围 UI 变更。
