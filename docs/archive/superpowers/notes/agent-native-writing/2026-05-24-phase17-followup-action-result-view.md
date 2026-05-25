# Phase17 Report: Follow-up Action Result View

## 本阶段目标

让后端 `action_result_view` 支持 `plan_recommended_followups`，保证消息接口刷新、历史消息和非前端 fallback 场景都能展示推荐后继摘要。

## 实现内容

- `TYPE_LABELS` 新增 `plan_recommended_followups`。
- `_label` 增加推荐后继预览专门文案：
  - 成功：`推荐后继预览已生成`
  - 失败：`推荐后继预览失败`
- `_detail_items` 增加推荐后继分支，输出：
  - 来源运行；
  - 推荐状态；
  - 自动后继数量；
  - 需确认修复数量。

## 设计取舍

- 后端 view 与前端 fallback 保持同一摘要语义。
- 不输出工具名和参数，避免历史消息泄露内部修复细节。
- 不改变 DialogMessage 存储结构。

## 验证

- RED: `pytest tests/test_dialogs.py -k recommended_followup_result_view -q`
  - 初始失败：label 为通用 `plan_recommended_followups执行成功`，缺少 detail_items。
- GREEN: `pytest tests/test_dialogs.py -k recommended_followup_result_view -q`
  - 结果：`1 passed, 96 deselected`
- T1: `pytest tests/test_dialogs.py -k "recovery_preview or recommended_followup_result_view or agent_discovery_view" -q`
  - 结果：`4 passed, 93 deselected`

## 后续建议

下一阶段应补 Hermes 对话入口：当用户要求继续执行上一轮推荐后继时，后端需要能创建 `plan_recommended_followups` 的 action_result 消息，而不是只能通过 Agent run API 看到 preview。
