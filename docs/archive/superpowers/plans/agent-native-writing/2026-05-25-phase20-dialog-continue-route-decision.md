# Phase20: 低细节继续路由决策投影

## 背景

Phase18/19 打通了“继续”到恢复预览、推荐后继预览和推荐后继确认执行的链路，但用户和后续 Agent 审计仍难以直接看出：为什么同一句“继续吧”有时走恢复，有时走推荐后继，有时走章节生成。

对长期写作 Agent 来说，自动编排必须可解释、可审计。否则工具越多，用户越难判断 Agent 的行为边界。

## 目标

为低细节继续文本增加统一 route decision 投影：

1. 恢复预览：标记选中 `recover_blocked_run`，理由为发现可恢复 run。
2. 推荐后继预览：标记选中 `recommended_followups`，理由为发现上一轮推荐后继。
3. 章节生成回落：标记选中 `chapter_generation`，理由为没有恢复或推荐后继，继续写下一章。

投影写入：

- `ChatOut.meta.dialog_route_decision`
- assistant message `meta.dialog_route_decision`
- 对于 action_result 类预览，额外写入 `action_result.data.route_decision`
- 对于 pending action 章节生成，额外写入 pending params，便于后续确认/Trace 串联

## 参考项目取舍

参考项目中的 Agent 循环普遍重视 decision trace。本阶段不引入复杂 event bus，仅把 novelv3 已有对话路由选择补成轻量、稳定的结构化元数据，后续可再接入 Trace。

## 验证

1. RED：更新 `backend/tests/test_dialogs.py` 中三条低细节继续路由测试，要求存在 `dialog_route_decision`。
2. GREEN：在 `backend/app/api/dialogs.py` 最小实现。
3. T1：运行低细节继续和推荐后继相关 dialog 测试。

## 非目标

- 不改变“恢复 > 推荐后继 > 章节生成”的优先级。
- 不新增前端显示。
- 不把所有普通 intent router 都迁入本投影，只处理低细节继续路径。
