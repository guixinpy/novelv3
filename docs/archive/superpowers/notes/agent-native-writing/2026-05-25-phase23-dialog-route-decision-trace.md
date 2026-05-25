# Phase23: 对话继续路由 Trace 审计报告

## 目标

把低细节“继续”的 Agent 路由决策从消息元数据提升为可审计 Trace 事件，使后续 `inspect_agent_trace_audit` 能追溯 Agent 为什么选择恢复、推荐后继或章节生成回落。

## 参考项目取舍

- 采纳 `openhuman` 的“状态转移显式事件化”思路，但没有引入事件总线；novelv3 当前已有 `AIModelCallTrace`，先复用现有审计基座。
- 采纳 `hermes-agent` 对 tool-call/tool-result 历史可统计的思路，把“工具调用前的路由选择”也纳入可统计事件。
- 采纳 `openclaw` 对用户行为与工具使用可视化追踪的方向，但本阶段只做后端审计数据，不新增前端图表。

## 改动

1. `backend/app/api/dialogs.py`
   - 新增 `_record_dialog_route_decision_trace`。
   - 三条低细节继续路径都会写入 `dialog_route_decision` Trace：
     - 恢复阻塞运行
     - 推荐后继
     - 章节生成回落
   - Trace 绑定 `dialog_id`、请求消息、响应消息，并在 metadata 中记录 `dialog_route_decision`、`agent_run_id/source_run_id/action_type`。

2. `backend/app/services/writing_agent/agent_trace_audit.py`
   - 新增 `dialog_route_events`。
   - 新增 `audit.dialog_route_event_count`。
   - `event_chain` 开头接入 `dialog_route_decision` 事件。
   - 输出中文标签，不暴露 `priority` 等内部路由细节。

3. `backend/tests/test_dialogs.py`
   - 低细节继续三条路径均断言存在路由 Trace。

4. `backend/tests/test_writing_agent_trace_audit.py`
   - 新增审计工具暴露对话路由事件测试。

## 验证

- RED：`pytest backend/tests/test_dialogs.py -k "low_detail_continue_prefers_recovery_preview or low_detail_continue_previews_latest_recommended_followups or low_detail_continue_uses_first_unwritten_outline_chapter" -q`
  - 失败原因：三条路径均查不到 `dialog_route_decision` Trace。
- GREEN：同一命令通过，`3 passed`。
- RED：`pytest backend/tests/test_writing_agent_trace_audit.py -k "dialog_route_decision" -q`
  - 失败原因：`audit.dialog_route_event_count` 不存在。
- GREEN：同一命令通过，`1 passed`。
- T1：`pytest backend/tests/test_dialogs.py -k "low_detail_continue or recommended_followup_result_view or recovery_preview" -q`
  - `7 passed`
- T2：`pytest backend/tests/test_writing_agent_trace_audit.py -q`
  - `6 passed`
- T2：`pytest backend/tests/test_writing_agent_health_projection.py -q`
  - `2 passed`
- T2：`pytest backend/tests/test_writing_agent_tool_executor.py -k "inspect_agent_trace_audit" -q`
  - `2 passed`
- T2：`pytest backend/tests/test_model_call_traces.py -k "create_trace_sanitizes_context_blocks_and_trace_metadata or list_model_call_traces_filters_by_trace_type" -q`
  - `2 passed`

## 下一阶段建议

1. 将 `dialog_route_events` 投影到 Hermes 聊天侧的审计卡片或 Agent 运行抽屉，避免只在工具审计 JSON 中可见。
2. 继续把 slash command 与普通文本意图统一成同一类 `agent_intent_route` Trace，减少旧命令系统与 Agent 路由系统并存的灰区。
