# Phase23: 对话继续路由 Trace 审计

## 背景

Phase20-22 已让低细节“继续”请求产生 `dialog_route_decision`，并在消息、action result 与待确认卡片中展示。但该决策目前仍主要停留在对话消息元数据中，没有成为可检索的 Trace 事件。对 Agent 化系统来说，路由选择属于工具编排前的关键状态转移，应当进入审计链。

## 参考项目取舍

- `openhuman` 的事件总线强调跨模块事件可订阅、可追踪；本阶段吸收其“状态转移显式事件化”的思路。
- `hermes-agent` 的工具统计与 tool-call 映射强调工具调用历史可汇总；本阶段把路由决策作为工具调用前置事件纳入模型调用 Trace 体系。
- `openclaw` 的使用量/工具调用视图强调从用户行为反推 Agent 决策；本阶段优先保证路由事件可被后续审计工具读取，而不是先做新可视化。

## 目标

1. 低细节“继续”三条路径都写入 `AIModelCallTrace`：
   - `recover_blocked_run`
   - `recommended_followups`
   - `chapter_generation`
2. Trace 使用独立 `trace_type`，并在 `trace_metadata.dialog_route_decision` 中保存已脱敏的路由决策。
3. Trace 绑定 `dialog_id`、用户请求消息、助手响应消息；有 Agent run 时绑定 run id 到 metadata。
4. `inspect_agent_trace_audit` 能暴露对话路由事件，使 run 审计能看到 run 前置路由来源。

## 验证

1. RED：补 `test_dialogs.py`，证明低细节“继续”目前不会产生路由 Trace。
2. GREEN：实现最小 Trace 记录 helper，并在恢复预览、推荐后继预览、章节生成回落路径调用。
3. RED/GREEN：补 `test_writing_agent_trace_audit.py`，让审计输出包含与 run 相关的对话路由事件。
4. T1：运行低细节继续相关后端测试。
5. T2：运行 Agent Trace 审计相关后端测试。

## 非目标

- 不改变低细节“继续”的路由优先级。
- 不新增数据库字段或迁移。
- 不把路由 Trace 伪装成真实 LLM 调用；使用本地路由模型标识。
- 不调整前端展示。
