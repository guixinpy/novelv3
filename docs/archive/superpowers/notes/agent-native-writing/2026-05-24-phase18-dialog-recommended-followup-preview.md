# Phase18 报告：Hermes 推荐后继预览入口

## 完成内容

1. 在 `recommended_followup_planner` 增加 `latest_recommended_followup_run_id`，用于从最近成功/完成的 Agent run 中寻找可继续的推荐后继来源。
2. 在 Hermes 对话入口增加 `_handle_dialog_recommended_followup_preview`。
3. 低细节“继续/继续吧/下一步”现在遵循优先级：
   - 先处理可恢复的 blocked/failed run；
   - 若无可恢复运行，再处理最近的 recommended followups；
   - 若两者都没有，再回落到原有章节生成/普通意图。
4. 保存 assistant `action_result.type = plan_recommended_followups`，沿用前几阶段的后端 action result view 与前端聊天投影。

## 参考项目取舍记录

本阶段没有直接移植 openclaw、hermes-agent、openhuman 的代码，而是采用它们共同强调的“对话入口只表达意图，Agent run 负责规划与审计”的模式。novelv3 的适配点是：所有后继动作仍落到现有 `WritingAgentRun`、`WritingAgentStep`、`action_result` 三层记录中，避免新增第二套不可审计的对话内执行链。

后续继续参考三个项目时，按“更适合长篇写作 Agent、可审计、能工具化已有模块、可小步验证”的标准选择，不机械照搬。

## 验证

RED：

```powershell
pytest backend/tests/test_dialogs.py -k recommended_followups -q
```

结果：新增测试失败，低细节“继续吧”仍创建 `preview_chapter` pending action。

GREEN：

```powershell
pytest backend/tests/test_dialogs.py -k recommended_followups -q
```

结果：`1 passed, 97 deselected`。

T1：

```powershell
pytest backend/tests/test_dialogs.py -k "low_detail_continue or recommended_followup_result_view or recovery_preview" -q
pytest backend/tests/test_writing_agent_runs.py -k "recommended_followup" -q
```

结果：

- `7 passed, 91 deselected`
- `7 passed, 178 deselected`

## 下一阶段建议

1. 把推荐后继的“确认执行”也从开发化 API 入口投影到 Hermes 对话层，但必须保持 plan_hash/confirmation gate。
2. 将 “继续” 路由的选择原因写入 trace 或 response meta，方便前端展示“为什么这次继续是恢复/后继/章节生成”。
