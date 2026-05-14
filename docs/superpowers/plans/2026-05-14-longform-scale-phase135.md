# Phase 135: 模型调用 Trace 消息体积控制

## 背景

模型调用 trace 会保存 messages 和 context blocks。
此前 context block 会做脱敏和截断，但 messages 只脱敏、不截断。

章节生成 prompt 有 24000 字上下文预算，千章级生成会产生大量 trace。
如果 messages 原样入库，长期使用后 trace JSON 会持续膨胀，影响列表、详情和数据库体积。

## 修复

- `sanitize_model_messages` 对 `messages[*].content` 字符串执行 `truncate_text`。
- 保持原有脱敏逻辑。
- 非 `content` 字段继续走递归脱敏。
- 默认单条 message content 限制与 context block 一致，为 12000 字符。

## 验证

- 先新增失败测试：
  - `backend/tests/test_model_call_traces.py::test_sanitize_model_messages_truncates_large_message_content`
  - RED：旧实现不截断 large message content。
- 修复后通过：
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_model_call_traces.py::test_sanitize_model_messages_truncates_large_message_content -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_model_call_traces.py::test_sanitize_model_messages_redacts_authorization_bearer_and_api_keys backend\tests\test_model_call_traces.py::test_sanitize_model_messages_redacts_common_secret_key_variants_without_redacting_token_counts backend\tests\test_chapters.py::test_generate_chapter_records_model_call_trace -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_model_call_traces.py -q`
  - `.\backend\.venv\Scripts\python.exe -m pytest backend\tests\test_chapters.py backend\tests\test_prompting_chapter_migration.py -q`

## 后续观察

- Trace 详情页需要清晰展示 `truncated` 语义，目前 message content 只通过文本 notice 表示。
- 若未来需要完整 prompt 审计，可提供按需外部归档，而不是默认写入主库。
