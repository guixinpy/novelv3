# Phase21: 继续路由决策详情展示

## 背景

Phase20 已把低细节“继续”路由决策写入后端元数据，但如果只存在于 JSON 中，用户视角仍看不到 Agent 为什么选择恢复、推荐后继或章节生成。下一步需要把该决策投影到现有消息详情。

## 目标

1. 后端 `action_result_view` 对 `plan_recovery_tools` 和 `plan_recommended_followups` 展示：
   - `继续路由`
   - `路由原因`
2. 前端本地 fallback `buildAgentRunActionResultView` 做同样展示，保证实时消息和历史消息一致。
3. 不改变 action_result schema，不新增 UI 组件，只复用现有 `detail_items`。

## 参考项目取舍

参考项目里的 decision trace 通常可进入 event stream 或 audit timeline。本阶段先落到 novelv3 已有 action_result_view，保持小步可验证，后续再把同一结构接入 Trace。

## 验证

1. RED：
   - `pytest backend/tests/test_dialogs.py -k "recovery_preview or recommended_followup_result_view" -q`
   - `npm run test:unit -- agentRunProjection.test.ts -t "fallback views for"`
2. GREEN：目标测试通过。
3. T1/T2：
   - 后端相关 dialog 小集合
   - 前端 agentRunProjection 单测

## 非目标

- 不新增前端样式。
- 不展示 raw `source_run_id` 之外的内部执行参数。
- 不处理普通 free chat 的 route trace。
