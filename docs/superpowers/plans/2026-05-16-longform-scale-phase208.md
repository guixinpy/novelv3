# Phase 208 - 对话消息预览前缀投影

## 目标

Hermes/Athena 长期使用后会积累大量对话消息。消息列表和工作区冷启动默认只需要预览内容，但旧实现会先从数据库读取完整 `dialog_messages.content`，再在 Python 层截断。

## 变更

- `DialogMessageService.list_messages()` 在默认预览模式下改用 `substr(dialog_messages.content, 1, max_content_chars + 1)`。
- 同一查询补充 `length(dialog_messages.content)`，前端仍能拿到 `original_content_length` 和 `content_truncated`。
- `after_id` 游标查询只读取 `created_at` 与 `id`，避免为分页游标加载完整消息。
- `full_content=true` 继续保留完整内容读取路径。

## 测试

- RED：`test_dialog_messages_preview_uses_bounded_content_projection` 先确认旧实现直接投影完整消息内容。
- GREEN：默认预览改为 SQL 前缀投影后，该测试通过。
- 回归：消息分页、Hermes/Athena 对话、工作区冷启动历史相关测试通过。

## 后续验证

- 已运行：`backend\.venv\Scripts\python.exe -m pytest backend/tests/test_dialog_messages_pagination.py backend/tests/test_dialogs.py backend/tests/test_athena_dialog.py backend/tests/test_workspace_bootstrap.py -q`
- 结果：`87 passed`
