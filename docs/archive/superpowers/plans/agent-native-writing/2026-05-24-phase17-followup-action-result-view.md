# Phase17: Follow-up Action Result View

## 背景

Phase16 已让前端 fallback 能识别 `plan_recommended_followups`。但 `DialogMessageService` 会优先返回后端 `action_result_view`，当前后端只对 `plan_recovery_tools` 做专门摘要。若后端不支持 `plan_recommended_followups`，历史消息、刷新后的消息列表和非前端 fallback 场景仍不能稳定展示推荐后继摘要。

## 假设

- `action_result.data.tools` 表示安全自动后继工具。
- `action_result.data.recommended_followups.provenance_write_tools` 表示需确认修复工具。
- 后端 view 只展示计数和状态，不展示工具参数。

## 目标

1. 后端 `action_result_view` 支持 `plan_recommended_followups`。
2. view label 为“推荐后继预览已生成/失败”。
3. detail items 包含来源运行、推荐状态、自动后继、需确认修复。

## 验证

- T0: `pytest tests/test_dialogs.py -k recommended_followup_result_view -q`
- T1: `pytest tests/test_dialogs.py -k "recovery_preview or recommended_followup_result_view or agent_discovery_view" -q`

## 风险控制

- 不改 DialogMessage 存储结构。
- 不改 action 执行路径。
- 不暴露 plan hash、tool params 或写工具参数。
