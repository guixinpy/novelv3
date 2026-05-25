# Phase20 报告：低细节继续路由决策投影

## 完成内容

1. 增加 `phase20.dialog_continue_route_decision.v1` 结构化投影。
2. Hermes 对低细节“继续/继续吧/下一步”进行自动路由时，现在记录：
   - `selected_route`
   - `reason_code`
   - `priority`
   - `source_run_id`（恢复/推荐后继路径）
3. 恢复预览和推荐后继预览将决策写入：
   - `ChatOut.meta.dialog_route_decision`
   - assistant message `meta.dialog_route_decision`
   - `action_result.data.route_decision`
4. 章节生成回落将决策写入：
   - `ChatOut.meta.dialog_route_decision`
   - assistant message `meta.dialog_route_decision`
   - pending action params `dialog_route_decision`

## 参考项目取舍记录

openclaw、hermes-agent、openhuman 都强调 Agent 行为需要 traceable decision。本阶段采用轻量结构化元数据，而不是引入复杂事件总线：先把 novelv3 现有 Hermes 路由的选择理由落到消息和 action_result/pending action 中，后续再接 Trace 或更完整的 Agent loop。

## 验证

RED：

```powershell
pytest backend/tests/test_dialogs.py -k "low_detail_continue_prefers_recovery_preview or low_detail_continue_previews_latest_recommended_followups or low_detail_continue_uses_first_unwritten_outline_chapter" -q
```

结果：3 个测试失败，原因分别为缺少 `dialog_route_decision` 或 `meta` 为 `None`。

GREEN：

```powershell
pytest backend/tests/test_dialogs.py -k "low_detail_continue_prefers_recovery_preview or low_detail_continue_previews_latest_recommended_followups or low_detail_continue_uses_first_unwritten_outline_chapter" -q
```

结果：`3 passed, 95 deselected`。

T1：

```powershell
pytest backend/tests/test_dialogs.py -k "low_detail_continue or recommended_followup_result_view or recovery_preview" -q
pytest backend/tests/test_writing_agent_runs.py -k "recommended_followup" -q
```

结果：

- `7 passed, 91 deselected`
- `7 passed, 178 deselected`

## 下一阶段建议

1. 将 `dialog_route_decision` 接入 action_result_view 或前端消息详情，让用户直接看到“为什么这次继续走该路径”。
2. 把低细节继续路由决策同步写入 Agent Trace，形成长期审计链路。
