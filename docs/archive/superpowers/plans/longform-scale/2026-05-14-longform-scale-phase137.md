# Phase 137: 消息列表 Trace 查询避免读取大 JSON

## 背景

对话消息列表会为 assistant 消息挂载 `trace_id`，便于前端打开模型调用详情。
旧实现通过 `db.query(AIModelCallTrace)` 查询完整 trace 行，这会同时读取 `messages`、`context_blocks`、`trace_metadata`。

长篇项目中这些 JSON 字段可能很大，消息列表只需要 `id` 与 `response_message_id`，读取完整 trace 会拖慢 Hermes/Athena 历史和 workspace 冷启动。

## 修复

- `_trace_by_response_id` 改为只投影：
  - `AIModelCallTrace.response_message_id`
  - `AIModelCallTrace.id`
- 消息返回结构不变，仍能填充 `trace_id`。
- 不影响 trace 详情接口，详情仍按需读取完整 JSON。

## 验证

- 先新增失败测试：
  - `backend/tests/test_dialog_messages_pagination.py::test_dialog_messages_trace_lookup_does_not_select_large_trace_json`
  - RED：旧查询 select 中包含 `messages/context_blocks/trace_metadata`。
- 修复后通过：
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialog_messages_pagination.py::test_dialog_messages_trace_lookup_does_not_select_large_trace_json -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialog_messages_pagination.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_dialogs.py backend\tests\test_athena_dialog.py backend\tests\test_workspace_bootstrap.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_model_call_traces.py -q`

## 后续观察

- 其他列表接口若只展示 trace summary，应继续使用字段投影，不直接加载完整 trace JSON。
- Trace 详情仍是完整审计入口，列表只做导航索引。
