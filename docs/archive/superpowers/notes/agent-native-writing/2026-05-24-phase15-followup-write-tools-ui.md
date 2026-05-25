# Phase15 Report: Follow-up Write Tools UI Projection

## 本阶段目标

把 `plan_recommended_followups` preview 中的读写分离信号展示到 Agent run drawer，让用户能看见“可自动诊断工具”和“需确认修复工具”。

## 实现内容

- `AgentRunDrawer.vue` 新增 recommended follow-up preview 读取逻辑。
- 新增“推荐后继策略”区块：
  - 自动诊断工具：读取 preview `tools`。
  - 需确认修复：读取 `recommended_followups.provenance_write_tools`。
- 运行类型在推荐后继预览下显示为“后继预览”。
- 未新增任何写入执行按钮，仍不绕过 approval contract。

## 设计取舍

- 先放在 drawer，而不是直接改对话卡片，因为 drawer 是完整运行详情入口，变更范围更小。
- `provenance_write_tools` 只展示工具名，不展示 params，避免泄露内部诊断细节或未来审批契约信息。
- 复用现有列表样式，减少 UI 风险。

## 验证

- RED: `npm run test:unit -- AgentRunDrawer.test.ts -t provenance`
  - 初始失败：页面文本不包含“推荐后继策略”。
- GREEN: `npm run test:unit -- AgentRunDrawer.test.ts -t provenance`
  - 结果：`1 passed, 11 skipped`
- T1: `npm run test:unit -- AgentRunDrawer.test.ts`
  - 结果：`12 passed`

## 后续建议

下一阶段可以把同样的摘要加入 chat action result projection：对话消息中展示“自动诊断 1 个、需确认修复 1 个”，用户不必打开 drawer 才能理解 Agent 的下一步边界。
